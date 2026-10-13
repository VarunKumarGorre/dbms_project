# Architecture & Design Decisions Log

This document records the foundational decisions made during the design, implementation, and deployment of the Research Project, Publication & Grant Management System (RPGMS).

---

## Decision 1: Single Integrated Application Architecture
- **Context:** The system merges previous UI specifications (`FRONTEND_SPEC.md`) and database/business logic specifications (`PROJECT_SPEC.md`) into a single implementation contract (`FINAL_RPGMS_SPEC.md`).
- **Decision:** Build a single integrated Flask 3 + Jinja2 web application connected to a single MySQL 8.0+ relational database via a dedicated service layer and MySQL connection pool. Streamlit or separate duplicate front-ends are prohibited.
- **Rationale:** Prevents drift between database state and UI state, ensures consistent role definitions and status enums, and centralizes validation and business logic.

---

## Decision 2: Environment & Local Execution (No Docker)
- **Context:** The deployment target is a developer workstation running macOS with an existing native MySQL installation.
- **Decision:** Use only the local native MySQL server (defaulting to `127.0.0.1:3306`). Docker, containers, and Docker Compose are prohibited.
- **Rationale:** Eliminates container networking overhead, uses existing homebrew/native tools, and maintains straightforward local debugging.

---

## Decision 3: Database Schemas & Safe Setup Strategy
- **Context:** The database setup script must manage database initialization and resets without endangering unrelated databases.
- **Decision:**
  - Allowlist strictly two target schemas: `rpgms` (development/runtime) and `rpgms_test` (automated test suite).
  - Prohibit `DROP DATABASE` anywhere in setup, migration, or test scripts.
  - Implement `--reset` in `db/setup_db.py` to drop and recreate only database objects (views, procedures, triggers, tables) inside the selected schema.
  - Require an explicit `--confirm-reset <dbname>` argument matching the target database before executing any destructive drop.
- **Rationale:** Ensures zero risk of accidental data destruction on the developer's workstation while allowing deterministic testing and re-seeding.

---

## Decision 4: Least-Privilege Database Accounts
- **Context:** Standard web applications often connect using MySQL `root`, bypassing privilege isolation and making it impossible to enforce procedural access controls.
- **Decision:**
  - `rpgms_owner`: Used solely during schema initialization and running `setup_db.py`. Holds schema-scoped object management privileges on `rpgms` and `rpgms_test`.
  - `rpgms_app`: Used by the Flask runtime application. Granted `SELECT` across tables/views, `EXECUTE` on stored procedures, and controlled DML on non-financial tables. Specifically denied direct DML (`INSERT`, `UPDATE`, `DELETE`) on `project`, `project_investigator`, `grant_award`, `grant_budget_allocation`, and `expenditure`.
  - `rpgms_test_user`: Used during automated test runs on `rpgms_test` to verify native constraints and seed test fixtures.
- **Rationale:** Guarantees that even if an application bug or SQL injection attempt occurred, financial expenditures and project budgets cannot be manipulated without executing the transaction-owning stored procedures.

---

## Decision 5: Aggregate Rule Enforcement via Stored Procedures
- **Context:** Business Rule BR-06 requires that line-item and overall grant expenditures never exceed allocated budgets. Business Rule BR-11 requires that researcher workloads never exceed 100%.
- **Decision:** Enforce aggregate budget limits and effort caps in `SQL SECURITY DEFINER` stored procedures (`sp_record_expenditure`, `sp_register_project`, `sp_assign_investigator`, `sp_change_project_pi`) using explicit row locking (`FOR UPDATE` under `READ COMMITTED`). Do not use self-table aggregate triggers (`SELECT SUM(...) FROM expenditure`) on the same table being mutated.
- **Rationale:** Avoids MySQL table-mutating trigger limitations, establishes a strict serialization boundary against concurrent over-expenditure races, and provides deterministic ACID rollbacks.

---

## Decision 6: Single PI Invariant Modeling
- **Context:** Business Rule BR-10 requires exactly one Principal Investigator per project.
- **Decision:** Implement a generated stored column in `project_investigator`:
  ```sql
  pi_flag TINYINT GENERATED ALWAYS AS (IF(role = 'PI', 1, NULL)) STORED,
  UNIQUE KEY uq_one_pi_per_project (project_id, pi_flag)
  ```
- **Rationale:** MySQL `UNIQUE` indexes permit multiple `NULL` values but strictly one `1`. This structurally prevents having more than one PI per project at the storage engine level, while `sp_register_project` guarantees that at least one PI is assigned upon creation.

---

## Decision 7: Multi-Level Viewer Redaction
- **Context:** The `VIEWER` role is restricted to aggregate dashboard metrics and analytical reports (R1–R10). Record-level operational details (project codes, individual names, DOIs, voucher numbers) must not be accessible.
- **Decision:** Redact viewer data at the database service query layer before returning data to the application, charts, or CSV exports. Never retrieve sensitive rows and hide them with client-side CSS or JavaScript.
- **Rationale:** Ensures complete privacy and prevents data leakage through browser inspection, JSON endpoints, or exported spreadsheets.
