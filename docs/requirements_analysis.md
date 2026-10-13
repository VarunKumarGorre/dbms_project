# Requirements Analysis & Specification

## 1. Problem Statement

University research offices oversee numerous sponsored projects, grants, faculty investigators, deliverables, research publications, and patent filings. Historically, these records were managed across disparate spreadsheets and siloed administrative trackers. This fragmented record-keeping leads to severe operational deficiencies:
- **Budget Overspending:** Difficulties in tracking real-time line-item balances across distinct budget heads (Equipment, Manpower, Travel, etc.), risking unapproved over-expenditure and audit rejection.
- **Milestone Slippage:** Poor visibility into project delivery timelines, overdue milestones, and delayed technical reports.
- **Effort Tracking Conflicts:** Faculty members committed to multiple projects exceeding 100% aggregate effort capacity.
- **Reporting Inefficiencies:** Manual collation of analytical summaries for accreditation bodies, funding agencies, and university management.
- **Authorization Gaps:** Lack of role-scoped data isolation between research office administrators, project investigators, and external evaluators.

The **Research Project, Publication & Grant Management System (RPGMS)** solves these problems by providing an integrated relational database and web management portal enforcing strict data integrity, automated accounting constraints, and role-based access control.

---

## 2. Stakeholders & User Roles

| Role | Description | Core Capabilities & Permissions |
|---|---|---|
| **ADMIN** | System Administrator / Research Dean | Full administrative authority across all modules: user management, security audit log inspection, system-wide CRUD on all entities. |
| **RESEARCH_OFFICER** | Research Project Management Officer | Operational administration: project registration, grant entry, budget allocation, expenditure verification, milestone scheduling, and analytical reporting. Cannot manage user accounts or view raw audit logs. |
| **PI (Principal Investigator)** | Faculty member leading research projects | Scoped access: view and manage own projects, track team effort, complete project milestones, link publications/patents, submit project periodic reports, inspect own grant balances. Forbidden from viewing unrelated projects. |
| **VIEWER** | External Evaluator / Auditor / Guest | Read-only aggregate insights: high-level dashboard summaries and sanitized analytical reports (R1–R10). Record-level operational routes and individual identifiers are strictly redacted. |

---

## 3. Functional Requirements

### 3.1 Project & Investigator Management
- **FR-01 (Project Registration):** Register research projects with unique formatted project codes (`RP-YYYY-NNN`), duration dates, department host, and an initial Principal Investigator (PI) assigned atomically.
- **FR-02 (Team Allocation):** Assign faculty, postdocs, and scholars to project teams with designated roles (Co-PI, Researcher, Research Scholar) and committed effort percentages (1–100%).
- **FR-03 (Effort Validation):** Ensure a researcher's cumulative effort across all Proposed and Active projects does not exceed 100%. Inactive researchers cannot be assigned.
- **FR-04 (Single PI Invariant):** Ensure every project has exactly one active PI at any given time. Transfers of PI responsibilities must execute as an atomic handoff.

### 3.2 Grants & Budget Allocation
- **FR-05 (Grant Sanctioning):** Record external grants linked to projects, specifying the funding agency, sanction date, validity period, and total sanction amount. Grant validity must reside within project lifetime.
- **FR-06 (Budget Head Allocation):** Allocate sanctioned grant funds across standardized budget heads (Equipment, Consumables, Travel, Manpower, Contingency, Overheads). The sum of allocations must not exceed the total grant sanction.
- **FR-07 (Grant Protection):** Disallow reducing a grant's sanctioned total below its committed allocations or actual expenditures.

### 3.3 Expenditure Accounting
- **FR-08 (Expenditure Recording):** Record real-world expenses against specific grant budget heads with verified voucher numbers, descriptions, and dates within the active grant period.
- **FR-09 (Overspend Prevention):** Enforce hard database-level locking and balance checks so expenditure on any head cannot exceed its allocated budget, and total grant spend cannot exceed the grant sanction amount.
- **FR-10 (Statement Generation):** Generate running-balance financial statements for any grant showing voucher transactions and remaining balances.

### 3.4 Milestones & Technical Reports
- **FR-11 (Milestone Tracking):** Define project deliverables with target due dates within project bounds. Track status (Pending, In Progress, Completed, Delayed). Overdue milestones are flagged dynamically.
- **FR-12 (Completion Integrity):** Mark milestones completed with explicit completion dates. Completed milestones cannot be created on closed projects.
- **FR-13 (Project Reporting):** Submit periodic progress, financial, and utilization reports with drafting, submission, review, acceptance, and return workflows.

### 3.5 Publications & Intellectual Property
- **FR-14 (Publication Catalogue):** Catalogue research outputs (Journals, Conferences, Books) with peer-review indexing (Scopus, SCI, SCIE, WoS), validated DOIs, and ordered author lists.
- **FR-15 (Project Attribution):** Link published works to sponsoring projects, ensuring publication dates post-date project initiation.
- **FR-16 (Patent Tracking):** Register patents with jurisdiction and filing status (Filed, Published, Granted, Rejected, Lapsed). Granted patents strictly require registration numbers and grant dates.

### 3.6 Analytics & Audit
- **FR-17 (Analytical Reports R1–R10):** Compute standardized analytical reports: Project Progress (R1), Budget Utilization (R2), Milestone Tracker (R3), Researcher Output (R4), Agency Portfolio (R5), Publications Report (R6), Department Summary (R7), Expenditure Statement (R8), Patent Status (R9), and Project Closing Summary (R10).
- **FR-18 (Viewer Redaction):** Redact record-level identifiers, individual names, voucher numbers, and DOIs from VIEWER report queries, charts, and CSV downloads.
- **FR-19 (Audit Logging):** Record automated audit trails for table mutations with JSON snapshots of previous and updated row states, authenticated actor identity, and timestamps.

---

## 4. Non-Functional Requirements

- **NFR-01 (Data Integrity):** Normalization to 3NF/BCNF. All business constraints enforced directly within MySQL using CHECK constraints, generated unique columns, triggers, foreign keys, and stored procedures.
- **NFR-02 (Concurrency & Transactions):** ACID transaction guarantees with row-level locking (`SELECT ... FOR UPDATE` under `READ COMMITTED`) to eliminate race conditions during concurrent budget expenditures and team assignments.
- **NFR-03 (Performance & Indexing):** Indexed access paths for frequent foreign-key joins, status/date filters, and FULLTEXT search for research titles and abstracts. Sub-second response times across all views.
- **NFR-04 (Security & Least Privilege):** Web application connects using a least-privileged database role (`rpgms_app`) denied direct DML on critical financial and project tables. Passwords hashed using bcrypt. CSRF protection on all mutating POST requests.
- **NFR-05 (Accessibility & Usability):** Adherence to WCAG 2.1 AA accessibility: minimum 4.5:1 color contrast in both light and dark themes, keyboard navigable modals/drawers, semantic markup, and responsive layouts (1440px desktop down to 390px mobile).

---

## 5. Entity List & Conceptual Attributes (19 Entities)

1. **DEPARTMENT:** Academic department hosting researchers and projects (`dept_id`, `dept_code`, `dept_name`, `building`, `contact_email`, `created_at`).
2. **RESEARCHER:** Faculty, fellow, or scholar (`researcher_id`, `employee_code`, `first_name`, `last_name`, `email`, `phone`, `designation`, `dept_id`, `orcid_id`, `joined_date`, `is_active`).
3. **USER_ACCOUNT:** System login account (`user_id`, `username`, `password_hash`, `role`, `researcher_id`, `is_active`, `created_at`).
4. **FUNDING_AGENCY:** External sponsor (`agency_id`, `agency_name`, `agency_type`, `country`, `contact_email`, `website`).
5. **PROJECT:** Research project initiative (`project_id`, `project_code`, `title`, `abstract`, `dept_id`, `start_date`, `end_date`, `status`, `created_at`).
6. **PROJECT_INVESTIGATOR:** Project team membership (`project_id`, `researcher_id`, `role`, `assigned_date`, `effort_percent`, `pi_flag`).
7. **GRANT_AWARD:** Financial award (`grant_id`, `grant_number`, `project_id`, `agency_id`, `grant_amount`, `sanction_date`, `grant_start`, `grant_end`, `status`).
8. **BUDGET_HEAD:** Financial expense category (`head_id`, `head_name`, `description`).
9. **GRANT_BUDGET_ALLOCATION:** Line-item budget breakdown (`grant_id`, `head_id`, `allocated_amount`).
10. **EXPENDITURE:** Financial transaction (`expenditure_id`, `grant_id`, `head_id`, `expense_date`, `amount`, `description`, `voucher_no`, `recorded_by`, `created_at`).
11. **MILESTONE:** Project technical deliverable (`milestone_id`, `project_id`, `title`, `description`, `due_date`, `completed_date`, `status`).
12. **PUBLICATION:** Research paper or book (`publication_id`, `title`, `pub_type`, `venue`, `doi`, `issn_isbn`, `pub_date`, `indexing`, `citation_count`).
13. **PUBLICATION_AUTHOR:** Authorship credit (`publication_id`, `researcher_id`, `author_order`, `is_corresponding`).
14. **PROJECT_PUBLICATION:** Research output attribution (`project_id`, `publication_id`).
15. **PATENT:** Intellectual property filing (`patent_id`, `application_number`, `patent_number`, `title`, `jurisdiction`, `filing_date`, `grant_date`, `status`).
16. **PATENT_INVENTOR:** Inventorship credit (`patent_id`, `researcher_id`).
17. **PROJECT_PATENT:** IP attribution to project (`project_id`, `patent_id`).
18. **REPORT:** Formal progress/financial reporting (`report_id`, `project_id`, `report_type`, `period_start`, `period_end`, `submitted_on`, `submitted_by`, `summary`, `status`).
19. **AUDIT_LOG:** System security mutation log (`log_id`, `table_name`, `record_id`, `action`, `old_values`, `new_values`, `changed_at`, `changed_by`).
