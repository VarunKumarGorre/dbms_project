# RPGMS UI Wireframes & Layout Architecture

**Project:** Research Project, Publication & Grant Management System (RPGMS)  
**Design Philosophy:** Clean institutional aesthetic, high information density, zero generic UI kits  
**Responsive Breakpoints:** Desktop (1440px wide viewport), Mobile (390px wide viewport)  
**Color Modes:** Light Mode (default, warm slate tones), Dark Mode (deep zinc/slate background)  

---

## 1. Authentication View (`/login`)

### Wireframe (Desktop)
```text
+--------------------------------------------------------------------------+
|                                                                          |
|                     [RPGMS Emblem / Logo]                                |
|          Research Project, Publication & Grant Management                |
|                    Single Institutional Portal                           |
|                                                                          |
|              +------------------------------------------+                |
|              | Sign In                                  |                |
|              | Enter your credentials to access system  |                |
|              |                                          |                |
|              | Username                                 |                |
|              | [ admin                                ] |                |
|              |                                          |                |
|              | Password                                 |                |
|              | [ ••••••••••••                         ] |                |
|              |                                          |                |
|              | [ Sign In Button                      ] |                |
|              +------------------------------------------+                |
|                                                                          |
|           Demo Accounts: admin | officer | pi_rao | viewer              |
+--------------------------------------------------------------------------+
```
- **Desktop Screenshot:** `docs/screens/login_desktop.png`
- **Mobile Screenshot:** `docs/screens/login_mobile.png`
- **Intentional Differences / Implementation Notes:** Center-staged card with institutional deep-navy gradient backdrop, crisp autofocus inputs, clear role indicator chips for quick viva demonstrations.

---

## 2. Institutional Executive Dashboard (`/dashboard`)

### Wireframe (Desktop)
```text
+--------------------------------------------------------------------------+
| [RPGMS Logo] | Global Search [cmd+k]         | Theme [D/L] | [Admin Chip]|
+--------------+-----------------------------------------------------------+
| Dashboard    | Dashboard > Institutional Overview                        |
| Projects     |                                                           |
| Investigators| +------------+ +------------+ +------------+ +----------+ |
| Grants       | | Active Proj| | Sanctioned | | Disbursed  | | Pubs/Pat | |
| Expenditure  | |    15      | | ₹ 4.82 Cr  | | ₹ 3.12 Cr  | |  30 / 7  | |
| Milestones   | +------------+ +------------+ +------------+ +----------+ |
| Publications |                                                           |
| Patents      | +-------------------------------+ +---------------------+ |
| Reports      | | Budget Utilization by Agency  | | Expenditure Mix     | |
| Admin        | | [Interactive Chart.js Bar]    | | [Chart.js Doughnut] | |
|              | +-------------------------------+ +---------------------+ |
|              |                                                           |
|              | +-------------------------------+ +---------------------+ |
|              | | Critical Pending Milestones   | | Recent Vouchers     | |
|              | | [Table with due date badges]  | | [Audit stream table]| |
|              | +-------------------------------+ +---------------------+ |
+--------------+-----------------------------------------------------------+
```
- **Desktop Screenshot:** `docs/screens/dashboard_desktop.png`
- **Mobile Screenshot:** `docs/screens/dashboard_mobile_closed.png`
- **Dark Mode Screenshot:** `docs/screens/dashboard_dark.png`
- **Mobile Drawer Open:** `docs/screens/mobile_drawer_open.png`
- **Intentional Differences / Implementation Notes:** Chart.js containers adapt dynamically to theme changes. Metric cards include compact Indian currency formatting (₹ Cr / L) with subtext trends.

---

## 3. Project Registry & List (`/projects`)

### Wireframe (Desktop)
```text
+--------------------------------------------------------------------------+
| Projects > Directory                          [+ New Project] [Export CSV|
+--------------------------------------------------------------------------+
| Filter: [Search title, code...] [Dept: All v] [Status: Active v] [Year v]|
+--------------------------------------------------------------------------+
| Code        | Title                  | Dept | PI            | Funding/Exp|
|-------------+------------------------+------+---------------+------------|
| RP-2023-001 | Scalable Edge AI...    | CSE  | Dr. A. Rao    | 38L (81.9%)|
| RP-2023-002 | Bio-Compatible Nano... | ChE  | Dr. S. Kulk.. | 52L (65.8%)|
| RP-2024-001 | High-Efficiency Per... | EE   | Dr. R. Iyer   | 64L (64.8%)|
+--------------------------------------------------------------------------+
| Showing 1-15 of 15 projects                      [ < Page 1 of 1 > ]     |
+--------------------------------------------------------------------------+
```
- **Desktop Screenshot:** `docs/screens/projects_list_desktop.png`
- **Mobile Screenshot:** `docs/screens/projects_list_mobile.png`
- **Intentional Differences / Implementation Notes:** Mobile view stacks rows into card-like summaries with touch-friendly detail links. Progress bars represent both expenditure and schedule consumption.

---

## 4. Project Detail View (`/projects/<id>`)

### Wireframe (Desktop)
```text
+--------------------------------------------------------------------------+
| Projects > RP-2023-001                                   [Status: Active]|
| Scalable Edge AI for Sensor Networks                                     |
| Dept: Computer Science & Engineering | Duration: 01 Jun 2023 - 31 May 2026|
+--------------------------------------------------------------------------+
| [Overview] | [Team & Effort (3)] | [Grants (2)] | [Milestones (5)] | [Rep]|
+--------------------------------------------------------------------------+
| +--------------------------------------+ +-----------------------------+ |
| | Project Abstract & Description       | | Financial Breakdown         | |
| | Edge inference algorithms on low-    | | Total Sanctioned: ₹ 38.0 L  | |
| | power microcontrollers with sensor...| | Expended:         ₹ 31.1 L  | |
| |                                      | | Balance:          ₹  6.9 L  | |
| +--------------------------------------+ +-----------------------------+ |
+--------------------------------------------------------------------------+
```
- **Desktop Overview Screenshot:** `docs/screens/project_detail_desktop.png`
- **Desktop Dark Mode:** `docs/screens/project_detail_dark.png`
- **Desktop Team Tab:** `docs/screens/project_tab_team_desktop.png`
- **Desktop Grants Tab:** `docs/screens/project_tab_grants_desktop.png`
- **Desktop Milestones Tab:** `docs/screens/project_tab_milestones_desktop.png`
- **Desktop Reports Tab:** `docs/screens/project_tab_reports_desktop.png`
- **Mobile View:** `docs/screens/project_detail_mobile.png`
- **Intentional Differences / Implementation Notes:** Tab state is fully persistent via query parameter `?tab=team|grants|milestones|reports`. Modals allow instant PI change, co-PI assignment, and milestone status toggling.

---

## 5. Grant Award Wizard & Allocation (`/grants/new`)

### Wireframe (Desktop)
```text
+--------------------------------------------------------------------------+
| Grants > New Grant Award                                                 |
+--------------------------------------------------------------------------+
| 1. Grant Information                                                     |
| Grant Number: [ SERB/2025/0091           ]                               |
| Project:      [ RP-2025-001: Scalable Edge AI                          v]|
| Agency:       [ SERB - Science and Engineering Research Board          v]|
| Grant Amount: [ ₹ 45,00,000.00                                         ] |
| Sanction Date:[ 2025-01-01 ]  Start: [ 2025-01-01 ]  End: [ 2027-12-31 ] |
+--------------------------------------------------------------------------+
| 2. Budget Head Allocations (Must Sum Exactly to Grant Amount)            |
| Equipment:    [ ₹ 20,00,000.00 ]     Manpower:    [ ₹ 12,00,000.00 ]     |
| Consumables:  [ ₹  6,00,000.00 ]     Travel:      [ ₹  3,00,000.00 ]     |
| Contingency:  [ ₹  2,00,000.00 ]     Overheads:   [ ₹  2,00,000.00 ]     |
| Total Allocated: ₹ 45,00,000.00 / ₹ 45,00,000.00   [ Status: Balanced ✓] |
+--------------------------------------------------------------------------+
|                                          [ Cancel ] [ Create Grant Award]|
+--------------------------------------------------------------------------+
```
- **Desktop Screenshot:** `docs/screens/grants_new_wizard_desktop.png`
- **Detail View:** `docs/screens/grant_detail_desktop.png`
- **Intentional Differences / Implementation Notes:** Live JavaScript ticker computes the remaining unallocated balance in real-time, coloring the badge red if unbalanced and green when exactly 100% allotted.

---

## 6. Financial Disbursement & Expenditure Statement (`/expenditure/statement/<id>`)

### Wireframe (Desktop)
```text
+--------------------------------------------------------------------------+
| Statement of Expenditure: SERB/2023/00142               [Download CSV]   |
| Project: RP-2023-001 | Total Grant: ₹ 38,00,000.00                       |
+--------------------------------------------------------------------------+
| Date        | Voucher No  | Budget Head | Amount      | Balance          |
|-------------+-------------+-------------+-------------+------------------|
| 15 Jul 2023 | V-2023-001  | Equipment   | 18,50,000.00| 19,50,000.00     |
| 20 Aug 2023 | V-2023-014  | Manpower    |    45,000.00| 19,05,000.00     |
| 10 Sep 2023 | V-2023-022  | Consumables |    22,500.00| 18,82,500.00     |
+--------------------------------------------------------------------------+
| Total Expended: ₹ 31,11,500.00        Remaining Balance: ₹ 6,88,500.00   |
+--------------------------------------------------------------------------+
```
- **Desktop Screenshot:** `docs/screens/expenditure_statement_desktop.png`
- **Mobile Screenshot:** `docs/screens/expenditure_statement_mobile.png`
- **New Expense Entry:** `docs/screens/expenditure_entry_desktop.png`
- **Intentional Differences / Implementation Notes:** Implements a strict chronological running balance ledger. Overdrafts are physically blocked at the database engine level via `sp_record_expenditure`.

---

## 7. Analytical Reports Hub & Report Engines (`/reports`)

### Wireframe (Desktop)
```text
+--------------------------------------------------------------------------+
| Analytical Reports Hub                                                   |
| Institutional compliance, financial audits, and researcher output metrics|
+--------------------------------------------------------------------------+
| +-------------------------+ +-------------------------+ +--------------+ |
| | R1: Executive Summary   | | R2: Budget Utilization  | | R3: Milestone| |
| | High-level portfolio KPIs| | Grant-wise spend & head | | Schedule perf| |
| +-------------------------+ +-------------------------+ +--------------+ |
| +-------------------------+ +-------------------------+ +--------------+ |
| | R4: Researcher Output   | | R5: Departmental Matrix | | R6: Financial| |
| | Publications & citations| | Cross-dept comparisons  | | Overspend aud| |
| +-------------------------+ +-------------------------+ +--------------+ |
+--------------------------------------------------------------------------+
```
- **Reports Hub Desktop:** `docs/screens/reports_hub_desktop.png`
- **Reports Hub Mobile:** `docs/screens/reports_hub_mobile.png`
- **Report R1 Desktop:** `docs/screens/report_r1_desktop.png`
- **Report R2 Desktop:** `docs/screens/report_r2_desktop.png`
- **Report R2 Mobile:** `docs/screens/report_r2_mobile.png`
- **Report R3 Desktop:** `docs/screens/report_r3_desktop.png`
- **Intentional Differences / Implementation Notes:** Universal analytical report engine renders filter bars, interactive Chart.js visualizations, sortable sticky tables, CSV export streams, and print-ready typography. Redaction automatically masks individual identifiers for the `VIEWER` role.

---

## 8. Admin Forensic Audit Trail (`/admin/audit`)

### Wireframe (Desktop)
```text
+--------------------------------------------------------------------------+
| System Administration > Audit Log                                        |
+--------------------------------------------------------------------------+
| Filter: [Table: All v] [Action: UPDATE v] [User: All v] [Date Range    ] |
+--------------------------------------------------------------------------+
| Timestamp        | User     | Table       | Action | Changes (Diff)      |
|------------------+----------+-------------+--------+---------------------|
| 2026-10-14 00:24 | officer  | expenditure | INSERT | [View Added Data]   |
| 2026-10-13 18:40 | admin    | milestone   | UPDATE | status: In Progress |
+--------------------------------------------------------------------------+
| Showing 1-25 of 541 audit entries                  [ < Page 1 of 22 > ]  |
+--------------------------------------------------------------------------+
```
- **Audit Log Desktop:** `docs/screens/admin_audit_desktop.png`
- **Admin Users Desktop:** `docs/screens/admin_users_desktop.png`
- **Admin Users Mobile:** `docs/screens/admin_users_mobile.png`
- **Intentional Differences / Implementation Notes:** Clicking any audit entry opens an accessible modal with side-by-side color-coded JSON before/after state diffs.
