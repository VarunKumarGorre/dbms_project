# RPGMS Technical Viva & Oral Defense Preparation Guide

**Project:** Research Project, Publication & Grant Management System (RPGMS)  
**Database Architecture:** Relational (MySQL 8.0+/9.0+), 3NF, InnoDB engine, strict ACID transactions  
**Application Stack:** Python 3.14 + Flask 3.1, Jinja2, Vanilla JavaScript, Custom Design System  

This guide provides 30 technical questions and authoritative, plain-language answers covering relational modeling, normal forms, transaction isolation, concurrency control, trigger-procedure architecture, and indexing strategies.

---

### Section 1: Relational Modeling & Schema Design

#### Q01: Why is the grant entity named `grant_award` rather than simply `grant`?
**Answer:** `GRANT` is an ANSI SQL and MySQL reserved keyword used for Data Control Language (DCL) statements (e.g., `GRANT SELECT ON...`). Naming a table `grant` requires all queries, views, procedures, and ORMs to escape the table name with backticks (`` `grant` ``), which is highly prone to syntax bugs, migration failures, and parser errors. Naming the table `grant_award` adheres to SQL naming best practices and accurately reflects the domain concept of a sanctioned financial award.

#### Q02: What is the purpose of the composite foreign key on `expenditure (grant_id, head_id)` referencing `grant_budget_allocation (grant_id, head_id)`?
**Answer:** A simple foreign key from `expenditure` to `budget_head(head_id)` would only prove that the expense category exists globally in the university. It would NOT verify that the specific grant was actually allotted money for that particular budget head. By enforcing a composite foreign key referencing `grant_budget_allocation(grant_id, head_id)`, the relational engine guarantees at the schema level (BR-15) that an expense can only ever be booked against a head that has an approved allocation on that specific grant award.

#### Q03: Why does `project_investigator` have a surrogate/composite key structure, and how is the single-PI rule enforced?
**Answer:** A project can have multiple investigators (Co-PIs, Researchers), but only one Principal Investigator (PI) at any given point in time (BR-10). The table uses a primary key of `(project_id, researcher_id)`. The single-PI constraint is enforced in the database via a unique functional/conditional index (`UNIQUE KEY uq_one_pi_per_project (project_id, (CASE WHEN role = 'PI' THEN 1 ELSE NULL END))`). In SQL, multiple `NULL` values are permitted in a unique index, ensuring only one row per `project_id` can have `role = 'PI'`.

#### Q04: Why is researcher effort capped at 100%, and how is it calculated across multiple projects?
**Answer:** Faculty and research staff have finite full-time equivalent (FTE) commitments. Under BR-11, a researcher's cumulative active project allocation cannot exceed 100%. This is calculated across all `project_investigator` rows where the associated project status is 'Active' or 'Proposed'. The validation is enforced both via triggers before insert/update and verified inside the `sp_assign_investigator` procedure.

#### Q05: Why is the `report` entity separate from `milestone`?
**Answer:** A milestone represents a technical deliverable (e.g., "Prototype Fabrication" or "Alpha Software Release") tied to project schedules. A report is an official administrative/compliance document submitted to funding agencies or internal review bodies (e.g., "Quarterly Progress Report", "Annual Utilization Certificate", or "Final Project Technical Report"). Reports have distinct lifecycles (`Draft`, `Submitted`, `Approved`, `Rejected`), due dates, submission dates, and file references.

---

### Section 2: Normalization & Functional Dependencies

#### Q06: What is Third Normal Form (3NF), and how does the RPGMS schema satisfy it?
**Answer:** A relation is in 3NF if and only if it is in 2NF (all non-key attributes are fully functionally dependent on the primary key) and no non-key attribute is transitively dependent on the primary key ($X \to Y \to Z$). In RPGMS:
1. Every table has a primary key with atomic attributes (1NF).
2. Associative tables (`project_investigator`, `grant_budget_allocation`, `publication_author`) have no partial dependencies on subsets of composite keys (2NF).
3. Derived financial figures (e.g., `total_spent`, `remaining_balance`, `utilization_percentage`) are calculated dynamically through views (`vw_budget_utilization`) rather than stored in tables, preventing transitive dependencies and update anomalies (3NF).

#### Q07: Did you deliberately denormalize any entity in RPGMS? Why or why not?
**Answer:** No tables were denormalized. Total spend and balance are computed dynamically using aggregated views or stored procedure queries. For auditability and forensic tracking, the `audit_log` table stores JSON snapshots of `old_values` and `new_values`. Storing JSON in audit logs is not considered denormalization of operational data; it is an append-only event-sourcing pattern that preserves historical state regardless of subsequent operational schema changes.

#### Q08: How are many-to-many relationships modeled between Projects, Publications, and Patents?
**Answer:** In academic institutions, a publication or patent may acknowledge multiple funding grants or research projects, and a single project produces multiple papers and patents. We model these using bridge/junction tables: `project_publication(project_id, publication_id)` and `project_patent(project_id, patent_id)`. Both bridge tables enforce composite primary keys and foreign keys with `ON DELETE CASCADE`.

#### Q09: What is the author attribution model in `publication_author`?
**Answer:** In scientific publishing, author sequence matters (e.g., First Author, Corresponding Author). `publication_author` maintains `(publication_id, researcher_id)` as the primary key, along with `author_order TINYINT UNSIGNED` and `is_corresponding BOOLEAN`. We enforce `UNIQUE (publication_id, author_order)` (BR-18) so no two co-authors can claim the same position on the author list.

#### Q10: How does the schema handle historical record retention when a researcher leaves the university?
**Answer:** Inactive researchers have `is_active = FALSE` (BR-12). Inactive researchers cannot be assigned to new projects or grants. However, their historical publications, patents, completed projects, and voucher logs remain intact because foreign keys use `ON DELETE RESTRICT` rather than cascading deletes, preserving institutional audit integrity.

---

### Section 3: Transactions, Locking & Concurrency Control

#### Q11: What is the ACID property, and how is it maintained in RPGMS?
**Answer:**
- **Atomicity:** Ensured via `START TRANSACTION`, `COMMIT`, and `ROLLBACK` within stored procedures. If any step fails (e.g., allocation sum validation in grant creation), the entire operation rolls back.
- **Consistency:** Maintained by schema-level constraints (`CHECK`, `FOREIGN KEY`, `UNIQUE`) and native triggers.
- **Isolation:** Configured to `READ COMMITTED` across all write procedures, preventing dirty reads while eliminating unnecessary phantom read deadlocks.
- **Durability:** Guaranteed by MySQL InnoDB's write-ahead redo log (`ib_logfile`) and binary logging.

#### Q12: Why use transaction-owning stored procedures instead of application-level multi-step SQL?
**Answer:** Executing multi-step financial logic across application-to-database round trips exposes the system to network latency, partial failures, and race conditions. By encapsulating registration, grant creation, and expenditure entry inside `SQL SECURITY DEFINER` stored procedures, all validation, row locks, writes, and commits occur within a single database server process in microseconds. Furthermore, applications cannot accidentally bypass business rules.

#### Q13: What happens when two users attempt to record an expenditure against the last ₹ 5,000 of a grant simultaneously?
**Answer:** Without concurrency control, a classic **Time-of-Check to Time-of-Use (TOCTOU)** race condition occurs, resulting in double-spending (overspending the grant). In `sp_record_expenditure`, we execute:
```sql
SELECT g.grant_amount, ... FROM grant_award AS g WHERE g.grant_id = p_grant_id FOR UPDATE;
SELECT gba.allocated_amount, ... FROM grant_budget_allocation AS gba WHERE ... FOR UPDATE;
```
The first transaction acquires an exclusive row lock (`FOR UPDATE`). The second transaction blocks and waits. When the first transaction commits, the second transaction acquires the lock, re-reads the updated total spend, detects that the remaining balance is ₹ 0, and triggers `SIGNAL SQLSTATE '45000'` with rule `BR-06: Expense exceeds allocated head balance`. Exactly one transaction succeeds, and overspending is impossible.

#### Q14: Why can't `CHECK` constraints or native triggers enforce BR-06 (Expenditure Budget Limit)?
**Answer:**
1. A `CHECK` constraint can only inspect the columns of the single row being inserted; it cannot query other rows or aggregate tables.
2. In MySQL, executing queries against the mutating table inside a trigger on that same table causes Error 1442 (Mutating Table Error).
3. Triggers do not acquire explicit row-level mutex locks (`FOR UPDATE`) on parent grant records, meaning concurrent requests can both pass trigger validation before either has inserted its row. Only stored procedures with explicit row locking can serialize concurrent disbursements safely.

#### Q15: Why is `READ COMMITTED` chosen over `REPEATABLE READ` or `SERIALIZABLE`?
**Answer:** `REPEATABLE READ` in InnoDB relies on Next-Key Locking (record locks plus gap locks). In high-frequency transactional systems, gap locking on range scans frequently causes deadlocks between concurrent inserts. `READ COMMITTED` eliminates gap locking for ordinary searches, locking only the exact indexed rows inspected, while explicit `FOR UPDATE` clauses ensure strict serializability where financial balances are mutated.

---

### Section 4: Triggers, Stored Procedures & Business Rules

#### Q16: When should business logic be placed in a Trigger versus a Stored Procedure?
**Answer:**
- **Triggers** are best for invariant checks that must apply to ALL direct DML statements regardless of source (e.g., date bounds checking `BR-01`, `BR-02`, status transitions `BR-14`, and automatic audit logging).
- **Stored Procedures** are best for multi-table business transactions that own a lifecycle (e.g., creating a project and assigning its first PI atomically, creating a grant and distributing its multi-head budget, or locking and disbursing funds).

#### Q17: How is the forensic audit trail implemented, and why is it tamper-resistant?
**Answer:** The `audit_log` table tracks `table_name`, `record_id`, `action (INSERT/UPDATE/DELETE)`, `old_values (JSON)`, `new_values (JSON)`, `changed_by (user_id)`, and `changed_at (TIMESTAMP)`. It is populated automatically by native `AFTER INSERT/UPDATE/DELETE` triggers across all operational tables. Before executing queries, the application sets session variables (`@app_user_id`, `@app_username`). If an attacker directly modifies rows via MySQL workbench or command line, the triggers still fire and log the modification with actor `system`.

#### Q18: What is Rule BR-17 (Closed Project Immutability) and how is it enforced?
**Answer:** Once a project's status transitions to 'Completed' or 'Cancelled', its operational history is sealed. No new grant awards, budget allocations, milestones, or expenditures can be logged. This is enforced in both `sp_record_expenditure` and trigger `trg_chk_proj_closed_exp` by checking the parent project status before permitting an insert.

#### Q19: How is DOI uniqueness and format enforced (BR-08)?
**Answer:** `doi` is declared with a unique constraint `UNIQUE (doi)`. In addition, a `CHECK` constraint enforces the international Digital Object Identifier regex syntax:
```sql
CONSTRAINT chk_pub_doi CHECK (doi IS NULL OR doi REGEXP '^10\\.[0-9]{4,9}/.+$')
```
This guarantees invalid strings (e.g. `xyz`, `http://...`) are rejected before insertion.

#### Q20: What is Rule BR-16 (Publication Date Relative to Project)?
**Answer:** When linking a publication to a research project via `project_publication`, the publication date must not be earlier than the project start date minus a grace window (e.g., 6 months for preliminary work). Trigger `trg_chk_proj_pub_date_ins` inspects the project's `start_date` and signals SQLSTATE 45000 if the publication predates the project inception.

---

### Section 5: Indexing Strategy & Query Optimization

#### Q21: What are clustered and secondary indexes in MySQL InnoDB?
**Answer:**
- **Clustered Index:** In InnoDB, the primary key is the clustered index. The leaf pages of the clustered B+ Tree contain the actual row data. Table data is physically sorted by the primary key.
- **Secondary Index:** Any non-primary index. The leaf pages of a secondary index store the indexed column values and the clustered index key (primary key pointer). A secondary index lookup requires a secondary index seek followed by a primary key lookup (bookmark lookup), unless it is a covering index.

#### Q22: What is a Covering Index, and where is it used in RPGMS?
**Answer:** A covering index is an index that contains all columns requested by a query, allowing MySQL to fulfill the query directly from the B+ Tree without reading the base table rows (`Using index` in `EXPLAIN`). In RPGMS, index `idx_exp_grant_head_amount_date` on `expenditure(grant_id, head_id, amount, expense_date)` covers aggregate queries like:
```sql
SELECT head_id, SUM(amount) FROM expenditure WHERE grant_id = 1 GROUP BY head_id;
```
This query executes entirely in memory from the index leaf nodes.

#### Q23: Why do we index foreign key columns explicitly in MySQL?
**Answer:** MySQL automatically creates indexes on foreign keys, but optimizing join performance and preventing table locks during parent table deletions requires explicit indexing. In composite foreign keys like `(grant_id, head_id)`, the leftmost prefix rule means queries filtering by `grant_id` utilize the index, but queries filtering solely by `head_id` require an independent index on `head_id`.

#### Q24: How does the Leftmost Prefix Rule affect composite index design?
**Answer:** For a composite index on `(A, B, C)`, MySQL can use the index for queries filtering on `(A)`, `(A, B)`, or `(A, B, C)`. It CANNOT use the index efficiently for queries filtering solely on `(B)` or `(C)` because the B+ Tree is ordered primarily by `A`. In RPGMS, index `idx_ms_proj_status_target` on `milestone(project_id, status, target_date)` supports queries filtering by project, or by project and status, and avoids file-sorts when ordering by `target_date`.

#### Q25: How do you verify an index is working using `EXPLAIN`?
**Answer:** Prefix the SQL statement with `EXPLAIN` or `EXPLAIN FORMAT=JSON`. Key indicators:
1. `type`: Should be `ref`, `eq_ref`, or `range`; NOT `ALL` (full table scan).
2. `key`: Shows the index chosen by the cost-based optimizer (e.g., `idx_proj_dept_status`).
3. `rows`: Shows the estimated number of rows examined; lower is better.
4. `Extra`: `Using index` indicates a covering index; `Using filesort` or `Using temporary` indicates potential query tuning opportunities.

---

### Section 6: Security, Roles & Architecture

#### Q26: What are the 4 user roles in RPGMS and how are their boundaries enforced?
**Answer:**
1. **ADMIN:** Unrestricted operational and system access, user provisioning, and full forensic audit log viewer.
2. **RESEARCH_OFFICER:** Operational data entry across all departments and projects (projects, grants, milestones, expenditures, publications, patents, reports); cannot modify user credentials or tamper with audit logs.
3. **PI (Principal Investigator):** Scoped access; can only view and manage projects, grants, expenditures, and publications where they are an assigned team member.
4. **VIEWER:** Executive / auditor access; restricted to high-level dashboards and analytical reports (R1–R10); zero access to operational write routes; row-level financial details and researcher names are redacted into aggregate metrics.

#### Q27: How is SQL injection prevented in the application?
**Answer:** The application strictly forbids dynamic SQL concatenation with user input. All database operations in `app/db.py` use parameterized queries with tuple parameters (`cursor.execute(sql, params)`), passing arguments out-of-band directly to the MySQL binary protocol. Stored procedures accept strongly typed parameters (`INT`, `VARCHAR`, `DECIMAL`), ensuring user input is treated as literal data and never executable code.

#### Q28: How does the application prevent Cross-Site Scripting (XSS) and CSRF?
**Answer:**
- **XSS:** Jinja2 templates auto-escape all HTML entities by default (`{{ var }}`). Any user input containing `<script>` or HTML tags is rendered safely as escaped text.
- **CSRF:** All mutating forms (`POST`) require a hidden CSRF token verified via `flask_wtf.csrf.CSRFProtect`. Sessions use `HttpOnly`, `SameSite=Lax` cookie flags.

#### Q29: What is the architectural role of SQL Views (`vw_*`) in RPGMS?
**Answer:** SQL Views encapsulate complex, multi-table joins, aggregations, and business metrics (e.g. `vw_budget_utilization`, `vw_project_progress`). They provide a clean, consistent data interface for both Flask services and external analytical reporting tools. This prevents duplicate SQL logic across blueprints and ensures that financial definitions (such as budget utilization percentage) remain single-source-of-truth definitions maintained within the database engine.

#### Q30: Why does the system maintain zero Docker or container dependencies?
**Answer:** The project specification strictly mandates a transparent, bare-metal local development environment running against native Homebrew MySQL on macOS. Containers abstract networking, filesystem permissions, and service lifecycles in ways that often obscure core database fundamentals during evaluation. Developing directly against native MySQL ensures direct visibility into connection pooling, process threads, file storage, and transactional locking.
