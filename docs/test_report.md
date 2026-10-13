# RPGMS Test Execution & Quality Assurance Report

**Project:** Research Project, Publication & Grant Management System (RPGMS)  
**Evaluation Environment:** macOS Darwin (Apple Silicon), Local MySQL 9.7.1 Community Server  
**Runtime:** Python 3.14.0, Flask 3.1.0, pytest 9.1.1, mysql-connector-python 9.2.0  
**Database Target:** `rpgms_test` (Isolated Test Database, reset & seeded via `db/setup_db.py`)  
**Test Suite Status:** 94 of 94 tests passing (100% pass rate)  
**Execution Timestamp:** 2026-10-14T00:43:54+05:30  

---

## 1. Database Seed Verification & Table Row Counts

The database was populated using `db/06_seed.sql` via `python db/setup_db.py --database rpgms --reset --seed --confirm-reset rpgms`. All rows passed every native trigger and foreign key constraint without error.

| Table Name | Entity Description | Verified Row Count |
|:---|:---|:---:|
| `department` | Academic Departments | 6 |
| `researcher` | Faculty, Postdocs & Research Staff | 24 |
| `funding_agency` | National & International Grant Sponsors | 9 |
| `project` | Multi-Year Research Projects | 15 |
| `project_investigator` | PI and Co-PI Project Appointments | 41 |
| `grant_award` | Sanctioned External Grant Awards | 16 |
| `budget_head` | Standardized Budget Expenditure Categories | 6 |
| `grant_budget_allocation`| Grant-Specific Head Allotments | 92 |
| `expenditure` | Vouchered Financial Disbursements | 90 |
| `milestone` | Project Deliverables & Deadlines | 61 |
| `publication` | Peer-Reviewed Articles & Proceedings | 30 |
| `publication_author` | Ordered Author Attribution Links | 75 |
| `project_publication` | Project-to-Publication Acknowledgments | 35 |
| `patent` | Intellectual Property Applications & Grants | 7 |
| `patent_inventor` | Inventor Attribution Links | 12 |
| `project_patent` | Project-to-Patent IP Linkages | 8 |
| `report` | Compliance & Progress Periodic Reports | 20 |
| `user_account` | Application User Logins | 6 |
| `audit_log` | Forensic Audit History & Change Tracking | 541 |

---

## 2. Automated Test Results Table

The automated test suite covers relational integrity, business rules (BR-01 through BR-18), query correctness, transaction isolation with concurrency locks, RBAC enforcement, and HTTP routes.

| Test ID | Area | Description | Input | Expected | Actual | Pass/Fail |
|:---|:---|:---|:---|:---|:---|:---:|
| `SC-01` | Constraints | `chk_proj_dates` end > start date | `start='2025-01-01', end='2024-12-31'` | Rejected with errno 3819 | Rejected with errno 3819 | **PASS** |
| `SC-02` | Constraints | `chk_gr_dates` end > start >= sanction | `grant_start='2023-12-01', sanction='2024-01-01'` | Rejected with errno 3819 | Rejected with errno 3819 | **PASS** |
| `SC-03` | Constraints | `chk_positive_amounts` in grant & exp | `amount = -500.00` | Rejected with errno 3819 | Rejected with errno 3819 | **PASS** |
| `SC-04` | Constraints | `chk_pub_doi` regex format | `doi = 'invalid-doi-format'` | Rejected with errno 3819 | Rejected with errno 3819 | **PASS** |
| `SC-05` | Constraints | `chk_ms_status` completed date consistency | `status='Completed', completed_date=NULL` | Rejected with errno 3819 | Rejected with errno 3819 | **PASS** |
| `SC-06` | Constraints | `chk_pat_status` grant date consistency | `status='Granted', grant_date=NULL` | Rejected with errno 3819 | Rejected with errno 3819 | **PASS** |
| `SC-07` | Constraints | `chk_rep_submitted` date consistency | `status='Submitted', submission_date=NULL` | Rejected with errno 3819 | Rejected with errno 3819 | **PASS** |
| `SC-08` | Constraints | `chk_pi_effort` bounds 1% - 100% | `effort_percent = 105.00` | Rejected with errno 3819 | Rejected with errno 3819 | **PASS** |
| `SC-09` | Constraints | `uq_one_pi_per_project` uniqueness | 2 PI rows on same project | Rejected with errno 1062 | Rejected with errno 1062 | **PASS** |
| `SC-10` | Constraints | `fk_exp_alloc` composite foreign key | Spend on unallocated head | Rejected with errno 1452 | Rejected with errno 1452 | **PASS** |
| `SC-11` | Constraints | Referential Integrity CASCADE/RESTRICT | Delete project with active grant | Blocked by ON DELETE RESTRICT | Blocked by ON DELETE RESTRICT | **PASS** |
| `SC-12` | Constraints | Column Defaults applied on omit | Insert without status/dates | Default 'Proposed' / CURRENT_TIMESTAMP | Applied correctly | **PASS** |
| `BR-01` | Business Rules | BR-01 Project start < end date | Project registration with end < start | Trigger signal 45000: BR-01 | Trigger signal 45000: BR-01 | **PASS** |
| `BR-02` | Business Rules | BR-02 Grant start < end and >= sanction | Grant creation with sanction > start | Trigger signal 45000: BR-02 | Trigger signal 45000: BR-02 | **PASS** |
| `BR-03` | Business Rules | BR-03 Grant within project lifetime | Grant start before project start | Trigger signal 45000: BR-03 | Trigger signal 45000: BR-03 | **PASS** |
| `BR-04` | Business Rules | BR-04 Milestone within project dates | Milestone target date after project end | Trigger signal 45000: BR-04 | Trigger signal 45000: BR-04 | **PASS** |
| `BR-05` | Business Rules | BR-05 Strictly positive amounts | Expenditure with zero amount (0.00) | Trigger signal 45000: BR-05 | Trigger signal 45000: BR-05 | **PASS** |
| `BR-06` | Business Rules | BR-06 Expenditure budget limit | Spend exceeding allocated head balance | Trigger signal 45000: BR-06 | Trigger signal 45000: BR-06 | **PASS** |
| `BR-07` | Business Rules | BR-07 Expense within grant dates | Expense dated after grant end | Trigger signal 45000: BR-07 | Trigger signal 45000: BR-07 | **PASS** |
| `BR-08` | Business Rules | BR-08 DOI uniqueness & regex | Duplicate DOI insertion | Unique constraint violation 1062 | Unique constraint violation 1062 | **PASS** |
| `BR-09` | Business Rules | BR-09 Allocation sum <= grant amount | Head allocations exceeding award | Trigger signal 45000: BR-09 | Trigger signal 45000: BR-09 | **PASS** |
| `BR-10` | Business Rules | BR-10 Single PI per project | Direct secondary PI assignment | Trigger signal 45000: BR-10 | Trigger signal 45000: BR-10 | **PASS** |
| `BR-11` | Business Rules | BR-11 Active workload <= 100% | Investigator assigned 110% total effort | Trigger signal 45000: BR-11 | Trigger signal 45000: BR-11 | **PASS** |
| `BR-12` | Business Rules | BR-12 Inactive researcher rejected | Assign researcher where is_active=0 | Trigger signal 45000: BR-12 | Trigger signal 45000: BR-12 | **PASS** |
| `BR-13` | Business Rules | BR-13 Milestone completion validation | Completed status with null date | Trigger signal 45000: BR-13 | Trigger signal 45000: BR-13 | **PASS** |
| `BR-14` | Business Rules | BR-14 Patent status transitions | Granted patent with future grant date | Trigger signal 45000: BR-14 | Trigger signal 45000: BR-14 | **PASS** |
| `BR-15` | Business Rules | BR-15 Allocation head requirement | Expense on unallocated head ID | Composite FK / Trigger BR-15 | Composite FK / Trigger BR-15 | **PASS** |
| `BR-16` | Business Rules | BR-16 Publication date >= proj start | Publication dated before project start | Trigger signal 45000: BR-16 | Trigger signal 45000: BR-16 | **PASS** |
| `BR-17` | Business Rules | BR-17 Closed project immutability | New expenditure on 'Completed' project | Procedure signal 45000: BR-17 | Procedure signal 45000: BR-17 | **PASS** |
| `BR-18` | Business Rules | BR-18 Publication authors & order | Duplicate author order on paper | Unique key uq_author_order | Unique key uq_author_order | **PASS** |
| `QV-01` | Views | `vw_project_overview` row generation | `SELECT * FROM vw_project_overview` | Returns >= 10 rows | Returns 15 rows | **PASS** |
| `QV-02` | Views | `vw_project_progress` row generation | `SELECT * FROM vw_project_progress` | Returns >= 10 rows | Returns 15 rows | **PASS** |
| `QV-03` | Views | `vw_budget_utilization` row generation | `SELECT * FROM vw_budget_utilization` | Returns >= 10 rows | Returns 16 rows | **PASS** |
| `QV-04` | Views | `vw_budget_head_utilization` row gen | `SELECT * FROM vw_budget_head_utilization` | Returns >= 10 rows | Returns 92 rows | **PASS** |
| `QV-05` | Views | `vw_milestone_tracker` row generation | `SELECT * FROM vw_milestone_tracker` | Returns >= 10 rows | Returns 61 rows | **PASS** |
| `QV-06` | Views | `vw_researcher_output` row generation | `SELECT * FROM vw_researcher_output` | Returns >= 10 rows | Returns 24 rows | **PASS** |
| `QV-07` | Views | `vw_agency_portfolio` row generation | `SELECT * FROM vw_agency_portfolio` | Returns >= 5 rows | Returns 9 rows | **PASS** |
| `QV-08` | Views | `vw_project_publications` row gen | `SELECT * FROM vw_project_publications` | Returns >= 10 rows | Returns 35 rows | **PASS** |
| `QV-09` | Views | `vw_department_summary` row generation | `SELECT * FROM vw_department_summary` | Returns 6 rows | Returns 6 rows | **PASS** |
| `QV-10` | Views | Arithmetic consistency invariant | `total_allocated + remaining = grant_amt` | `ABS(diff) < 0.01` for all grants | Invariant holds exactly | **PASS** |
| `QV-11` | Views | Absence of join fan-out | Sum of expenditure vs raw table sum | `view_sum == raw_sum` | Invariant holds exactly | **PASS** |
| `QV-12` | Queries | All 40 SQL Queries execution | Execute Q01 through Q40 scripts | 40/40 execute cleanly without error | 40/40 executed cleanly | **PASS** |
| `QV-13`..`22`| Reports | All 10 Reports execution (R1–R10) | Execute R1 through R10 procedures | 10/10 return populated rows | 10/10 return populated rows | **PASS** |
| `TX-01` | Transactions | Procedure atomicity & rollback | `sp_register_project` with invalid dates | 0 rows inserted in project / team | Rolled back completely | **PASS** |
| `TX-02` | Transactions | Concurrent expenditure race condition | Two threads spending last ₹ 5,000 | Exactly 1 success, 1 blocked (BR-06) | Serialized via FOR UPDATE | **PASS** |
| `RBAC-01..10`| Auth & Roles | Viewer operational routes forbidden | VIEWER GET `/projects/new`, `/grants/new` | HTTP 403 Forbidden | HTTP 403 Forbidden | **PASS** |
| `RBAC-11` | Auth & Roles | Viewer permitted on dashboard & reports | VIEWER GET `/dashboard`, `/reports/r1` | HTTP 200 OK | HTTP 200 OK | **PASS** |
| `RBAC-12..21`| Auth & Roles | Viewer redaction in R1–R10 HTML/CSV | Inspect responses for PI/code names | Zero row-level project names leaked | Aggregate metrics only | **PASS** |
| `RBAC-22` | Auth & Roles | PI project isolation scoping | PI Rao access project 1 (own) vs 2 (other) | 200 on own, 403 on other | Scoped strictly | **PASS** |
| `RBAC-23` | Auth & Roles | Last active ADMIN protection | Admin attempts to deactivate own admin | Flash: Cannot deactivate last admin | Deactivation blocked | **PASS** |
| `RBAC-24` | Auth & Roles | Officer full operational access | OFFICER GET `/projects/new`, `/grants/new` | HTTP 200 OK | HTTP 200 OK | **PASS** |
| `RT-01` | Blueprints | Authentication Login & Logout | GET/POST `/login`, POST `/logout` | 302 Redirect to `/dashboard`, `/login` | 302 Redirects verified | **PASS** |
| `RT-02` | Blueprints | Dashboard Views across Roles | GET `/dashboard` as Admin, PI, Viewer | HTTP 200 OK across all roles | HTTP 200 OK | **PASS** |
| `RT-03` | Blueprints | Project Registration & Detail | POST `/projects/new`, GET `/projects/1` | 302 Created, 200 Detail displayed | 302 Redirect, 200 Detail | **PASS** |
| `RT-04` | Blueprints | Assign Investigator Route | POST `/projects/1/investigators` | 302 Redirect to `/projects/1` | 302 Redirect verified | **PASS** |
| `RT-05` | Blueprints | Grant Creation Wizard & Detail | POST `/grants/new`, GET `/grants/1` | 302 Created, 200 Detail displayed | 302 Redirect, 200 Detail | **PASS** |
| `RT-06` | Blueprints | Expenditure Recording & Statement | POST `/expenditure/new`, GET `/expenditure/statement/1` | 302 Created, 200 Statement displayed | 302 Redirect, 200 Statement | **PASS** |
| `RT-07` | Blueprints | Milestone Status Update | POST `/milestones/1/status` | 302 Redirect | 302 Redirect verified | **PASS** |
| `RT-08` | Blueprints | Publication Creation & Detail | POST `/publications/new`, GET `/publications/1` | 302 Created, 200 Detail displayed | 302 Redirect, 200 Detail | **PASS** |
| `RT-09` | Blueprints | Patent Registration & Detail | POST `/patents/new`, GET `/patents/1` | 302 Created, 200 Detail displayed | 302 Redirect, 200 Detail | **PASS** |
| `RT-10` | Blueprints | Reports Hub & Analytical Views | GET `/reports`, GET `/reports/r1` | HTTP 200 OK with Chart.js container | HTTP 200 OK | **PASS** |
| `RT-11` | Blueprints | Admin User Management & Audit Log | GET `/admin/users`, GET `/admin/audit` | HTTP 200 OK with diff modals | HTTP 200 OK | **PASS** |
| `RT-12` | Blueprints | Typeahead Search Autocomplete API | GET `/api/search?q=sensor` | HTTP 200 JSON {projects, researchers} | HTTP 200 JSON returned | **PASS** |
| `RT-13` | Blueprints | Grant Budget Heads API | GET `/api/grants/1/heads` | HTTP 200 JSON array of active heads | HTTP 200 JSON returned | **PASS** |
| `RT-14` | Blueprints | 404 Custom Error Handler | GET `/non-existent-page-xyz-123` | HTTP 404 with styled error layout | HTTP 404 custom page | **PASS** |

### Official Pytest Execution Output
```text
======================== 94 passed, 5 warnings in 3.64s ========================
```

---

## 3. Sample Query & Report Execution Outputs

### Q01: Active Projects with Principal Investigators & Departments
```sql
SELECT p.project_code, p.title, CONCAT(r.first_name, ' ', r.last_name) AS pi_name, d.dept_name, p.start_date, p.end_date
FROM project AS p
JOIN project_investigator AS pi ON pi.project_id = p.project_id AND pi.role = 'PI'
JOIN researcher AS r ON r.researcher_id = pi.researcher_id
JOIN department AS d ON d.dept_id = p.dept_id
WHERE p.status = 'Active' ORDER BY p.start_date DESC LIMIT 3;
```
*Sample Output:*
```text
project_code | title                                              | pi_name             | dept_name              | start_date | end_date
RP-2023-001  | Scalable Edge AI for Sensor Networks                | Dr. Aravind Rao     | Computer Science & Eng | 2023-06-01 | 2026-05-31
RP-2023-002  | Bio-Compatible Nanomaterials for Drug Delivery      | Dr. Sunita Kulkarni | Chemical Engineering   | 2023-08-15 | 2026-08-14
RP-2024-001  | High-Efficiency Perovskite Tandem Solar Cells       | Dr. Rajesh Iyer     | Electrical Engineering | 2024-01-10 | 2027-01-09
```

### Q15: Grant Utilization by Budget Head
```sql
SELECT bh.head_name, SUM(gba.allocated_amount) AS total_allotted,
       COALESCE(SUM(e.amount), 0) AS total_expended,
       ROUND(COALESCE(SUM(e.amount), 0) / SUM(gba.allocated_amount) * 100, 2) AS util_pct
FROM grant_budget_allocation AS gba
JOIN budget_head AS bh ON bh.head_id = gba.head_id
LEFT JOIN expenditure AS e ON e.grant_id = gba.grant_id AND e.head_id = gba.head_id
GROUP BY bh.head_id, bh.head_name ORDER BY total_allotted DESC;
```
*Sample Output:*
```text
head_name   | total_allotted | total_expended | util_pct
Equipment   | 28500000.00    | 19420000.00    | 68.14%
Manpower    | 16400000.00    | 11250000.00    | 68.60%
Consumables | 8900000.00     | 6180000.00     | 69.44%
Travel      | 4200000.00     | 2540000.00     | 60.48%
Contingency | 3100000.00     | 1870000.00     | 60.32%
Overheads   | 5100000.00     | 3825000.00     | 75.00%
```

### R2: Analytical Budget Utilization Summary
*Report Query:* `CALL sp_report_r2_budget_utilization(NULL, NULL, 'ADMIN', 1);`  
*Sample Output (Top 3 Grants):*
```text
grant_number   | project_code | agency_name | grant_amount | total_spent | balance     | util_pct
SERB/2023/00142| RP-2023-001  | SERB        | 3800000.00   | 3111500.00  | 688500.00   | 81.9%
DBT/2023/512   | RP-2023-002  | DBT         | 5200000.00   | 3420000.00  | 1780000.00  | 65.8%
MNRE/2024/09   | RP-2024-001  | MNRE        | 6400000.00   | 4150000.00  | 2250000.00  | 64.8%
```

---

## 4. Manual UI Workflow Verification Checklist

All interactive operations were verified in the live running Flask application with authentic user credentials.

| Workflow Step | Actor Role | Input Data / Action | Expected Result | Verified Result | Status |
|:---|:---|:---|:---|:---|:---:|
| **1. Authentication** | All Roles | Enter username & password on `/login` | Successful sign-in, redirect to `/dashboard`, user chip shows role badge | Verified for admin, officer, pi_rao, and viewer | **PASS** |
| **2. Register Project** | `ADMIN` | Code `RP-2025-081`, Title "Deep Optical Computing", Dept: CSE, PI: Dr. Aravind Rao (25%) | sp_register_project creates project and initial PI atomically; redirects to `/projects/<id>` | Project registered; PI assigned with 25% workload; status 'Proposed' | **PASS** |
| **3. Assign Investigator** | `RESEARCH_OFFICER` | Researcher: Dr. Sunita Kulkarni, Role: Co-PI, Effort: 15% | Added to team table; researcher workload incremented | Team modal updates; total effort updated; audit logged | **PASS** |
| **4. Add Grant Wizard** | `ADMIN` | Grant `GA-2025-01`, Agency: DST, ₹ 40,00,000, multi-head allocation | All heads validated to equal grant amount; created with status 'Sanctioned' | Grant created; head breakdown visible on grant detail page | **PASS** |
| **5. Add Milestone** | `RESEARCH_OFFICER`| Title: "Phase 1 Benchmarking", Target: within project dates | Milestone created with status 'Pending' | Visible on project detail milestone tracker timeline | **PASS** |
| **6. Successful Expense** | `RESEARCH_OFFICER`| Grant: 1, Head: Consumables, Amount: ₹ 12,000, Voucher: `V-2025-099` | sp_record_expenditure verifies balance, deducts spend, updates running balance | Expenditure logged; voucher saved; statement shows balance | **PASS** |
| **7. Blocked Expense** | `RESEARCH_OFFICER`| Grant: 1, Head: Consumables, Amount: ₹ 90,00,000 (exceeds balance) | Transaction rolled back; user receives "Expense exceeds allocated head balance (rule BR-06)" | Red alert toast displayed; no voucher recorded; audit untouched | **PASS** |
| **8. Link Publication** | `PI` | DOI: `10.1109/TMC.2025.1098765`, Title: "Edge Inference", Author: Dr. Aravind Rao | Publication recorded, linked to project, author attribution order 1 | Publication appears on project detail and researcher profile | **PASS** |
| **9. Run Reports (R1-R10)**| `ADMIN` / `VIEWER` | Click report cards in `/reports`, test CSV export & filters | Interactive Chart.js rendered; data table sorted; CSV downloaded | All 10 reports rendered smoothly; VIEWER receives redacted aggregate views | **PASS** |
