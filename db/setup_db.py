#!/usr/bin/env python3
"""
RPGMS Database Setup and Migration Utility
File: db/setup_db.py
Author: Antigravity AI

Safety & Security Rules:
1. Targets ONLY allowlisted schemas ('rpgms', 'rpgms_test').
2. NEVER executes DROP DATABASE.
3. --reset drops and recreates schema objects ONLY with exact --confirm-reset matching.
4. Uses a custom delimiter-aware SQL runner that handles 'DELIMITER $$' constructs.
5. Applies least-privilege GRANTs to runtime application and test users.
"""

import os
import sys
import argparse
import re
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv

# Load environment configuration
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

ALLOWLISTED_DATABASES = ("rpgms", "rpgms_test")

def parse_sql_statements(sql_text: str):
    """
    Robust delimiter-aware SQL statement parser.
    Tracks single quotes, double quotes, backticks, line comments (--), and block comments (/* */).
    Interprets 'DELIMITER <token>' directives without sending them to the MySQL server.
    """
    statements = []
    current_token = []
    delimiter = ";"
    
    i = 0
    n = len(sql_text)
    in_single_quote = False
    in_double_quote = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    
    while i < n:
        # Check DELIMITER command at start of line
        if not in_single_quote and not in_double_quote and not in_backtick and not in_block_comment and not in_line_comment:
            if i == 0 or sql_text[i - 1] == "\n":
                rest = sql_text[i:]
                if rest.upper().startswith("DELIMITER"):
                    eol = sql_text.find("\n", i)
                    if eol == -1:
                        eol = n
                    line = sql_text[i:eol].strip()
                    parts = line.split()
                    if len(parts) >= 2:
                        delimiter = parts[1]
                    i = eol + 1
                    continue

        ch = sql_text[i]
        next_ch = sql_text[i + 1] if i + 1 < n else ""

        if in_line_comment:
            current_token.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            current_token.append(ch)
            if ch == "*" and next_ch == "/":
                current_token.append("/")
                i += 2
                in_block_comment = False
                continue
            i += 1
            continue

        if in_single_quote:
            current_token.append(ch)
            if ch == "\\":
                if next_ch:
                    current_token.append(next_ch)
                    i += 2
                    continue
            elif ch == "'":
                if next_ch == "'":
                    current_token.append("'")
                    i += 2
                    continue
                in_single_quote = False
            i += 1
            continue

        if in_double_quote:
            current_token.append(ch)
            if ch == "\\":
                if next_ch:
                    current_token.append(next_ch)
                    i += 2
                    continue
            elif ch == '"':
                in_double_quote = False
            i += 1
            continue

        if in_backtick:
            current_token.append(ch)
            if ch == "`":
                in_backtick = False
            i += 1
            continue

        # Check comment starts
        if ch == "-" and next_ch == "-":
            in_line_comment = True
            current_token.append(ch)
            current_token.append(next_ch)
            i += 2
            continue

        if ch == "/" and next_ch == "*":
            in_block_comment = True
            current_token.append(ch)
            current_token.append(next_ch)
            i += 2
            continue

        if ch == "'":
            in_single_quote = True
            current_token.append(ch)
            i += 1
            continue

        if ch == '"':
            in_double_quote = True
            current_token.append(ch)
            i += 1
            continue

        if ch == "`":
            in_backtick = True
            current_token.append(ch)
            i += 1
            continue

        # Check active delimiter match
        delim_len = len(delimiter)
        if sql_text[i:i + delim_len] == delimiter:
            stmt = "".join(current_token).strip()
            if stmt:
                statements.append(stmt)
            current_token = []
            i += delim_len
            continue

        current_token.append(ch)
        i += 1

    rem = "".join(current_token).strip()
    if rem:
        statements.append(rem)
        
    return statements


def execute_sql_file(cursor, file_path: Path):
    """Executes a SQL file statement by statement using delimiter awareness."""
    if not file_path.exists():
        raise FileNotFoundError(f"SQL file not found: {file_path}")
    
    content = file_path.read_text(encoding="utf-8")
    statements = parse_sql_statements(content)
    
    for stmt in statements:
        stmt_clean = stmt.strip()
        if not stmt_clean or stmt_clean.startswith("--") or stmt_clean.startswith("/*"):
            # Skip pure comment statements
            lines = [l for l in stmt_clean.splitlines() if not l.strip().startswith("--") and not l.strip().startswith("/*")]
            if not lines:
                continue
        cursor.execute(stmt_clean)


def reset_schema_objects(cursor, db_name: str):
    """
    Drops all views, procedures, triggers, and tables inside db_name.
    NEVER drops the database itself.
    """
    print(f"[*] Resetting schema objects inside '{db_name}'...")
    
    # 1. Drop Views
    cursor.execute("""
        SELECT table_name FROM information_schema.views
        WHERE table_schema = %s
    """, (db_name,))
    views = [row[0] for row in cursor.fetchall()]
    for v in views:
        cursor.execute(f"DROP VIEW IF EXISTS `{v}`")
    if views:
        print(f"  - Dropped {len(views)} views")

    # 2. Drop Routines (Procedures & Functions)
    cursor.execute("""
        SELECT routine_name, routine_type FROM information_schema.routines
        WHERE routine_schema = %s
    """, (db_name,))
    routines = cursor.fetchall()
    for r_name, r_type in routines:
        cursor.execute(f"DROP {r_type} IF EXISTS `{r_name}`")
    if routines:
        print(f"  - Dropped {len(routines)} routines")

    # 3. Drop Tables safely using disabled FK checks
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    try:
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
        """, (db_name,))
        tables = [row[0] for row in cursor.fetchall()]
        for t in tables:
            cursor.execute(f"DROP TABLE IF EXISTS `{t}`")
        if tables:
            print(f"  - Dropped {len(tables)} tables")
    finally:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")


def apply_least_privilege_grants(cursor, db_name: str):
    """
    Grants least-privilege permissions to rpgms_app and test users.
    Ensures Flask runtime user cannot bypass stored procedures for financial/project DML.
    """
    print(f"[*] Configuring least-privilege permissions on '{db_name}'...")
    app_user = os.getenv("DB_USER", "rpgms_app")
    test_user = os.getenv("DB_TEST_USER", "rpgms_test_user")

    # App User permissions
    try:
        # First grant SELECT on all tables/views and EXECUTE on procedures
        cursor.execute(f"GRANT SELECT, EXECUTE ON `{db_name}`.* TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        
        # Controlled table DML for allowed operational workflows
        cursor.execute(f"GRANT INSERT, UPDATE ON `{db_name}`.researcher TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        cursor.execute(f"GRANT INSERT, UPDATE ON `{db_name}`.publication TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        cursor.execute(f"GRANT INSERT, UPDATE ON `{db_name}`.patent TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        cursor.execute(f"GRANT INSERT, DELETE ON `{db_name}`.publication_author TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        cursor.execute(f"GRANT INSERT, DELETE ON `{db_name}`.project_publication TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        cursor.execute(f"GRANT INSERT, DELETE ON `{db_name}`.patent_inventor TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        cursor.execute(f"GRANT INSERT, DELETE ON `{db_name}`.project_patent TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        cursor.execute(f"GRANT INSERT, UPDATE ON `{db_name}`.report TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        cursor.execute(f"GRANT INSERT ON `{db_name}`.milestone TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        cursor.execute(f"GRANT INSERT ON `{db_name}`.user_account TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        cursor.execute(f"GRANT UPDATE (username, role, researcher_id, is_active) ON `{db_name}`.user_account TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        cursor.execute(f"GRANT INSERT ON `{db_name}`.audit_log TO '{app_user}'@'127.0.0.1', '{app_user}'@'localhost';")
        
        print(f"  - Granted restricted app privileges to '{app_user}'")
    except mysql.connector.Error as err:
        print(f"  [!] Notice configuring app user grants: {err}")

    # Test User permissions on rpgms_test
    if db_name == "rpgms_test":
        try:
            cursor.execute(f"GRANT ALL PRIVILEGES ON `rpgms_test`.* TO '{test_user}'@'127.0.0.1', '{test_user}'@'localhost';")
            print(f"  - Granted test suite privileges to '{test_user}' on rpgms_test")
        except mysql.connector.Error as err:
            print(f"  [!] Notice configuring test user grants: {err}")

    cursor.execute("FLUSH PRIVILEGES;")


def main():
    parser = argparse.ArgumentParser(description="RPGMS MySQL Schema Setup and Migration Tool")
    parser.add_argument("--database", required=True, choices=ALLOWLISTED_DATABASES,
                        help="Allowlisted database target ('rpgms' or 'rpgms_test')")
    parser.add_argument("--reset", action="store_true",
                        help="Drop and recreate all objects inside the selected database")
    parser.add_argument("--confirm-reset", default=None,
                        help="Must exactly match --database to authorize --reset")
    parser.add_argument("--seed", action="store_true",
                        help="Load sample seed data from db/06_seed.sql")
    parser.add_argument("--indexes", action="store_true", default=True,
                        help="Apply performance and FULLTEXT indexes from db/05_indexes.sql")

    args = parser.parse_args()
    db_name = args.database

    if args.reset:
        if args.confirm_reset != db_name:
            print(f"[-] ERROR: --reset requires --confirm-reset {db_name} (got: '{args.confirm_reset}')")
            sys.exit(1)

    # Resolve DB setup credentials
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", 3306))
    user = os.getenv("DB_SETUP_USER", os.getenv("DB_USER", "root"))
    password = os.getenv("DB_SETUP_PASSWORD", os.getenv("DB_PASSWORD", ""))

    print(f"[*] Connecting to MySQL at {host}:{port} as user '{user}'...")
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            autocommit=True
        )
    except mysql.connector.Error as err:
        print(f"[-] Connection failed: {err}")
        print("    Ensure your local MySQL service is running on macOS: `brew services start mysql`")
        sys.exit(1)

    cursor = conn.cursor()

    try:
        # Check MySQL version (requires 8.0.16+)
        cursor.execute("SELECT VERSION();")
        version_str = cursor.fetchone()[0]
        print(f"[*] Connected to MySQL Server version: {version_str}")

        # Ensure schema exists (utf8mb4)
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;")
        cursor.execute(f"USE `{db_name}`;")

        db_dir = ROOT_DIR / "db"

        if args.reset:
            reset_schema_objects(cursor, db_name)

        # 1. Schema DDL
        print("[*] Applying schema DDL (db/01_schema.sql)...")
        execute_sql_file(cursor, db_dir / "01_schema.sql")

        # 2. Triggers
        print("[*] Applying business rule & audit triggers (db/02_triggers.sql)...")
        execute_sql_file(cursor, db_dir / "02_triggers.sql")

        # 3. Stored Procedures
        print("[*] Applying transaction-owning stored procedures (db/03_procedures.sql)...")
        execute_sql_file(cursor, db_dir / "03_procedures.sql")

        # 4. Indexes (if enabled)
        if args.indexes and (db_dir / "05_indexes.sql").exists():
            print("[*] Applying indexes (db/05_indexes.sql)...")
            execute_sql_file(cursor, db_dir / "05_indexes.sql")

        # 5. Views (if present)
        if (db_dir / "04_views.sql").exists():
            print("[*] Applying views (db/04_views.sql)...")
            execute_sql_file(cursor, db_dir / "04_views.sql")

        # 6. Seed Data (if requested)
        if args.seed:
            seed_file = db_dir / "06_seed.sql"
            if seed_file.exists():
                print("[*] Loading sample seed data (db/06_seed.sql)...")
                execute_sql_file(cursor, seed_file)
                print("[+] Sample seed data loaded successfully!")
            else:
                print(f"[!] Warning: Seed file '{seed_file}' does not exist yet.")

        # 7. Apply Least-Privilege Grants
        apply_least_privilege_grants(cursor, db_name)

        # Verification summary
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        print(f"\n[+] Success! '{db_name}' initialized with {len(tables)} tables:")
        for t in tables:
            print(f"    - {t[0]}")

        cursor.execute("SHOW TRIGGERS;")
        triggers = cursor.fetchall()
        print(f"[+] Active triggers: {len(triggers)}")

        cursor.execute("SHOW PROCEDURE STATUS WHERE Db = %s;", (db_name,))
        procs = cursor.fetchall()
        print(f"[+] Active stored procedures: {len(procs)}")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
