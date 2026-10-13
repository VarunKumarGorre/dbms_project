# RPGMS Role-Based User Guide

**System:** Research Project, Publication & Grant Management System (RPGMS)  
**Portal URL:** `http://127.0.0.1:5001`  
**Authentication Scheme:** Role-Based Access Control (RBAC) across 4 defined tiers: `ADMIN`, `RESEARCH_OFFICER`, `PI`, and `VIEWER`.

---

## 1. System Administrator (`ADMIN`)

### Role Scope & Permissions
- Full read and write authority across all 12 system blueprints.
- Exclusive access to User Account provisioning and role assignments (`/admin/users`).
- Full access to the institutional forensic audit trail (`/admin/audit`).
- Protection: The system enforces a strict invariant preventing the deactivation or demotion of the last remaining active Administrator.

### Key Workflows & Step-by-Step Instructions

#### 1.1 Managing User Accounts & Provisioning
1. Navigate to **Administration > Users** in the sidebar (`/admin/users`).
2. To create a new user:
   - Click **+ New User Account** in the top action bar.
   - Enter a unique username, full display name, valid email, and temporary password.
   - Select the assigned Role (`ADMIN`, `RESEARCH_OFFICER`, `PI`, or `VIEWER`).
   - If assigning role `PI`, select the linked faculty member from the **Linked Researcher** dropdown.
   - Click **Create User**.
3. To update roles or deactivate a user:
   - Locate the user row in the table.
   - Use the status toggle button or edit modal. Deactivating the active admin account is blocked by the system with a red alert.
*(Reference Screenshot: `docs/screens/admin_users_desktop.png`)*

#### 1.2 Inspecting the Forensic Audit Log
1. Navigate to **Administration > Audit Log** (`/admin/audit`).
2. Filter entries by Table (`project`, `grant_award`, `expenditure`), Action (`INSERT`, `UPDATE`, `DELETE`), or Date Range.
3. Click any row or the **View Changes** button to view a side-by-side modal displaying the exact previous state (`old_values`) and subsequent state (`new_values`).
*(Reference Screenshot: `docs/screens/admin_audit_desktop.png`)*

---

## 2. Research Officer (`RESEARCH_OFFICER`)

### Role Scope & Permissions
- Complete operational lifecycle management across all departments.
- Creating projects, assigning team investigators, creating grants, recording vouchers, managing milestones, and recording publications and patents.
- Read access to all operational data and reports.
- Restricted from modifying user credentials or viewing the admin audit trail.

### Key Workflows & Step-by-Step Instructions

#### 2.1 Registering a New Research Project
1. Navigate to **Projects > New Project** (`/projects/new`).
2. Complete Step 1 (Project Metadata):
   - Enter a unique Project Code following the institutional format `RP-YYYY-NNN` (e.g., `RP-2025-081`).
   - Enter the full project title and comprehensive abstract.
   - Select the hosting academic department.
3. Complete Step 2 (Schedule):
   - Choose Start Date and End Date (End date must be strictly after Start date, enforcing rule `BR-01`).
4. Complete Step 3 (Initial Principal Investigator):
   - Type researcher name into the autocomplete typeahead input. Only active researchers are permitted (`BR-12`).
   - Set the PI's allocated effort percentage (1% to 100%).
5. Click **Register Project**. The atomic procedure `sp_register_project` registers the project and initial PI record simultaneously.
*(Reference Screenshot: `docs/screens/projects_new_desktop.png`)*

#### 2.2 Awarding a Grant with Budget Head Allocation
1. Navigate to **Grants > New Grant** (`/grants/new`).
2. Select the target project and the funding agency.
3. Enter the total sanctioned amount (e.g. ₹ 45,00,000.00) and dates (Sanction, Start, End).
4. In Section 2, allot funds across the standardized budget heads (Equipment, Manpower, Consumables, Travel, Contingency, Overheads).
5. Ensure the live allocation meter displays **Balanced (100%)**. Enforcing rule `BR-09`, if the head allocations do not sum exactly to the grant amount, submission is rejected.
6. Click **Create Grant Award**.
*(Reference Screenshot: `docs/screens/grants_new_wizard_desktop.png`)*

#### 2.3 Recording a Vouchered Financial Disbursement
1. Navigate to **Expenditure > Record Expense** (`/expenditure/new`).
2. Select the target active Grant and the specific Budget Head.
3. Enter the voucher number, expense date, description, and expense amount.
4. Click **Record Expenditure**.
   - *Success Case:* If the expense amount is less than or equal to the remaining balance for that head, the transaction commits, updates the running balance, and redirects to the Statement of Expenditure.
   - *Blocked Case (Overspend):* If the expense exceeds the remaining balance, the transaction rolls back, and the UI displays an alert: `"Expense exceeds allocated head balance (rule BR-06)"`.
*(Reference Screenshot: `docs/screens/expenditure_entry_desktop.png`)*

---

## 3. Principal Investigator (`PI`)

### Role Scope & Permissions
- Scoped project dashboard displaying grants, expenditures, and deliverables for projects where the logged-in PI is an appointed team member.
- Real-time access to the Statement of Expenditure and running balances for their own grants.
- Authority to update milestone deliverable statuses for their own projects.
- Authority to link publications and patents acknowledging their projects.
- Restricted: Access to other PIs' projects or unassigned grants is strictly blocked with HTTP 403 Forbidden.

### Key Workflows & Step-by-Step Instructions

#### 3.1 Monitoring Project Finances & Running Ledger
1. Sign in as a PI (e.g., `pi_rao` / `password123`).
2. From the Dashboard, select your project or click **Projects** to view your assigned projects.
3. Open the project detail page (`/projects/<id>`) and switch to the **Grants** tab.
4. Click **View Statement** on any grant to inspect the chronological Statement of Expenditure ledger (`/expenditure/statement/<id>`).
5. Review the running balance after each voucher disbursement. Click **Download CSV** to export an official expenditure statement for audit submission.
*(Reference Screenshot: `docs/screens/expenditure_statement_desktop.png`)*

#### 3.2 Updating Milestone Deliverables
1. On your project detail page, switch to the **Milestones** tab (`/projects/<id>?tab=milestones`).
2. Review the chronological milestone timeline with color-coded status badges (`Pending`, `In Progress`, `Completed`, `Delayed`).
3. Click the status button on any pending milestone to open the update modal.
4. Select `Completed` and input the completion date. The system enforces rule `BR-13`, ensuring completed milestones record a completion date.
*(Reference Screenshot: `docs/screens/project_tab_milestones_desktop.png`)*

#### 3.3 Registering a Project Publication
1. Navigate to **Publications > New Publication** (`/publications/new`).
2. Enter publication details (Title, Type, Venue, Publication Date, Indexing).
3. Provide the DOI in standard format (e.g., `10.1109/TMC.2025.1098765`, enforcing `BR-08`).
4. In the Authors section, add co-authors and assign the author sequence order (`BR-18`).
5. Select your research project from the linked project list (`BR-16`).
6. Click **Record Publication**.
*(Reference Screenshot: `docs/screens/publications_new_desktop.png`)*

---

## 4. Institutional Auditor / Executive (`VIEWER`)

### Role Scope & Permissions
- Executive read-only visibility into institutional KPIs, aggregate trends, and analytical reports (R1 through R10).
- High-level executive dashboard showing total active projects, institutional funding totals, and overall disbursement velocity.
- Privacy & Redaction: Under strict data protection policies, individual researcher names, staff salaries, and row-level operational project codes are automatically redacted from all HTML tables, JSON responses, and CSV exports.
- Restricted: Any attempt to access operational creation routes (`/projects/new`, `/grants/new`, `/expenditure/new`, etc.) results in HTTP 403 Forbidden.

### Key Workflows & Step-by-Step Instructions

#### 4.1 Reviewing the Executive Dashboard
1. Sign in as `viewer` / `password123`.
2. Review top-level KPI cards: Active Projects Count, Total Sanctioned Funding, Disbursed Capital, and Output Counts.
3. Inspect interactive Chart.js visualizations: Budget Utilization by Funding Agency and Expenditure Category Breakdown.
*(Reference Screenshot: `docs/screens/dashboard_desktop.png`)*

#### 4.2 Generating Institutional Analytical Reports (R1–R10)
1. Navigate to **Analytical Reports** in the sidebar (`/reports`).
2. Choose from the 10 standardized institutional reports:
   - **R1:** Executive Project Portfolio Summary
   - **R2:** Detailed Budget Utilization Report
   - **R3:** Milestone Delivery Performance Tracker
   - **R4:** Researcher Scholarly Output & Citation Matrix
   - **R5:** Departmental Comparative Performance Matrix
   - **R6:** Financial Overspend & Burn-Rate Audit
   - **R7:** Funding Agency Strategic Investment Portfolio
   - **R8:** Patent & Intellectual Property Commercialization Tracker
   - **R9:** Comprehensive Grant Financial Closeout Statement
   - **R10:** Compliance & Overdue Periodic Report Tracker
3. Use the filter bar to isolate specific agencies, academic departments, or financial years.
4. View interactive Chart.js distribution graphs and sticky sortable data tables.
5. Click **Export CSV** to download sanitized, auditor-ready datasets.
*(Reference Screenshots: `docs/screens/reports_hub_desktop.png`, `docs/screens/report_r2_desktop.png`)*

---

## 5. UI Features & Accessibility

- **Theme Toggle:** Switch between Light Mode and Dark Mode instantly using the theme toggle in the top navigation bar. Preferences persist across sessions via browser local storage. *(Reference: `docs/screens/dashboard_dark.png`)*
- **Responsive Navigation:** On tablet and mobile screens (viewport <= 768px), the desktop sidebar collapses into a slide-out navigation drawer accessible via the top-left hamburger menu. *(Reference: `docs/screens/mobile_drawer_open.png`)*
- **Typeahead Autocomplete:** Form inputs for researchers, projects, and budget heads feature debounced typeahead suggestions powered by `/api/search`.
- **Keyboard Navigation:** Full tab order compliance, visible focus rings, and skip-to-content links ensure standard accessibility compliance.
