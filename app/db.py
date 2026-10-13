"""
RPGMS Database Access Layer
File: app/db.py
Author: Antigravity AI

Provides:
- Thread-safe MySQL connection pooling.
- run_query: Parameterized SELECT/DML returning dictionary rows.
- run_transaction: Context manager for direct multi-statement write transactions.
- call_procedure: Dedicated runner for transaction-owning stored procedures.
- Automatic session actor injection (@rpgms_actor) and cleanup.
"""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple, Union
import mysql.connector
from mysql.connector import pooling
from flask import g, current_app, has_request_context, session

_connection_pool: Optional[pooling.MySQLConnectionPool] = None

def init_db_pool(app):
    """Initializes the MySQL connection pool."""
    global _connection_pool
    config = app.config
    try:
        _connection_pool = pooling.MySQLConnectionPool(
            pool_name=config.get("DB_POOL_NAME", "rpgms_pool"),
            pool_size=config.get("DB_POOL_SIZE", 5),
            pool_reset_session=False,
            host=config.get("DB_HOST", "127.0.0.1"),
            port=config.get("DB_PORT", 3306),
            database=config.get("DB_NAME", "rpgms"),
            user=config.get("DB_USER", "rpgms_app"),
            password=config.get("DB_PASSWORD", ""),
            autocommit=True
        )
    except mysql.connector.Error as err:
        app.logger.error(f"Failed to initialize MySQL connection pool: {err}")
        raise err

def get_connection():
    """Retrieves a connection from the pool."""
    global _connection_pool
    if _connection_pool is None:
        if current_app:
            init_db_pool(current_app)
        else:
            raise RuntimeError("Database pool not initialized.")
    conn = _connection_pool.get_connection()
    return conn

def set_connection_actor(conn, username: Optional[str] = None):
    """Sets session variable @rpgms_actor on the checked-out connection."""
    if username is None and has_request_context():
        username = session.get("username")
    cursor = conn.cursor()
    try:
        if username:
            cursor.execute("SET @rpgms_actor = %s;", (username,))
        else:
            cursor.execute("SET @rpgms_actor = NULL;")
    finally:
        cursor.close()

def clear_connection_actor(conn):
    """Cleans up session variable @rpgms_actor before returning to pool."""
    cursor = conn.cursor()
    try:
        cursor.execute("SET @rpgms_actor = NULL; SET @rpgms_pi_transfer = NULL;")
    except Exception:
        pass
    finally:
        cursor.close()

def run_query(sql: str, params: Union[Tuple, List, Dict] = (), fetchone: bool = False, as_dict: bool = True) -> Any:
    """
    Executes a parameterized query and returns results.
    For SELECT queries: returns List[Dict] or Optional[Dict].
    For INSERT/UPDATE/DELETE queries: returns affected row count or last_insert_id.
    """
    conn = get_connection()
    try:
        set_connection_actor(conn)
        cursor = conn.cursor(dictionary=as_dict)
        try:
            cursor.execute(sql, params)
            if cursor.with_rows:
                if fetchone:
                    return cursor.fetchone()
                return cursor.fetchall()
            else:
                return cursor.lastrowid if cursor.lastrowid else cursor.rowcount
        finally:
            cursor.close()
    finally:
        clear_connection_actor(conn)
        conn.close()

@contextmanager
def run_transaction():
    """
    Context manager for direct multi-statement write transactions.
    Autocommit is disabled for the duration of the block.
    Commits on success; rolls back on any exception.
    """
    conn = get_connection()
    conn.autocommit = False
    try:
        set_connection_actor(conn)
        cursor = conn.cursor(dictionary=True)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
    finally:
        clear_connection_actor(conn)
        conn.autocommit = True
        conn.close()

def call_procedure(proc_name: str, params: Tuple = ()) -> Tuple[Tuple, List[List[Dict]]]:
    """
    Executes a transaction-owning stored procedure.
    Must NOT be called within run_transaction() because the procedure owns its transaction.
    Returns (out_parameters, [result_sets]).
    """
    conn = get_connection()
    try:
        set_connection_actor(conn)
        cursor = conn.cursor(dictionary=True)
        try:
            out_raw = cursor.callproc(proc_name, params)
            if isinstance(out_raw, dict):
                out_params = tuple(val for _, val in sorted(out_raw.items(), key=lambda it: int(it[0].split('_arg')[-1])))
            else:
                out_params = tuple(out_raw) if out_raw is not None else ()

            results = []
            for result in cursor.stored_results():
                results.append(result.fetchall())
            return out_params, results
        finally:
            cursor.close()
    finally:
        clear_connection_actor(conn)
        conn.close()
