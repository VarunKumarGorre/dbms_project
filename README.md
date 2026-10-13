# Research Project, Publication & Grant Management System (RPGMS)

An integrated, enterprise-grade database management system and web application for tracking multi-year academic research projects, sanctioned external grants, multi-head budget allocations, vouchered expenditures, milestone deliverables, peer-reviewed publications, and patents.

Built with a pure relational foundation (MySQL 8.0+/9.0+, 3NF, strict ACID transactions, row-level locks, native triggers, and stored procedures) coupled with a modern, responsive Flask 3 web application using custom design tokens, accessible components, and zero generic CSS frameworks or containers.

---

## 1. System Architecture

```text
+--------------------------------------------------------------------------+
|                       FLASK 3 WEB APPLICATION                            |
| 12 Blueprints: auth, dashboard, projects, investigators, grants,         |
|                milestones, expenditure, publications, patents,           |
|                reports (R1-R10), admin, api (typeahead autocomplete)     |
+--------------------------------------------------------------------------+
                                    |
                        Connection Pool (app/db.py)
                        Least-Privilege SQL User
                                    |
+--------------------------------------------------------------------------+
|                       MYSQL RELATIONAL ENGINE                            |
| Schemas: rpgms (production/demo) | rpgms_test (isolated test suite)      |
|                                                                          |
| 19 Tables: 3NF Relational Core with Composite Foreign Keys & Checks     |
| 9 Views:   Single-source aggregation metrics without join fan-out       |
| 18 Triggers: Invariant date bounds, effort limits, and tamper-proof audit|
| 8 Procedures: Transaction-owning sp_* with explicit row-level locking   |
| 15 Composite B-Tree Indexes: Tuned for sub-millisecond EXPLAIN execution |
+--------------------------------------------------------------------------+
```

---

## 2. Prerequisites

- **Operating System:** macOS (Apple Silicon / Intel)
- **Database Engine:** Local MySQL Community Server 8.0+ or 9.0+ (running on `127.0.0.1:3306`)
- **Python Runtime:** Python 3.12+ (tested on Python 3.14.0)
- **Package Manager:** `pip` / `venv`

---

## 3. Quick Start Setup (Mac Local)

### Step 3.1: Start Local MySQL Service
Start your local Homebrew MySQL server:
```bash
brew services start mysql
# Or manually if not using brew services:
# mysql.server start
```
Verify MySQL is listening on port 3306:
```bash
mysqladmin -u root -p ping
```

### Step 3.2: Initialize Database Schemas and Users
Connect to MySQL as your local administrator (`root`) and create the two dedicated `utf8mb4` databases and least-privilege users:
```sql
-- Connect via: mysql -u root -p

CREATE DATABASE IF NOT EXISTS rpgms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS rpgms_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Runtime Application User
CREATE USER IF NOT EXISTS 'rpgms_app'@'127.0.0.1' IDENTIFIED BY 'rpgms_app_pass';
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON rpgms.* TO 'rpgms_app'@'127.0.0.1';

-- Schema Owner / Migration User
CREATE USER IF NOT EXISTS 'rpgms_owner'@'127.0.0.1' IDENTIFIED BY 'rpgms_owner_pass';
GRANT ALL PRIVILEGES ON rpgms.* TO 'rpgms_owner'@'127.0.0.1';

-- Automated Test Suite User
CREATE USER IF NOT EXISTS 'rpgms_test_user'@'127.0.0.1' IDENTIFIED BY 'rpgms_test_pass';
GRANT ALL PRIVILEGES ON rpgms_test.* TO 'rpgms_test_user'@'127.0.0.1';

FLUSH PRIVILEGES;
```

### Step 3.3: Set Up Python Virtual Environment
Navigate to the repository root and create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3.4: Configure Environment Variables
Copy the configuration template to `.env`:
```bash
cp .env.example .env
```
Ensure `.env` matches your database configuration:
```ini
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=rpgms
TEST_DB_NAME=rpgms_test
DB_USER=rpgms_app
DB_PASSWORD=rpgms_app_pass
DB_SETUP_USER=rpgms_owner
DB_SETUP_PASSWORD=rpgms_owner_pass
DB_TEST_USER=rpgms_test_user
DB_TEST_PASSWORD=rpgms_test_pass
SECRET_KEY=rpgms-development-secret-key-32chars-min-length-2026
APP_ENV=demo
FLASK_DEBUG=0
PORT=5001
```

### Step 3.5: Run Schema Migrations & Seed Data
Execute `db/setup_db.py` to create the complete schema, views, triggers, stored procedures, indexes, and initial realistic seed data:
```bash
python db/setup_db.py --database rpgms --reset --seed --confirm-reset rpgms
```
> [!IMPORTANT]
> The setup tool enforces zero tolerance for `DROP DATABASE`. The `--reset` flag targets objects *inside* the selected schema only and strictly requires matching `--confirm-reset <dbname>`.

### Step 3.6: Launch the Web Application
Start the Flask application:
```bash
python run.py
```
Open your browser to: **`http://127.0.0.1:5001`**

---

## 4. Demo Login Credentials

The seed data provisions 6 user accounts spanning all 4 RBAC tiers with pre-hashed BCrypt passwords:

| Username | Password | Role | Description / Linked Identity |
|:---|:---|:---|:---|
| `admin` | `password123` | `ADMIN` | System Administrator (Full access, user provisioning, audit log) |
| `officer` | `password123` | `RESEARCH_OFFICER` | Research Office Staff (Operational CRUD across all entities) |
| `pi_rao` | `password123` | `PI` | Principal Investigator (Dr. Aravind Rao, CSE Dept, Project RP-2023-001) |
| `pi_kulkarni`| `password123` | `PI` | Principal Investigator (Dr. Sunita Kulkarni, Chemical Eng, RP-2023-002) |
| `pi_iyer` | `password123` | `PI` | Principal Investigator (Dr. Rajesh Iyer, Electrical Eng, RP-2024-001) |
| `viewer` | `password123` | `VIEWER` | Institutional Auditor (Executive metrics, reports R1–R10, redacted PII) |

---

## 5. Running the Test Suite

The comprehensive test suite contains 94 automated tests covering schema constraints, business rules (BR-01 through BR-18), query invariants, concurrent race condition locking, role scoping, and HTTP routes.

All automated tests target `rpgms_test` exclusively and will never modify or reset the main `rpgms` schema.

```bash
# 1. Reset and prepare isolated test database:
python db/setup_db.py --database rpgms_test --reset --seed --confirm-reset rpgms_test

# 2. Run the full pytest suite with verbose output:
pytest -v
```

Expected result:
```text
======================== 94 passed, 5 warnings in 3.64s ========================
```

---

## 6. Project Directory Structure

```text
DBMS/
├── app/                        # Application Source Code
│   ├── blueprints/             # 12 Modular Flask Blueprints
│   │   ├── auth.py             # Login, logout, session management
│   │   ├── dashboard.py        # Executive dashboard & role routing
│   │   ├── projects.py         # Project registration & detail tabs
│   │   ├── investigators.py    # Researcher directory & profiles
│   │   ├── grants.py           # Grant awards & budget allocations
│   │   ├── expenditure.py      # Expense vouchers & financial statement
│   │   ├── milestones.py       # Milestone deliverables tracker
│   │   ├── publications.py     # Publication catalogue & author orders
│   │   ├── patents.py          # Patent filings & grant tracking
│   │   ├── reports.py          # Analytical Reports Hub (R1–R10)
│   │   ├── admin.py            # User management & audit log diffs
│   │   └── api.py              # Autocomplete typeahead search endpoints
│   ├── services/               # Transactional Service Layer
│   ├── templates/              # 32 Semantic Jinja2 Templates
│   ├── static/                 # Static Assets (CSS, Vanilla JS, SVG icons)
│   │   ├── css/app.css         # Custom Design System & tokens
│   │   ├── js/                 # Modular Vanilla JS (forms, charts, search)
│   │   └── img/                # SVG icons and favicon
│   ├── __init__.py             # Flask App Factory & Jinja filters
│   ├── auth.py                 # RBAC decorators & project scoping helpers
│   ├── config.py               # Flask configurations (Dev, Test, Prod)
│   ├── db.py                   # MySQL connection pooling & transaction helpers
│   ├── errors.py               # Custom database error translation & mapping
│   └── utils.py                # Formatting utilities (INR ₹, dates, percentages)
├── db/                         # Database Migration & Seed Scripts
│   ├── 01_schema.sql           # 19 Relational tables, CHECKs, composite FKs
│   ├── 02_triggers.sql         # 18 Triggers (BR enforcement & audit logging)
│   ├── 03_procedures.sql       # 8 Transaction-owning stored procedures
│   ├── 04_views.sql            # 9 Relational views (portfolio metrics)
│   ├── 05_indexes.sql          # 15 Composite B-Tree optimization indexes
│   ├── 06_seed.sql             # Realistic multi-year institutional seed data
│   ├── 07_queries.sql          # Queries Q01 through Q40 with benchmarks
│   ├── 08_reports.sql          # Stored procedures for Reports R1 through R10
│   ├── 09_transaction_demo.sql # Interactive transaction demonstration script
│   └── setup_db.py             # Idempotent database provisioning script
├── docs/                       # Project Documentation
│   ├── requirements_analysis.md# Domain requirements & entity analysis
│   ├── er_model.md             # Conceptual & Logical Entity-Relationship Model
│   ├── relational_schema.md    # Schema definitions, datatypes, constraints
│   ├── normalization.md        # 1NF, 2NF, 3NF formal normalization proofs
│   ├── business_rules.md       # Specification of all 18 Business Rules
│   ├── indexing.md             # Indexing strategy & EXPLAIN plan analysis
│   ├── transactions.md         # Transaction boundaries, ACID, concurrency locks
│   ├── test_report.md          # Complete test execution logs & UI checklist
│   ├── user_guide.md           # Role-based guide with screenshot references
│   ├── decisions.md            # Architectural Decision Records (ADRs)
│   ├── viva_prep.md            # 30 Technical viva questions & answers
│   ├── wireframes.md           # Page layouts mapped to screenshot files
│   └── screens/                # High-resolution desktop & mobile screenshots
├── tests/                      # Automated Test Suite (94 Tests)
│   ├── conftest.py             # Pytest fixtures & isolated client runners
│   ├── test_schema_constraints.py # Constraint validations
│   ├── test_business_rules.py  # Positive and negative tests for BR-01 to BR-18
│   ├── test_queries_views.py   # View invariants, Q01-Q40, and R1-R10
│   ├── test_transactions.py    # Atomicity, rollback, and race conditions
│   ├── test_auth_roles.py      # RBAC, scoping, redaction, admin protection
│   └── test_routes.py          # Blueprint HTTP route lifecycles
├── run.py                      # Application launch entry point
├── requirements.txt            # Pinned dependencies
├── .env.example                # Configuration template
└── README.md                   # Quick-start documentation
```

---

## 7. Troubleshooting & FAQ

### Port 5000 / 5001 Conflict
On macOS, AirPlay Receiver ("Control Center") listens on port 5000 by default. RPGMS defaults to port 5001 to avoid conflicts. To change the port, set `PORT=<custom_port>` in `.env` or run:
```bash
PORT=8080 python run.py
```

### Resetting the Database
To re-initialize the database back to clean seed data:
```bash
python db/setup_db.py --database rpgms --reset --seed --confirm-reset rpgms
```
*Never use `--reset` without specifying the target schema in `--confirm-reset`.*

### MySQL Connection Pool Issues
If you encounter `OperationalError: MySQL Connection not available`, verify that MySQL server is running and that `pool_reset_session=False` is set in `app/db.py` (required for Python 3.14 C-extension compatibility).
