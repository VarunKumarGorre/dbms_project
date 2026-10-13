# FINAL_RPGMS_SPEC.md — Integrated Research Project, Publication & Grant Management System

> **This is the single master specification.** It merges the former `FRONTEND_SPEC.md` and `PROJECT_SPEC.md` into one implementation contract. Do not build two separate applications. Part A defines the UI; Part B defines the database and business logic. Both layers must use the same entities, IDs, roles, status values and business rules.

## Integration decisions (resolve conflicts before building)

1. **Application:** Flask 3 + Jinja2 server-rendered pages, vanilla JavaScript and hand-written CSS. Do **not** use Streamlit. Part A’s route table and templates are the UI source of truth.
2. **Database:** the user already has MySQL installed on a Mac. Use that local MySQL installation only (`127.0.0.1`, port `3306` by default), with credentials from `.env`. Do not use Docker, containers, or Docker Compose anywhere in setup, development, testing, or documentation.
3. **One app / one DB layer:** every Flask route calls a service; services use the shared MySQL connection pool and transaction helpers. Stored procedures listed in Part B own their transactions and must be called without an outer application transaction; direct multi-statement writes use the shared `run_transaction()` helper. Never nest transactions. SQL procedures, triggers, constraints and views remain authoritative.
4. **One integrated tree:** use the unified folder structure in Part B, with Part A’s `app/templates`, `app/static`, blueprints, CSS/JS and routes. Do not create duplicate app entry points or separate data stores.
5. **Local safety:** initialize only the two explicitly named schemas `rpgms` and `rpgms_test`. The setup script must never run `DROP DATABASE`; `--reset` drops/recreates objects only inside the one selected allowlisted schema and requires `--confirm-reset` to exactly match `--database`. Never drop or modify unrelated databases. Never commit `.env`, credentials, real personal data, or password hashes generated for a real account.
6. **Dependencies:** keep `requirements.txt` pinned and compatible with Python 3.11+. MySQL must be 8.0.16+ for enforced CHECK constraints. If the installed server is older, stop and clearly report the version instead of silently weakening integrity rules.
7. **Evidence honesty:** do not claim a test, screenshot, query, or database operation passed unless it was actually run. Record environment limitations and actual outputs in `docs/test_report.md` and `docs/decisions.md`.
8. **Build sequence:** follow Part B Section 17’s phases and gates, and include Part A’s visual QA before declaring completion. A gate cannot pass while its checks are unrun or failing.

---

# PART A — RPGMS FRONT-END DESIGN, ROUTES & INTERACTIONS

> **Part A of this integrated master specification.** Part A defines the UI; Part B defines the database, business rules, queries and tests. This file replaces the former separate specs. Build one Flask application and one MySQL database; the two former source files are no longer separate implementation documents.

---

## 0. AGENT RULES FOR THE FRONT-END

1. **Build the site to match the wireframes in Section 6.** After building each page, compare it to its wireframe (layout, regions, order, labels). Differences must be improvements, never omissions.
2. **Use the design tokens in Section 3.** No hard-coded colors, font sizes or spacings in templates — only CSS variables and the utility/component classes defined in `app.css`.
3. **One layout, many pages.** Every authenticated application page extends `base.html` (sidebar + topbar). Public login and centered error pages use the same shared design tokens/macros but render with the app shell disabled; do not force a sidebar onto login or error pages. Reusable UI pieces are Jinja macros in `templates/_components.html`.
4. **No JS framework, no CSS framework.** Hand-written CSS + small vanilla-JS modules. Only external resources allowed: Google Font *Inter* (with system-font fallback) and Chart.js (pinned, from cdnjs). The layout must remain usable if either resource fails; if Chart.js fails, show the chart's accessible data table or a clear fallback message rather than a blank chart.
5. **Every data-driven page and component must handle the states that apply to it**: loading, empty, error, and populated (Section 10). Static pages such as login and error pages implement their relevant validation/error states instead of artificial empty or populated states.
6. **Every page must be responsive** at 1440 / 1024 / 768 / 390 px (Section 11) with no horizontal page scroll.
7. **Real data only.** Pages render from the database through the service layer. No hard-coded demo numbers in templates.
8. **Accessibility is part of "done"** (Section 12): labels, focus rings, contrast, keyboard use.
9. **Take screenshots** of every page at 1440 and 390 px (use a browser tool if available, otherwise Playwright) and save to `docs/screens/`. Fix anything that looks unpolished: misalignment, overflow, cramped spacing, inconsistent buttons.

---

## 1. DESIGN INTENT

**Feel:** calm, professional, data-first — like a modern finance/ops dashboard that a university research office would trust. Plenty of white space, soft borders instead of heavy shadows, one accent color, numbers that are easy to scan.

**Principles (in plain words)**
- **Show the money and the deadlines first.** The two things a research office worries about are *"are we overspending?"* and *"what is late?"* — these get the strongest visual treatment (progress bars, red/amber/green).
- **Same thing looks the same everywhere.** A status badge, a ₹ amount or a progress bar looks identical on every page.
- **Never make the user guess.** Show remaining balance *before* they submit an expense; show unallocated budget *while* they type allocations; explain why a button is disabled.
- **Errors are friendly and specific.** "This would exceed the Equipment budget by ₹ 18,500" — not "Error 1644".

---

## 2. TECH & FILE LAYOUT (front-end part)

- **Flask 3** + **Jinja2** server-rendered pages, Post/Redirect/Get for form submits, small JSON endpoints for live widgets.
- **Chart.js 4.4.1** (pinned) for charts.
- **Fonts:** `Inter` via Google Fonts, fallback stack `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`. Monospace for codes: `ui-monospace, "JetBrains Mono", Consolas, monospace`.
- **Icons:** one inline SVG sprite (`static/img/icons.svg`), 20×20, 1.75 px stroke, rounded caps (Lucide style), referenced with `<svg class="icon"><use href="…#name"/></svg>`. Create these icons: `home, folder, users, wallet, receipt, flag, book, award, bar-chart, shield, search, bell, plus, edit, trash, check, x, alert, info, chevron-down, chevron-right, chevron-left, download, filter, calendar, clock, menu, sun, moon, logout, more, external, upload, user, building`.

```
app/
├── templates/
│   ├── base.html                # <head>, skip-link, conditional shell, sidebar/topbar, flash toasts, {% block content %}
│   ├── _components.html         # macros: kpi_card, badge, progress, avatar, empty_state, page_header,
│   │                            #   field(label,input,help,error), money, date_chip, tabs, modal, pagination, stepper
│   ├── auth/login.html
│   ├── dashboard/index.html
│   ├── projects/{list,new,detail,report_form}.html # detail tabs: _overview,_team,_grants,_milestones,_expenditure,_publications,_patents,_reports
│   ├── investigators/{list,detail,form,workload,_assign_modal}.html
│   ├── grants/{list,new,detail}.html
│   ├── milestones/{list,_form_modal}.html
│   ├── expenditure/{list,entry,statement}.html
│   ├── publications/{list,new,detail}.html
│   ├── patents/{list,new,detail}.html
│   ├── reports/{hub,report}.html                # report.html is one template driven by a report definition
│   ├── admin/{users,audit}.html
│   └── errors/{403,404,500}.html
└── static/
    ├── css/app.css              # sections in order: tokens, reset, base, layout, components, pages, utilities, responsive, print
    ├── js/
    │   ├── app.js               # sidebar collapse, theme toggle, toasts, confirm modal, dropdowns, table sorting UI
    │   ├── forms.js             # inline validation, money input formatting, live character counters
    │   ├── typeahead.js         # accessible search-as-you-type dropdown (researchers, projects)
    │   ├── charts.js            # one function per chart, reads data from <script type="application/json"> blocks
    │   └── pages/{grant_wizard,expenditure,assign_modal,publication_form}.js
    └── img/{logo.svg,favicon.svg,icons.svg,login-art.svg}
```

---

## 3. DESIGN SYSTEM

### 3.1 Color tokens (implement as CSS variables on `:root`, dark overrides on `[data-theme="dark"]`)

```css
:root {
  /* brand */
  --primary:        #2457D6;   --primary-hover: #1C46B0;   --primary-soft: #E8EEFC;
  /* neutrals */
  --bg:             #F6F7FB;   --surface:       #FFFFFF;   --surface-2: #F1F3F9;
  --border:         #E3E6EF;   --border-strong: #CBD0DF;
  --text:           #1B2133;   --text-muted:    #6B7390;   --text-faint: #626B80;
  /* semantic */
  --success:        #1E9E6A;   --success-ink: #166A49; --success-soft: #E3F6EE;
  --warning:        #C98100;   --warning-ink: #805000; --warning-soft: #FFF3D9;
  --danger:         #D64545;   --danger-ink: #A62929; --danger-soft: #FDE8E8;
  --info:           #2B8CD6;   --info-ink: #145C8A; --info-soft: #E4F2FC;
  --neutral-ink:    #4B5368;   --neutral-soft: #EDEFF5;
  /* chart series: read these via getComputedStyle; never hard-code colors in charts.js */
  --chart-primary: #2457D6; --chart-secondary: #A9BDF2; --chart-success: #1E9E6A;
  --chart-warning: #C98100; --chart-danger: #D64545; --chart-info: #2B8CD6;
  /* shape & depth */
  --radius-sm: 6px;  --radius: 10px;  --radius-lg: 14px;
  --shadow-sm: 0 1px 2px rgba(20,28,58,.06);
  --shadow:    0 4px 16px rgba(20,28,58,.08);
  --focus:     0 0 0 3px rgba(36,87,214,.35);
  /* spacing scale (4px base) */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px; --s8:64px;
  /* layout */
  --sidebar-w: 248px; --sidebar-w-collapsed: 72px; --topbar-h: 64px; --content-max: 1280px;
}
[data-theme="dark"] {
  --bg:#0F1320; --surface:#171C2E; --surface-2:#1E2438; --border:#2A3150; --border-strong:#3A4368;
  --text:#E9ECF6; --text-muted:#9BA4C4; --text-faint:#A6AFCC;
  --primary:#6C93F5; --primary-hover:#8AA8F8; --primary-soft:#1F2A4F;
  --success:#3CC48F; --success-ink:#70E0B0; --success-soft:#143328;
  --warning:#F0B13A; --warning-ink:#FFD275; --warning-soft:#3A2C0E;
  --danger:#F07272; --danger-ink:#FF9A9A; --danger-soft:#3B1C1F;
  --info:#5FB0EE; --info-ink:#83CCF6; --info-soft:#142C40; --neutral-ink:#C3CAE0; --neutral-soft:#232A42;
  --chart-primary:#8AA8F8; --chart-secondary:#526BA8; --chart-success:#3CC48F;
  --chart-warning:#F0B13A; --chart-danger:#F07272; --chart-info:#5FB0EE;
}
```
Theme toggle in the topbar; respect `prefers-color-scheme` on first visit; remember the choice in `localStorage` (try/catch around it).

### 3.2 Typography

| Token | Size / weight / line-height | Use |
|---|---|---|
| `display` | 28px / 700 / 1.2 | Login headline only |
| `h1` | 24px / 650 / 1.25 | Page title |
| `h2` | 18px / 600 / 1.3 | Card titles |
| `h3` | 15px / 600 / 1.4 | Section labels inside cards |
| `body` | 14px / 400 / 1.55 | Default |
| `small` | 12.5px / 400 / 1.4 | Help text, table meta |
| `kpi` | 28px / 700, tabular numbers | KPI values |
| `code` | 13px mono | Project codes, voucher numbers, DOIs |

Use `font-variant-numeric: tabular-nums` on all money and number columns so digits align.

### 3.3 Money, dates, numbers (Jinja filters in `utils.py`)

| Filter | Example output |
|---|---|
| `inr` | `₹ 12,34,567.00` (Indian grouping) |
| `inr_compact` | `₹ 12.3 L`, `₹ 4.82 Cr`, `₹ 85 K` (used in KPI cards and chart axes) |
| `pct` | `72.5%` |
| `date_short` | `12 Mar 2026` |
| `date_rel` | `in 12 days` / `8 days overdue` / `today` |
| `initials` | `A. Rao → AR` |

Money columns are **right-aligned**; negative or overspend values are `--danger`.

### 3.4 Status & health badges (single mapping — use everywhere)

Badge = pill, 12px font, 600 weight, 4px×10px padding, soft background + the corresponding `--*-ink` foreground token (never the brighter chart/accent color when that fails contrast), 6px dot before the text. Use the matching `--success-ink`, `--warning-ink`, `--danger-ink`, `--info-ink` or `--neutral-ink` foreground token for the semantic state, including light and dark themes. Maintain text contrast ≥ 4.5:1 in both themes; verify each foreground/background pair with an automated contrast check.

| Value | Hue |
|---|---|
| Project: Proposed / Active / On Hold / Completed / Cancelled | neutral / success / warning / info / danger |
| Grant: Sanctioned / Active / Closed / Terminated | info / success / neutral / danger |
| Milestone: Pending / In Progress / Completed / Delayed | neutral / info / success / danger |
| Report: Draft / Submitted / Accepted / Returned | neutral / info / success / warning |
| Patent: Filed / Published / Granted / Rejected / Lapsed | info / info / success / danger / neutral |
| Budget health: Under 50% / On Track / Near Limit / Exhausted | info / success / warning / danger |
| RAG: Green / Amber / Red | success / warning / danger |
| Role: ADMIN / RESEARCH_OFFICER / PI / VIEWER | primary / info / success / neutral |

### 3.5 Components (class names are mandatory so CSS and templates stay consistent)

| Component | Spec |
|---|---|
| **Card** `.card` | surface bg, 1px `--border`, radius 14px, padding 20px, optional header row (`h2` left, actions right) separated by a hairline |
| **Button** `.btn` | height 38px, radius 10px, padding 0 16px, 600 weight. Variants: `.btn-primary` (solid blue), `.btn-secondary` (surface + border), `.btn-ghost` (text only), `.btn-danger`. Sizes: `.btn-sm` (32px). Icon-only buttons are 38×38 with `aria-label`. Disabled = 50% opacity + `not-allowed` + a `title` explaining why |
| **Input / Select / Textarea** `.input` | height 40px (textarea min 96px), 1px `--border-strong`, radius 8px, focus ring `--focus`; error state red border + message below with an alert icon; label above (13px/600), help text below (12.5px muted) |
| **Money input** | `₹` prefix inside the field, right-aligned digits, formats with Indian grouping on blur, submits a plain decimal |
| **Date input** | native `<input type="date">` with `min`/`max` attributes set from business rules (e.g., milestone date limited to project dates) |
| **Segmented control** | for roles (PI / Co-PI / Researcher / Scholar) and view toggles (Table / Timeline) |
| **Table** `.table` | header row 40px, `--surface-2` bg, 12px uppercase muted labels; rows 52px, hairline separators, hover `--surface-2`; sortable headers show ▲▼; sticky header inside scroll containers; first column bold; numeric columns right-aligned; row actions in a "more" (⋯) menu |
| **KPI card** `.kpi` | label (small, muted), value (kpi style), delta/sub-line (small), optional 24px icon chip in the corner with `--primary-soft` bg |
| **Progress bar** `.progress` | 8px high, radius 999px, track `--neutral-soft`; budget-bar fill follows health thresholds: <50% primary, 50–89% success, 90–99% warning, 100% danger/exhausted; milestone/time bars fill with primary. The accessible text label always names the percentage and health state. Label (value %) sits right of the bar |
| **Avatar** | 32px circle, initials, background from a fixed palette of 8 soft colors chosen by hashing the name |
| **Tabs** `.tabs` | underline style, active tab 2px primary underline, counts as small pills (`Milestones 7`) |
| **Modal** | centered, 520px (wide: 720px), radius 14px, backdrop `rgba(15,19,32,.55)`, traps focus, closes on Esc, primary action bottom-right |
| **Drawer** | right-side panel 420px for researcher/publication quick-view |
| **Toast** | top-right stack, auto-dismiss 5 s, colored left border by type, icon, close button; created from Flask `flash()` messages |
| **Empty state** | centered icon in a 56px soft circle, title, one-line help, primary action button |
| **Stepper** | numbered circles connected by a line; done = filled check, current = primary ring, upcoming = grey |
| **Typeahead** | input + dropdown list (max 8, keyboard ↑↓ Enter Esc), highlights matched text, shows secondary line (e.g., department) |
| **Page header** | `h1` + muted subtitle left; action buttons right; breadcrumb above in small muted text |
| **Pagination** | "Showing 1–10 of 48", page-size select (10/25/50), prev/next + numbered buttons |
| **Filter bar** | one row: search input (with icon), select filters, status chips, "Clear filters" ghost button; chips show active state |

---

## 4. APP SHELL (appears on every page after login)

```
+----------------------------------------------------------------------------------------------+
| [logo] RPGMS        | Projects  >  RP-2024-003          [ Search projects, people...  / ]     |
| Research Office     |                                    (sun)  (bell 3)  (AR) Dr. A. Rao    v     |  TOPBAR 64px
+---------------------+------------------------------------------------------------------------+
| MAIN                |  Page title                                          [Secondary][Primary]|
|  > Dashboard        |  One-line subtitle in muted text                                          |
|    Projects         |  --------------------------------------------------------------------   |
|    Investigators    |                                                                           |
| FINANCE             |   CONTENT AREA  (max 1280px, centered, 24px gutters, background --bg)   |
|    Grants & Budget  |                                                                           |
|    Expenditure      |                                                                           |
| OUTPUT              |                                                                           |
|    Milestones       |                                                                           |
|    Publications     |                                                                           |
|    Patents          |                                                                           |
| INSIGHTS            |                                                                           |
|    Reports          |                                                                           |
| ADMIN (admins only) |                                                                           |
|    Users & Audit    |                                                                           |
|---------------------|                                                                           |
| [<<] Collapse       |                                                                           |
+---------------------+------------------------------------------------------------------------+
 SIDEBAR 248px (72px when collapsed: icons only, labels as tooltips)
```

- **Sidebar:** surface bg, right hairline border. Group labels are 11px uppercase muted. Active item: `--primary-soft` bg, primary text, 3px primary bar on the left edge. Hover: `--surface-2`. Collapse state remembered in `localStorage`.
- **Topbar:** sticky. Left: breadcrumb. Center/right: global search (press `/` to focus) for ADMIN, RESEARCH_OFFICER and PI accounts, across projects, investigators, grants, publications, patents and milestones — results grouped by entity type in a keyboard-accessible dropdown. A PI sees only own-project records and linked records needed for those projects. VIEWER has no global record search; use the report hub and its filters. Right: theme toggle, bell (shows count of overdue milestones; click → Milestones filtered to overdue when that route is available to the role), user menu (name, role badge, a "My workload" link to `/my-workload` for PI, Logout). Search results must be scoped to the logged-in user’s permissions.
- **Under 1024 px** the sidebar becomes an off-canvas drawer opened with a menu button; under 768 px the global search collapses to an icon.
- **Skip link** "Skip to main content" is the first focusable element.

### 4.1 Navigation visibility by role

| Item | ADMIN | RESEARCH_OFFICER | PI | VIEWER |
|---|---|---|---|---|
| Dashboard | ✔ all-project aggregates and records | ✔ all-project aggregates and records | ✔ own-project data only | ✔ aggregate dashboard only; no record-level project lists |
| Projects | ✔ | ✔ | ✔ own projects only | — |
| Investigators | ✔ | ✔ | ✔ read-only details for investigators linked to own projects only | — |
| Grants & Budget | ✔ | ✔ | ✔ read-only, own projects only | — |
| Expenditure | ✔ | ✔ | ✔ read-only, own projects only | — |
| Milestones | ✔ | ✔ | ✔ edit milestones on own projects | — |
| Publications / Patents | ✔ | ✔ | ✔ may search existing records and link them only to own projects | — |
| Reports | ✔ all | ✔ all | ✔ data and filters scoped to own projects | ✔ read-only, all-project reports |
| Users & Audit | ✔ | — | — | — |

The `VIEWER` role is limited to aggregate Dashboard data and sanitized analytical Reports. It has no record-level operational routes and no global record search. Each report must provide a Viewer-safe aggregate version that omits individual project/grant identifiers, personal names, publication titles/DOIs, voucher numbers and other record-level details; the UI, JSON, charts and CSV must all use the same redacted service result. PIs may see only projects they lead; investigator details shown to a PI must be limited to members associated with those projects. Buttons and sidebar links the user may not use are **hidden** (not just disabled). Direct URL access to a forbidden page returns the 403 page.

### 4.2 Navigation and interaction rules (mandatory)

- **Current location:** mark the current sidebar link with `aria-current="page"`; when on a nested route, keep its parent navigation group expanded and active. On project detail pages, highlight Projects and show the project code in the breadcrumb.
- **Breadcrumbs:** every nested page shows a clickable path, for example `Projects > RP-2024-003 > Grants`. All crumbs except the current page are links. Do not use breadcrumbs as a replacement for a page title.
- **Return to results:** detail pages and edit/entry flows show a quiet `← Back to ...` link. Preserve the user's list filters, sort order and page using an internal `return_to` URL when practical. Validate that return targets are local application paths; reject external URLs and fall back to the appropriate list page.
- **After saving:** use Post/Redirect/Get. Successful creation redirects to the new record's detail page (or the parent project tab when there is no detail page), shows a success toast, and avoids duplicate submissions on refresh. On validation failure, preserve safe user-entered values and focus the first invalid field.
- **Contextual actions:** show actions beside the related record, not only in the global sidebar. Examples: Add grant from a project’s Grants tab, Add milestone from the project’s Milestones tab, and Record expense from a grant detail page. Preselect the known project or grant where possible.
- **Permission-aware actions:** render a primary action only when the logged-in role can use it. For example, `+ New project`, `+ New grant`, and `+ Record expense` are visible only to ADMIN/RESEARCH_OFFICER; PI milestone/publication actions appear only for the PI’s own projects. The server must still enforce every permission.
- **No dead ends:** list pages provide a clear empty state, a route back to the parent, and a relevant next action where permission allows it. Detail pages link to related records by their human-readable code/title.
- **Global search:** for ADMIN, RESEARCH_OFFICER and PI only, search Projects (code/title), Investigators (name/email/ORCID), Grants (grant number/agency/project code), Publications (title/DOI), Patents (title/application number), and Milestones (title/project code). Show grouped results, a useful “No results” state, keyboard navigation (Up/Down/Enter/Esc), and a “View all matching results” route or filtered list link. PI results must respect own-project scope. VIEWER does not receive this record-level search UI or endpoint.
- **Search and list state:** filters, sorting and pagination are encoded in GET parameters so views are bookmarkable. Provide a visible `Clear filters` action whenever any filter is active.
- **Confirmation:** ask for confirmation before destructive or high-impact actions (removing an investigator, disabling a user, or changing/closing a project). The dialog states what will happen and offers Cancel as the safe default. Do not use confirmation dialogs for ordinary navigation.
- **Session expiry:** if a session expires during navigation or form submission, redirect to login with a short notice. After login, return only to a validated internal destination; never expose protected data in the redirect URL.

### 4.3 Main user journeys

Use these journeys to check whether the navigation feels natural. Every step must be reachable through visible links/actions; users should not need to type URLs manually.

| Journey | Navigation path and expected result |
|---|---|
| Register a project | Projects → `+ New project` → complete form → Register → newly created project detail page with success toast |
| Assign a team member | Project detail → Team tab → `+ Assign investigator` → select researcher/role/effort → Assign → return to Team tab with updated workload |
| Add a grant and budget | Project detail → Grants tab → `+ Add grant` → 3-step wizard → review totals → save → grant card appears on project and grant detail is reachable |
| Track a milestone | Project detail → Milestones tab or global Milestones → add/update milestone if permitted → updated status and due-date display |
| Record expenditure | Project detail → Expenditure tab or Grants → grant detail → `+ Record expense` → live balance check → save or show a readable budget-rule error without losing form values |
| Link research output | Project detail → Publications/Patents tab → link existing record or create one → record appears on the project and relevant list |
| Produce an analytical report | Reports → choose R1–R10 → apply filters → review chart and table → export the same filtered result to CSV or print |
| Submit a project report | Project detail → Reports tab → `+ New report` → enter type, period and summary → save as draft or submit → report appears with correct status |
| Administer access | Admin → Users & Audit → create/disable a user or inspect an audit entry; this group is visible to ADMIN only |

### 4.4 Mobile navigation wireframe (390 px target)

On phone, the desktop sidebar is replaced by a menu button that opens a full-height off-canvas drawer. The current page remains visible behind a dim overlay; tapping a destination closes the drawer. Escape closes it, focus stays inside while open and returns to the menu button on close.

```text
+--------------------------------------+
| [☰] RPGMS       [Search] [Bell] [VK]  |  56px topbar
+--------------------------------------+
| Projects > RP-2024-003                |
| Soil Moisture Sensing                 |
| {Active}                              |
| [ + Add milestone ]                   |  only if permitted
+--------------------------------------+
| [Overview] [Team] [Grants] [More v]   |  horizontally scrollable tabs
+--------------------------------------+
| Total grant                           |
| ₹ 38,00,000                           |
|--------------------------------------|
| Spent                                 |
| ₹ 27,40,000  ·  72%                   |
|--------------------------------------|
| Next milestone                        |
| Soil sensor validation                |
| Due 24 Oct 2026                       |
| [View milestone]                      |
+--------------------------------------+
|                                      |
| [  Primary contextual action bar  ]   |  fixed above safe area on forms only
+--------------------------------------+

Menu open:
+----------------------+~~~~~~~~~~~~~~~+
| RPGMS                | dimmed page   |
| Research Office      |               |
|----------------------|               |
| Dashboard            |               |
| Projects             |               |
| Investigators        |               |
| Grants & Budget      |               |
| Expenditure          |               |
| Milestones           |               |
| Publications         |               |
| Patents              |               |
| Reports              |               |
| Users & Audit*       |               |
|----------------------|               |
| Theme: Light / Dark  |               |
| Logout               |               |
+----------------------+~~~~~~~~~~~~~~~+
*ADMIN only
```

On mobile, show the Search icon only to ADMIN/RESEARCH_OFFICER/PI and hide it for VIEWER; the bell count may appear for VIEWER but must not link to a restricted page. Keep the page title and primary action visible near the top. Use the `More` tab for secondary project tabs when they do not fit. The fixed form action bar must not cover validation messages, fields, or the on-screen keyboard; add bottom safe-area padding. Do not add a second bottom navigation bar that duplicates the sidebar destinations.

---

## 5. PAGE ANATOMY (applies to every page)

```
 breadcrumb (small, muted)
 [ H1 title + subtitle ]                                  [ secondary action ] [ PRIMARY ACTION ]
 [ filter bar / tabs ]                                    (optional)
 [ summary tiles ]                                        (optional, 3–5 KPI cards in a row)
 [ main content: cards / table / form ]
 [ pagination ]                                           (lists only)
```
Vertical rhythm: 24px between blocks, 20px inside cards.

---

## 6. WIREFRAMES (build each page to match)

Legend: `[ Button ]`  `( Select v )`  `[x] checkbox`  `{ Badge }`  `====` progress bar  `~~~~` chart area  `(AV)` avatar. Any names, dates, IDs and numbers shown in these wireframes are illustrative examples only; templates must render actual authorized database values.

### 6.1 Login (`/login`) — no shell, split screen

```
+-------------------------------------------+-------------------------------------------+
|  BRAND PANEL (linear gradient using --primary and --primary-hover) |                                           |
|                                           |            +-----------------------+      |
|  [logo] RPGMS                             |            |  Welcome back         |      |
|                                           |            |  Sign in to continue  |      |
|  Every project, grant and publication     |            |                       |      |
|  in one place.                            |            |  Username             |      |
|                                           |            |  [___________________]|      |
|  (  Track budgets  ) (  Watch deadlines ) |            |  Password             |      |
|  (  Measure output )                      |            |  [___________] (eye)  |      |
|                                           |            |  [   Sign in        ] |      |
|     ~~ abstract bars/line illustration ~~ |            |                       |      |
|                                           |            |  Demo accounts  v     |      |
|  (c) University Research Office           |            +-----------------------+      |
+-------------------------------------------+-------------------------------------------+
```
- Brand panel hidden under 900 px. "Demo accounts" is a collapsible box listing all 6 seeded demo logins (1 ADMIN, 1 RESEARCH_OFFICER, 3 PI and 1 VIEWER; shown only when `APP_ENV=demo`). Keep demo mode local-only and never enable it on a publicly reachable deployment. Wrong credentials → inline alert above the form: "Incorrect username or password." (never say which). Button shows a spinner while submitting.

### 6.2 Dashboard (`/dashboard`)

```
 Dashboard                                                         Updated just now  [ Refresh ]
 Overview of projects, funding and deadlines

 +-------------+ +-------------+ +-------------+ +-------------+ +-------------+
 | Active      | | Sanctioned  | | Spent       | | Overdue     | | Publications|
 | projects    | | funding     | | to date     | | milestones  | | this year   |
 |  9          | |  ₹ 4.82 Cr  | |  ₹ 2.91 Cr  | |  4  (red)   | |  11         |
 | 15 total    | | 6 agencies  | | 60% of fund | | in 3 proj.  | | 30 all-time |
 +-------------+ +-------------+ +-------------+ +-------------+ +-------------+

 +--------------------------------------------------+ +-----------------------------------+
 | Funding vs spending by agency                    | | Budget health                     |
 | ~~~~ grouped horizontal bars:                    | | ~~~ donut: Under 50 / On Track /  |
 | ~~~~ sanctioned (primary) vs spent (soft)        | | ~~~ Near Limit / Exhausted        |
 | ~~~~ one row per agency, ₹ compact axis          | | legend with counts                |
 +--------------------------------------------------+ +-----------------------------------+

 +--------------------------------------------------+ +-----------------------------------+
 | Overdue milestones                  [View all >] | | Grants near limit                 |
 | Milestone | Project | Due | Days late | {status} | | RP-2023-004  SERB   ============ 96%|
 | ...5 rows, days-late in red                      | | RP-2024-001  DBT    ==========   92%|
 |                                                  | | (top 5 by utilization, bars warn/ |
 |                                                  | |  danger colored)                  |
 +--------------------------------------------------+ +-----------------------------------+

 +--------------------------------------------------+ +-----------------------------------+
 | Recent activity (from audit_log, last 8)         | | Publications per year             |
 | (AV) Expenditure #88 added  ₹ 42,000  2h ago     | | ~~~ column chart by year, stacked |
 | ...                                              | | ~~~ by type                       |
 +--------------------------------------------------+ +-----------------------------------+
```
- Grid: 12 columns; KPI row = 5 equal cards (wraps to 2-up on tablet, 1-up on phone); chart rows are 8/4 and 7/5 splits.
- PI users see the same layout scoped to their projects. The full audit-log activity widget is ADMIN-only; for other roles, omit it or show only a separately derived activity feed limited to records they are allowed to access. Never expose raw audit-log rows to RESEARCH_OFFICER, PI or VIEWER unless the role policy is explicitly changed.

### 6.3 Projects list (`/projects`)

```
 Projects                                                              [ Export CSV ] [ + New project ]
 All research projects across departments

 [ Search title, code, keyword...  ] ( Department v ) ( Year v )   {All}{Active}{Proposed}{On Hold}{Completed}{Cancelled}   Clear

 +------------------------------------------------------------------------------------------------------+
 | CODE        TITLE & DEPT              PI              STATUS    PERIOD            FUNDING  SPENT  MILESTONES |
 |------------------------------------------------------------------------------------------------------|
 | RP-2024-003 Soil Moisture Sensing     (AV) A. Rao     {Active}  Jan 24 - Dec 26   ₹ 38 L   ====72%   5 / 8   (...) |
 |             Civil Engineering                                    ====== time bar                      |
 | RP-2023-011 ...                                                                                       |
 +------------------------------------------------------------------------------------------------------+
 Showing 1-10 of 15                                         Rows ( 10 v )        [<] 1 2 [>]
```
- Row click opens the project detail. The ⋯ menu contains View, Change status (opens a confirmation modal), Add grant, and Add milestone only when the current role can perform that action. No dead Edit button: project editing is not part of this assignment’s required workflow.
- "Period" cell shows two lines: the dates, and a thin 4px time-elapsed bar. "Spent" cell shows % and a bar colored by budget thresholds. Overdue milestone count appears as a small red pill next to the milestone ratio.
- Sorting on Code, Title, Status, Period, Funding, Spent. Filters are GET parameters so URLs are shareable.

### 6.4 Register project (`/projects/new`)

```
 Projects > New project
 Register a project                                                         [ Cancel ] [ Register ]

 +------------------------------------------------------------+ +--------------------------------+
 | 1  Basic information                                       | |  Summary (sticky)              |
 |   Project code *   [ RP-2026-___ ]  help: format RP-YYYY-NNN| |  Code      RP-2026-016         |
 |   Title *          [______________________________________]| |  Duration  2 yrs 3 mths        |
 |   Department *     ( Select department              v )    | |  PI        Dr. A. Rao          |
 |   Abstract         [                                      ]| |  Status    {Proposed}          |
 |                    [                              0/2000  ]| |                                |
 +------------------------------------------------------------+ |  Rules checked                 |
 | 2  Schedule                                                | |  (ok) End date after start     |
 |   Start date *  [ 2026-11-01 ]   End date * [ 2029-02-01 ] | |  (ok) Code is unique           |
 |   (live duration chip: "2 yrs 3 mths")                     | |  ( ) PI is active              |
 +------------------------------------------------------------+ +--------------------------------+
 | 3  Principal investigator                                  |
 |   PI *  [ search researcher by name...  ]  (typeahead)     |
 |   Effort on this project (%)  [ 20 ]  slider 1-100         |
 |   (live warning: "Dr. A. Rao is at 85% effort; adding 20% exceeds 100%")  <- BR-11                  |
 +------------------------------------------------------------+
```
- The summary panel updates live. The "Rules checked" list ticks off client-side where possible (dates, code format) and the unique-code check calls `/api/projects/code-exists`. Submitting calls `sp_register_project`; on success, redirect to the new project's detail page with a success toast.

### 6.5 Project detail (`/projects/<id>`)

```
 Projects > RP-2024-003
 [RP-2024-003]  Soil Moisture Sensing for Precision Irrigation    {Active}     [ Change status ]
 Civil Engineering  .  PI: (AV) Dr. A. Rao  .  Jan 2024 - Dec 2026

 +---------------+ +---------------+ +----------------+ +-----------------+
 | Total grant   | | Spent         | | Milestones     | | Time elapsed    |
 | ₹ 38.0 L      | | ₹ 27.4 L 72%  | | 5 of 8  (1 late)| | 78% (14 mo left)|
 |               | | ======== bar  | | ======== bar   | | ======== bar    |
 +---------------+ +---------------+ +----------------+ +-----------------+

 Overview | Team 4 | Grants 2 | Milestones 8 | Expenditure 21 | Publications 3 | Patents 1 | Reports 4
 ------------------------------------------------------------------------------------------------
 (tab content)
```
- Header actions are role-aware: `Change status` is shown only to ADMIN/RESEARCH_OFFICER. Do not render an `Edit` action because project editing is not a required route in this specification.

**Tab contents**

- **Overview:** left card — abstract text, key dates list (start, end, next milestone due); right card — "Health" with RAG badge (rule from R1), plus 3 plain-language sentences generated from data ("Spending is ahead of progress by 14 points.").
- **Team:** table of members (avatar, name, role badge, designation, effort %) + `[ + Assign investigator ]` (opens assign modal, Section 6.7) only for ADMIN/RESEARCH_OFFICER; remove button with confirmation has the same roles. PI sees read-only team details on their own project. ADMIN/RESEARCH_OFFICER also get `[ Change PI ]`, which uses the atomic PI-transfer route. The current PI cannot be removed or demoted through the generic remove/assign actions.
- **Grants:** one card per grant: grant number, agency, amount, period, status badge; underneath a per-budget-head list — head name, allocated, spent, remaining, progress bar (colored by threshold). `[ + Add grant ]` is visible only to ADMIN/RESEARCH_OFFICER and opens the wizard with this project preselected.
- **Milestones:** vertical timeline — dot colored by status, title, due date, status badge, "Mark complete" action. Overdue items get a red date and "8 days overdue".
- **Expenditure:** compact table (date, voucher, head, description, amount) with a small monthly spend sparkline above it; `[ + Record expense ]` is shown only to ADMIN/RESEARCH_OFFICER. PI sees the read-only own-project table and no entry action.
- **Publications / Patents:** list items with title, venue/year/DOI chip (publication) or application number + status stepper (patent), authors/inventors as avatar stack. `[ Link existing ]` is available to ADMIN/RESEARCH_OFFICER/PI within the project’s permitted scope; `[ + Add new ]` is visible only to ADMIN/RESEARCH_OFFICER. VIEWER never sees these operational lists.
- **Reports:** table of project report records (type, period, submitted on, status) plus links to R1–R10 generated reports with the project filter preselected. `[ + New report ]` opens a modal with report type, period start/end and summary. Offer `Save draft` and `Submit report`; a submitted report sets `submitted_on` to today and `submitted_by` from the authenticated session. Drafts and Returned reports can be edited and resubmitted; only ADMIN/RESEARCH_OFFICER can accept or return a Submitted report. Validate `period_end >= period_start`, preserve inputs on errors, and return to this tab after saving. This records project reporting status; it is separate from the R1–R10 analytical report pages.

### 6.6 Investigators (`/investigators`)

```
 Investigators                                                             [ + Add researcher ]
 Researchers, scholars and their workload

 [ Search name, email, ORCID... ] ( Department v ) ( Designation v ) [x] Active only

 +-----------------------------------------------------------+ +-----------------------------------+
 | RESEARCHER            DEPT   DESIGNATION   PROJ  WORKLOAD | | (drawer opens on row click)       |
 | (AV) Dr. A. Rao       CIVIL  Professor     3     ===== 85%| |  (AV) Dr. A. Rao   {Active}       |
 | (AV) S. Menon         CSE    Asst. Prof    1     ==    30%| |  a.rao@univ.edu . ORCID 0000-...  |
 | ...                                                       | |  Workload 85%  ========          |
 +-----------------------------------------------------------+ |  Projects (3): code, role, effort |
                                                               |  Output: 7 pubs . 2 patents       |
                                                               |  [ Assign to project ] [ Edit ]   |
                                                               +-----------------------------------+
```
- Workload bar colors: <70 primary, 70–99 warning, 100 danger. Inactive researchers are greyed with an "Inactive" badge and cannot be assigned. `[ Assign to project ]` and `[ Edit ]` are shown only for ADMIN/RESEARCH_OFFICER; other roles get read-only details.

### 6.7 Assign investigator (modal, used from Team tab and Investigators drawer)

```
 +--------------------------------------------------+
 | Assign investigator                           [x]|
 |--------------------------------------------------|
 | Project *     [ search project...   ] (typeahead)|
 | Researcher *  [ search researcher... ] (typeahead)|
 | Role *        [ Co-PI | Researcher | Research Scholar ] <- segmented
 | Effort (%) *  [ 25 ]  ----o----------   1..100   |
 |                                                  |
 | Workload impact:   60%  ====>  85%   (ok)        |
 |   or  (!) 105% exceeds 100% — reduce effort (BR-11)|
 | (!) This project already has a PI (BR-10)        |
 |--------------------------------------------------|
 |                           [ Cancel ] [ Assign ]  |
 +--------------------------------------------------+
```
- The workload line calls `/api/researchers/<id>/workload`; "Assign" is disabled while a rule is violated, with a tooltip explaining why. On an existing project, this modal offers only Co-PI, Researcher or Research Scholar. Changing the project's PI is a separate, admin/research-officer-only action so an existing PI cannot accidentally be removed.

### 6.8 Grants & Budget — list (`/grants`) and wizard (`/grants/new`)

**List**
```
 Grants & Budget                                                              [ + New grant ]
 [ Search grant no., project... ] ( Agency v ) ( Status v ) ( Health v )

 +---------------------------------------------------------------------------------------------+
 | GRANT NO.      PROJECT           AGENCY  AMOUNT     SPENT      BALANCE    USED          HEALTH |
 | SERB/2023/118  RP-2023-004       SERB    ₹ 45.0 L   ₹ 43.2 L   ₹ 1.8 L    =========96%  {Near Limit} |
 +---------------------------------------------------------------------------------------------+
```
Row click → `/grants/<id>`: grant header, KPI row (amount, spent, balance, % used), "Budget by head" table + stacked bar chart and expenditure table. `[ + Record expense ]` is shown only to ADMIN/RESEARCH_OFFICER. PI sees a read-only detail view only for own projects. VIEWER cannot open grant details; grant/budget aggregates appear only in Viewer-safe dashboard/report summaries.

**New grant — 3-step wizard**
```
 (1) Grant details  ------  (2) Budget allocation  ------  (3) Review & confirm        <- stepper

 STEP 1                                           STEP 2
 Project *  [ search project... ]                 Grant amount ₹ 45,00,000.00
 Agency *   ( Select agency  v )                  +-------------------------------------------+
 Grant no. * [____________]                       | Head           Allocate (₹)      Share    |
 Amount *    [₹ ____________]                     | Equipment      [ 20,00,000 ]     44%      |
 Sanction date * [ ... ]                          | Consumables    [  8,00,000 ]     18%      |
 Start *  [ ... ]   End * [ ... ]                 | Travel         [  3,00,000 ]      7%      |
 (dates limited to the project's period,          | Manpower       [ 10,00,000 ]     22%      |
  shown as help text; BR-03)                      | Contingency    [  2,00,000 ]      4%      |
                                                  | Overheads      [  2,00,000 ]      4%      |
                                                  +-------------------------------------------+
                                                  Allocated ₹ 45,00,000 / ₹ 45,00,000
                                                  Unallocated ₹ 0   =========================  100%
                                                  [ Distribute evenly ]  [ Clear ]
                                                  (bar turns red + "Over by ₹ X" when > amount; BR-09)

 STEP 3 (review): read-only summary of step 1 and the allocation table with totals.
                   [ Back ]   [ Confirm & save grant ]   -> calls sp_add_grant_with_budget
```
- Heads with ₹0 are omitted from the saved allocations. "Next" is disabled until step validations pass; the unallocated counter updates on every keystroke.

### 6.9 Milestones (`/milestones`)

```
 Milestones                                                          [ Table | Timeline ]  [ + New milestone ]
 [ Search... ] ( Project v ) ( Department v ) {All}{Pending}{In Progress}{Completed}{Delayed}  [x] Overdue only

 TABLE VIEW
 +--------------------------------------------------------------------------------------------+
 | MILESTONE            PROJECT       DUE          STATUS         DAYS LATE        ACTIONS      |
 | Prototype field test RP-2024-003   12 Aug 2026  {Delayed}      60 days (red)    [Mark done]  |
 +--------------------------------------------------------------------------------------------+
 (rows of overdue items have a faint danger-soft background)

 TIMELINE VIEW  (Gantt-lite, one row per project, months across the top)
 RP-2024-003  |--------[====o=====o=====o===x====]------------|     o done  x overdue  | today line
 RP-2023-011  |   [==o====o=====]                              |
```
- "Mark done" opens a small popover with a date input (default today, limited to project dates) → `sp_complete_milestone`.
- New-milestone modal: project, title, description, due date (min/max are populated from the selected project's current start/end dates; help text displays those actual dates, never a hard-coded example), status.

### 6.10 Expenditure list, entry and statement

**Recent expenditure list (`/expenditure`)**
```text
 Expenditure                                             [ + Record expense ]
 [ Search voucher/description ]  [ Grant v ] [ Date range ] [ Budget head v ]

 | DATE       VOUCHER       PROJECT       GRANT         HEAD          AMOUNT |
 | 12 Oct 26  V-2026-0417   RP-2024-003   SERB/2023…   Equipment     ₹ 1,25,000 |
 | ...                                                                      |
 Showing 1–20 of 86                                       [ < 1 2 3 > ]
```
ADMIN/RESEARCH_OFFICER may open the entry form and statement for any grant. PI sees a read-only list/statement scoped to own projects; the Record Expense action and any cross-project filter are hidden. VIEWER has no `/expenditure` route. Use server-side pagination and perform permission scoping before counts, filters and pagination so a PI cannot infer other projects from totals or empty-page behaviour.

**Record expense (`/expenditure/new`) — the most important form**

```
 Expenditure > Record expense
 Record an expense                                                           

 +----------------------------------------------+ +-------------------------------------------+
 | Expense details                              | | Budget position (live)                    |
 | Grant *  [ search grant / project...   ]     | |  SERB/2023/118 . RP-2023-004              |
 | Budget head *  ( Equipment          v )      | |  Grant total   ₹ 45,00,000                |
 | Date *    [ 2026-10-10 ]  (within grant dates)| |  Spent so far  ₹ 43,20,000   ========96% |
 | Amount *  [₹ 1,25,000.00 ]                   | |  --------------------------------------   |
 | Voucher no. * [ V-2026-0417 ]                | |  Equipment                                 |
 | Description * [____________________________]| |   Allocated ₹ 20,00,000                    |
 |                                              | |   Spent     ₹ 19,10,000                    |
 | [ Cancel ]  [ Record expense ]  (disabled if | |   Remaining ₹    90,000                    |
 |   amount > head remaining; tooltip explains) | |   After this entry:  -₹ 35,000  (red)      |
 +----------------------------------------------+ |   (!) Exceeds Equipment budget by ₹ 35,000 |
                                                  +-------------------------------------------+
 Recent expenses for this grant  (table, last 5)            [ View full statement > ]
```
- Selecting a grant loads head balances from `/api/grants/<id>/heads`. Choosing a head highlights its block in the right card. Typing an amount updates "After this entry" instantly (green if ok, red if over). The database procedure and constraints remain the final authority: if the server returns a `BR-06/07/17` message, show it in a danger alert on top of the form and keep the user's input.
- **Statement page** (`/expenditure/statement/<grant_id>`): date-range filter, table with a **Running balance** column, totals footer, `[ Export CSV ] [ Print ]`.

### 6.11 Publications (`/publications`, `/publications/new`)

```
 Publications                                                            [ + Add publication ]
 [ Search title, DOI... ] ( Year v ) ( Type v ) ( Indexing v ) ( Department v )

 +-------------------------------------------------------------------------------------------+
 | TITLE                                    TYPE     VENUE            YEAR  INDEXING  AUTHORS     PROJECTS |
 | Low-cost soil moisture sensor networks   Journal  IEEE Sensors J.  2025  {SCIE}    (AV)(AV)+2  RP-2024-003 |
 |   doi 10.1109/xxxxx  (mono, copy icon)                                                          |
 +-------------------------------------------------------------------------------------------+
```
**Add publication**
```
 +-----------------------------------------------------+ +-----------------------------------+
 | Publication details                                 | | Linked projects                   |
 | Title *   [______________________________________] | |  [ search project... ] (typeahead)|
 | Type *    ( Journal v )   Indexing ( SCIE v )       | |  chips: [RP-2024-003 x] [RP-.. x] |
 | Venue *   [__________________]  ISSN/ISBN [______]  | |  (!) Publication date is before   |
 | DOI       [ 10.1109/... ]  (live format check;      | |      project start (BR-16)        |
 |            "DOI already exists" shown inline, BR-08)| +-----------------------------------+
 | Publication date * [ ... ]                          |
 +-----------------------------------------------------+
 | Authors  (order matters)                            |
 |  1 [= handle] [ search researcher ]  [x] Corresponding  [up][down][remove]|
 |  2 [= handle] [ search researcher ]  [ ] Corresponding  [up][down][remove]|
 |  [ + Add author ]                                   |
 +-----------------------------------------------------+
                                       [ Cancel ] [ Save publication ]
```
- The `+ Add publication` button and create form are visible only to ADMIN/RESEARCH_OFFICER. PI users can search existing records and use `[ Link existing ]` from an own-project tab; they cannot create or edit global publication records. Author order is the row order (renumbered automatically). The same researcher cannot be added twice (inline message, BR-18). Saving a new publication, its authors and chosen project links occurs in one transaction.

### 6.12 Patents (`/patents`, `/patents/new`)

```
 Patents                                                                      [ + Add patent ]
 [ Search... ] ( Status v ) ( Jurisdiction v )

 cards in a 2-column grid, each card:
 +----------------------------------------------------+
 | {Granted}                        IN 2024-123456    |
 | Title of the patent                                 |
 | Stepper:  Filed o----o Published o----o Granted (*) |
 | Inventors: (AV)(AV)(AV)   Projects: [RP-2024-003]   |
 | Filed 14 Mar 2023 . Granted 02 Feb 2026             |
 +----------------------------------------------------+
```
- The `+ Add patent` button and create/status-edit actions are visible only to ADMIN/RESEARCH_OFFICER. PI users can search existing records and use `[ Link existing ]` from an own-project tab but cannot create or globally change patent records. The form switches required fields by status (Granted reveals *Patent number* and *Grant date* as required; BR-14). Layout otherwise mirrors the publication form: details card, inventors repeater, linked projects chips.

### 6.13 Reports hub (`/reports`) and report page (`/reports/<code>`)

```
 Reports
 Ready-made reports with filters, charts and CSV export

 +-----------------+ +-----------------+ +-----------------+ +-----------------+
 | (icon)          | | (icon)          | | (icon)          | | (icon)          |
 | R1 Project      | | R2 Budget       | | R3 Milestone    | | R4 Researcher   |
 | Progress        | | Utilization     | | Tracker         | | Output          |
 | Status & RAG... | | Spend vs grant..| | Deadlines...    | | Papers/patents..|
 | [ Open > ]      | | [ Open > ]      | | [ Open > ]      | | [ Open > ]      |
 +-----------------+ +-----------------+ +-----------------+ +-----------------+
 (R5 .. R10 continue in a 4-column grid; 2 columns on tablet, 1 on phone)
```
**Report page template (one template drives all 10)**
```
 Reports > R2 Budget Utilization                                   [ Print ] [ Export CSV ]
 [ filters specific to this report ... ]                             [ Apply ]

 +-----------+ +-----------+ +-----------+ +-----------+     <- 3-4 summary tiles (report-specific)
 |           | |           | |           | |           |
 +-----------+ +-----------+ +-----------+ +-----------+

 +--------------------------------------------------------------+
 | ~~~~ chart (type per report, see Section 9) ~~~~              |
 +--------------------------------------------------------------+

 +--------------------------------------------------------------+
 | data table (sortable, sticky header, totals footer row)       |
 +--------------------------------------------------------------+
```
- Reports are defined in one Python dict (`REPORTS = {"R1": {title, description, sql, filters, columns, chart, tiles}}`) so the hub and the report page are generated from the same source. Filters are GET params; the CSV export honours the current filters and uses the same query.

### 6.14 Admin (`/admin/users`, `/admin/audit`)

```
 Users & Audit            [ Users | Audit log ]                               [ + New user ]

 USERS
 | USERNAME   LINKED RESEARCHER   ROLE badge   ACTIVE   CREATED     ACTIONS (change role / disable) |

 AUDIT LOG
 ( Table v ) ( Action v ) [ From date ] [ To date ] [ Search record id ]
 | WHEN             TABLE        RECORD  ACTION   BY        CHANGES                     |
 | 10 Oct 14:02     expenditure  88      INSERT   officer1  [ View ]                    |
 -> "View" opens a drawer showing a two-column diff: field | old | new, changed fields highlighted. The audit actor is the logged-in application username, not merely the shared MySQL connection account.
```
- New-user modal: username, role (segmented), linked researcher (required and enforced when role = PI, BR from the CHECK), and a temporary password with a strength meter. Never display password hashes. A temporary password is shown only during creation and is not recoverable from the stored hash.

### 6.15 Error pages
Centered illustration-free layout: big muted code (`403` / `404` / `500`), one-sentence explanation in plain words, `[ Back to dashboard ]`. 500 shows a short reference id, never a stack trace.

---

## 7. ROUTES (implement exactly; one Flask blueprint per group)

| URL | Method | Roles allowed | Template / result |
|---|---|---|---|
| `/` | GET | any logged-in | redirect → `/dashboard` |
| `/login` | GET, POST | public | `auth/login.html` |
| `/logout` | POST | any | CSRF-protected logout; redirect → `/login` |
| `/dashboard` | GET | ADMIN, RESEARCH_OFFICER, PI, VIEWER | `dashboard/index.html`; Viewer receives aggregate KPIs/charts only; PI data is scoped to own projects |
| `/projects` | GET | ADMIN, RESEARCH_OFFICER, PI (own projects only) | filtered list; `?format=csv` exports the same validated filters and permission scope |
| `/projects/new` | GET, POST | ADMIN, RESEARCH_OFFICER | form → `sp_register_project` |
| `/projects/<id>` | GET | ADMIN, RESEARCH_OFFICER, PI (only when they are that project's PI) | detail; `?tab=` selects the tab |
| `/projects/<id>/status` | POST | ADMIN, RESEARCH_OFFICER | `sp_update_project_status` for Proposed/Active/On Hold; `sp_close_project` for Completed/Cancelled |
| `/projects/<id>/investigators` | POST | ADMIN, RESEARCH_OFFICER | assign non-PI member; DB enforces active status/workload |
| `/projects/<id>/investigators/<rid>/remove` | POST | ADMIN, RESEARCH_OFFICER | remove non-PI assignment; refuse removal of current PI |
| `/projects/<id>/pi` | POST | ADMIN, RESEARCH_OFFICER | atomically change PI through `sp_change_project_pi`; never expose the current PI as removable via generic actions |
| `/projects/<id>/publications` | POST | ADMIN, RESEARCH_OFFICER, PI (own project) | link an existing publication to the project |
| `/projects/<id>/patents` | POST | ADMIN, RESEARCH_OFFICER, PI (own project) | link an existing patent to the project |
| `/projects/<id>/reports/new` | GET, POST | ADMIN, RESEARCH_OFFICER, PI (own project) | GET renders the report form; POST creates a Draft with both submission fields NULL or a submitted record with `submitted_on` and `submitted_by` populated from the authenticated session, then redirects to `/projects/<id>?tab=reports` |
| `/projects/<id>/reports/<int:report_id>` | GET, POST | ADMIN, RESEARCH_OFFICER, PI (own project) | Edit only Draft or Returned reports; may save Draft or resubmit as Submitted, setting `submitted_on` to today and `submitted_by` to the current user; Accepted reports are read-only |
| `/projects/<id>/reports/<int:report_id>/review` | POST | ADMIN, RESEARCH_OFFICER | Accept or return only a Submitted report; transition to `Accepted` or `Returned`; preserve submission metadata; validate that the report belongs to the URL project; audit the state change |
| `/investigators` | GET | ADMIN, RESEARCH_OFFICER, PI (only investigators linked to own projects) | list; row drawer links to detail; PIs receive no global workload totals |
| `/investigators/<id>` | GET | ADMIN, RESEARCH_OFFICER, PI (only if associated with an own project) | `investigators/detail.html`, scoped as allowed |
| `/my-workload` | GET | PI | `investigators/workload.html`; workload and assignments for projects where the logged-in PI is the PI; no organization-wide totals |
| `/investigators/new` | GET, POST | ADMIN, RESEARCH_OFFICER | `investigators/form.html` |
| `/investigators/<id>/edit` | GET, POST | ADMIN, RESEARCH_OFFICER | same shared `investigators/form.html` |
| `/grants` | GET | ADMIN, RESEARCH_OFFICER, PI (own projects only) | scoped list |
| `/grants/<id>` | GET | ADMIN, RESEARCH_OFFICER, PI (own project only) | detail |
| `/grants/new` | GET, POST | ADMIN, RESEARCH_OFFICER | wizard → `sp_add_grant_with_budget` |
| `/milestones` | GET | ADMIN, RESEARCH_OFFICER, PI (own projects only) | table / timeline (`?view=`); filters preserve role scope |
| `/milestones/new` | POST | ADMIN, RESEARCH_OFFICER, PI (own project) | create from modal; min/max dates use the selected project's actual date range |
| `/milestones/<id>/status` | POST | ADMIN, RESEARCH_OFFICER, PI (own project) | calls `sp_update_milestone_status` for Pending / In Progress / Delayed; Completed must use `sp_complete_milestone` |
| `/milestones/<id>/complete` | POST | ADMIN, RESEARCH_OFFICER, PI (own project) | `sp_complete_milestone` |
| `/expenditure` | GET | ADMIN, RESEARCH_OFFICER, PI (own projects only) | Recent expenditure list with search/date/grant filters; PI only sees expenses for own projects; Viewer has no direct route |
| `/expenditure/new` | GET, POST | ADMIN, RESEARCH_OFFICER | `sp_record_expenditure`; GET may accept a validated `grant_id` for preselection |
| `/expenditure/statement/<grant_id>` | GET | ADMIN, RESEARCH_OFFICER, PI (own project only) | statement; `?format=csv` exports |
| `/publications` | GET | ADMIN, RESEARCH_OFFICER, PI | publication catalogue for search/link workflows; PI views expose publication metadata but redact unrelated project affiliations; PIs cannot edit global publication records |
| `/publications/<id>` | GET | ADMIN, RESEARCH_OFFICER, PI | detail; PI view exposes only publication metadata and project links in their own scope |
| `/publications/new` | GET, POST | ADMIN, RESEARCH_OFFICER | create publication, authors and project links in one service transaction; optional validated project preselection |
| `/patents` | GET | ADMIN, RESEARCH_OFFICER, PI | patent catalogue for search/link workflows; PI views redact unrelated project affiliations and unrelated project-derived data; PIs cannot create or change global patent records |
| `/patents/new` | GET, POST | ADMIN, RESEARCH_OFFICER | create patent, inventors and project links in one service transaction |
| `/patents/<id>` | GET | ADMIN, RESEARCH_OFFICER, PI | detail; PI view exposes only patent metadata and project links in their own scope |
| `/patents/<id>/status` | POST | ADMIN, RESEARCH_OFFICER | status update, validating grant number/date when Granted; a PI may link patents to their own project but cannot change a patent record's global status |
| `/reports` | GET | all | hub |
| `/reports/<code>` | GET | ADMIN, RESEARCH_OFFICER, PI (own-project results), VIEWER | report page; `?format=csv` exports the same authorised filtered result |
| `/admin/users` | GET, POST | ADMIN | list and create user |
| `/admin/users/<id>/disable` | POST | ADMIN | disable account (do not physically delete it); reject disabling the last active ADMIN account |
| `/admin/users/<id>/role` | POST | ADMIN | update role with PI-link validation; reject demoting the last active ADMIN account |
| `/admin/audit` | GET | ADMIN | audit log |

**Authorization invariants (apply to HTML, JSON, charts, totals and CSV alike):**
- ADMIN and RESEARCH_OFFICER may see organization-wide operational data, subject to the ADMIN-only user/audit rules. PI data access is always limited to projects where that user is the PI. VIEWER may access only the aggregate Dashboard and R1–R10 analytical Reports. Viewer-specific report queries must aggregate or redact individual records before producing results; do not send restricted rows to the browser and then hide them with CSS or JavaScript.
- For a PI, dashboard counts, milestones, grant sums, publication counts and all report outputs must be computed **after** filtering to their own projects—not computed globally and filtered only in the template. In R4, count publication/patent output only when linked to an own project; in R5, include only grants/agencies funding own projects; in R6, include publications linked to own projects; in R7, show only own-project-derived department figures and never reveal a department-wide total that includes other projects; in R8, permit only grants on own projects; in R9, include only patents linked to own projects; in R10, include only own completed projects. R1–R3 follow the same scope. CSV must use the same scoped service/query as the visible page.
- When a publication or patent is linked to multiple projects, a PI's page/report/CSV must disclose only project links the PI is allowed to see. Link-existing catalog pickers return only the item metadata needed to choose a record and whether it is already linked to the selected own project; they never return the list of other project IDs/titles. Avoid joining unrelated projects into aggregates or authoring a filtered display over globally computed totals.
- VIEWER's Dashboard is limited to aggregate KPIs/charts; hide named overdue milestone lists, individual record links, global search, and the overdue bell link to an operational page. ADMIN/RESEARCH_OFFICER see all permitted dashboard detail; PI receives own-project detail only. Apply the same redaction to HTML, JSON, chart data, tooltips and CSV.

Every POST route validates CSRF and input server-side and ends with Post/Redirect/Get plus a flash message. For an atomic stored-procedure call, call the procedure without wrapping it in `run_transaction()` because that procedure owns its transaction. For multi-statement writes performed directly by the service layer, use `run_transaction()`. Never nest transactions. Keep user input in parameterized statements.

**List-page rules:** server-side pagination (`?page=&size=`), sorting via `?sort=&dir=` using a **whitelist dict** mapping allowed sort keys to real column names (never interpolate request text into SQL), all filters via GET.

---

## 8. LIVE INTERACTIONS (small JSON endpoints, `blueprints/api.py`, login required, read-only except where noted)

| Endpoint | Returns | Used by |
|---|---|---|
| `GET /api/search?q=` | ADMIN, RESEARCH_OFFICER, PI only; `{projects:[…], researchers:[…], grants:[…], publications:[…], patents:[…], milestones:[…]}` (max 5 per group) | global search; PI is scoped to own projects and permitted linked records |
| `GET /api/researchers/search?q=&active=1` | `[{id,name,dept,designation}]` | typeaheads |
| `GET /api/projects/search?q=` | `[{id,code,title,start,end,status}]` | typeaheads, date limits |
| `GET /api/projects/code-exists?code=` | `{exists:bool}` | register form |
| `GET /api/researchers/<id>/workload` | `{current_percent, projects:[…]}` | assign modal, register form |
| `GET /api/grants/search?q=` | `[{id,grant_number,project_code,agency}]` | expenditure form |
| `GET /api/grants/<id>/heads` | `[{head_id,name,allocated,spent,remaining}]` + grant totals + grant dates | expenditure form |
| `GET /api/doi-exists?doi=` | `{exists:bool}` | publication form, ADMIN/RESEARCH_OFFICER only |
| `GET /api/publications/search?q=&project_id=` | minimal publication catalogue fields plus `already_linked_to_target:bool`; no project-link list | Link-existing publication picker; ADMIN/RESEARCH_OFFICER, or PI only when `project_id` is their own project |
| `GET /api/patents/search?q=&project_id=` | minimal patent catalogue fields plus `already_linked_to_target:bool`; no project-link list | Link-existing patent picker; ADMIN/RESEARCH_OFFICER, or PI only when `project_id` is their own project |
| `GET /api/notifications/count` | `{overdue:int}` | bell badge |

All endpoints are parameterized queries, debounced client-side (250 ms), cancel in-flight requests when a newer one starts, and fail quietly (the form still works; server/database checks remain authoritative). `/api/search` is available only to ADMIN, RESEARCH_OFFICER and PI. `/api/researchers/search`, `/api/researchers/<id>/workload`, `/api/projects/code-exists`, `/api/grants/search`, `/api/grants/<id>/heads`, and `/api/doi-exists` are ADMIN/RESEARCH_OFFICER only. The two catalog search endpoints may be called by a PI only with a validated project id that belongs to that PI, and they return no unrelated project affiliations. `/api/projects/search` returns all permitted projects for ADMIN/RESEARCH_OFFICER and only PI-owned projects for PI. VIEWER does not receive record-level search. `/api/notifications/count` returns only a permitted aggregate count; for VIEWER it must not provide an operational link to a forbidden route.

**Client-side behaviour list (`forms.js`):** validate on blur then on input; show the first error inline under the field and focus the first invalid field on submit; disable submit while a request is in flight and show a spinner in the button; format money on blur; character counters for textareas; warn on leaving a dirty form (`beforeunload`).

---

## 9. CHARTS (Chart.js, config lives in `charts.js`; data comes from JSON script blocks rendered by Jinja)

Global: font Inter 12px, grid lines `--border`, no chart borders, rounded bars (radius 6), tooltips with ₹ formatting, legend at the bottom, series colors from the `--chart-*` CSS variables, read using `getComputedStyle` so charts adapt to dark mode; do not hard-code chart colors in JavaScript. Each chart has a visible title (not a canvas title) and an `aria-label` plus a hidden data table for screen readers. Render chart data with Jinja’s `tojson` filter inside JSON script blocks; never concatenate user-controlled text into executable JavaScript.

| Where | Type | Detail |
|---|---|---|
| Dashboard — funding vs spend by agency | horizontal grouped bar | sanctioned (primary) vs spent (soft) |
| Dashboard — budget health | doughnut | 4 health classes, center text = total grants |
| Dashboard — publications per year | stacked column | stack by type |
| R1 Project Progress | horizontal bar | % milestones complete per project with a marker for time elapsed |
| R2 Budget Utilization | stacked horizontal bar | spent vs remaining per grant; second chart per-head when a grant is picked |
| R3 Milestone Tracker | column | counts by status per month of due date |
| R4 Researcher Output | grouped column | publications vs patents per researcher (top 10) |
| R5 Agency Portfolio | doughnut | share of total sanctioned funding |
| R6 Publications | grouped column | by year, grouped by indexing |
| R7 Department Summary | radar or grouped bar | projects, funding, publications (normalised) |
| R8 Expenditure Statement | line | running balance over time |
| R9 Patent Status | doughnut | by status |
| R10 Closing Summary | stacked bar | spent vs unspent per completed project |

---

## 10. STATES & MICROCOPY

| State | Treatment |
|---|---|
| **Loading** | Table/cards show quiet skeleton placeholders; a subtle 1.2 s loading pulse is allowed, but all hover/focus transitions are ≤150 ms and other decorative animations are ≤250 ms. Buttons show an inline spinner and a "Saving…" label. |
| **Empty** | Use the empty-state component with specific copy (below). |
| **Error** | Inline danger alert at the top of the content area: icon + plain sentence + (if useful) "Try again". Field errors under fields. |
| **Success** | Toast, e.g., "Expense of ₹ 1,25,000 recorded." |

**Empty-state copy**
- Projects: "No projects match your filters." → `[ Clear filters ]`; none at all: "No projects yet. Register your first project to start tracking." → `[ + New project ]`
- Milestones: "No milestones due. You're all caught up."
- Expenditure: "No expenses recorded for this grant yet."
- Publications: "No publications linked to this project yet." → `[ Link existing ]` `[ + Add new ]`
- Reports: "No data for these filters. Try widening the date range."

**Friendly messages for database rules (`errors.py` map; the user never sees the raw `BR-xx` text but the code is kept in a small muted "(rule BR-06)" suffix)**

| Code | Message |
|---|---|
| BR-01 | "End date must be after the start date." |
| BR-02 | "Grant dates are invalid. The end date must be after the start date, and the grant cannot start before its sanction date." |
| BR-03 | "The grant period must fall inside the project's dates ({project_start}–{project_end})." |
| BR-04 | "The milestone due/completion date must fall inside the project's dates ({project_start}–{project_end})." |
| BR-05 | "Grant, allocation and expenditure amounts must be greater than zero." |
| BR-06 | "This would exceed the available budget. Remaining for this head: ₹ {remaining}." |
| BR-07 | "The expense date must be within the grant period ({start}–{end})." |
| BR-08 | "A publication with this DOI already exists, or the DOI format is invalid." |
| BR-09 | "Budget allocations cannot exceed the grant amount, and the amount cannot be reduced below existing allocations or spending." |
| BR-10 | "This project must have exactly one Principal Investigator. Use Change PI to transfer responsibility." |
| BR-11 | "This would take {name} above 100% effort across Proposed/Active projects." |
| BR-12 | "{name} is inactive and cannot be assigned." |
| BR-13 | "A completed milestone needs a completion date; other statuses must not have one." |
| BR-14 | "A granted patent needs a patent number and grant date on or after its filing date." |
| BR-15 | "Select a budget head that is allocated to this grant." |
| BR-16 | "The publication date cannot be earlier than the start date of a linked project." |
| BR-17 | "This project is closed, so new expenses or milestones can't be added." |
| BR-18 | "Each author must appear once per publication and author order must be unique." |
| duplicate key | "That {field} is already in use." |
| FK / unknown | "Something went wrong saving this. Nothing was changed." (log details server-side) |

---

## 11. RESPONSIVE BEHAVIOUR

| Breakpoint | Behaviour |
|---|---|
| ≥ 1280 | Full layout as in wireframes |
| 1024–1279 | Sidebar auto-collapses to icons; 12-col grids keep structure; drawers overlay |
| 768–1023 | Sidebar becomes off-canvas drawer; KPI row 2-up; two-column forms stack into one; summary side panels move below the form |
| < 768 (target 390) | One column everywhere; tables become **card lists** (each row = a card with label/value pairs) for Projects, Milestones, Grants; wide report tables scroll horizontally inside their own container; modals become full-screen sheets; tabs scroll horizontally; primary action becomes a floating bottom bar on forms |

The page body must never scroll horizontally at any width. Touch targets ≥ 44 px on phone.

---

## 12. ACCESSIBILITY & POLISH CHECKLIST

- Color contrast ≥ 4.5:1 for text in both themes (verify badges).
- Every input has a `<label for>`; errors use `aria-describedby` and `role="alert"`.
- Visible focus ring (`--focus`) on all interactive elements; logical tab order; modals trap focus and return it on close; Esc closes.
- Icon-only buttons have `aria-label`; charts have text alternatives.
- Status is never conveyed by color alone (badges have text; overdue has "days overdue" text).
- Respect `prefers-reduced-motion` (disable shimmer/transitions).
- Consistent 150 ms ease transitions for hover/focus; no decorative animation longer than 250 ms. The loading indicator is the only exception and must stop/turn static under `prefers-reduced-motion`.
- Page `<title>` pattern: `Page name · RPGMS`. Favicon + logo as SVG.

### 13. Print stylesheet
`@media print`: hide sidebar, topbar, buttons and filter bars; white background; table borders visible; charts keep size; page header shows the report title, filters used and the date generated; avoid page breaks inside table rows.

---

## 14. FRONT-END BUILD ORDER & VISUAL QA (Phase 6 of this master specification's Section 17)

1. **Foundation:** `app.css` tokens + base + components, `base.html` shell, `_components.html` macros, icon sprite, theme toggle, sidebar, toasts. Create a temporary `/styleguide` page (ADMIN-only, dev mode) showing every component in every state — use it to polish before building pages.
2. **Auth & errors:** login, logout, 403/404/500, role decorators, CSRF.
3. **Read-only pages:** Dashboard, Projects list/detail, Investigators, Grants, Milestones, Publications, Patents, Reports hub + report page (all 10 reports).
4. **Forms:** register project, assign investigator, grant wizard, milestone modal, expenditure entry (with live balance), publication & patent forms, admin.
5. **Live widgets:** typeaheads, global search, workload preview, DOI check, code-exists check.
6. **Responsive + dark mode + print pass.**
7. **Visual QA:** for each of the 20+ pages, capture screenshots at 1440 and 390 px (and dark mode for Dashboard and Project detail) into `docs/screens/`. Also capture the mobile navigation drawer both closed and open, the active breadcrumb/sidebar state, and the project Reports-tab new-report modal. Create `docs/wireframes.md` that places each wireframe next to the screenshot filename and lists any intentional differences.

**Visual QA checks (fix before moving on):**
- Alignment: card edges, table columns and buttons line up on the 4px grid; headers and numbers align.
- No text truncation without a tooltip; no overlapping elements; no horizontal page scroll at 390 px.
- All buttons in a row have equal height; primary action is the only solid-blue button in a region.
- Empty, loading and error states each captured at least once.
- Money columns right-aligned with Indian grouping; dates use `12 Mar 2026` format everywhere.

---

## 15. FRONT-END ACCEPTANCE CHECKLIST (agent must tick with evidence)

- [ ] Design tokens and components implemented in one `app.css`; `/styleguide` shows them all
- [ ] App shell (sidebar, topbar, breadcrumb, global search, theme toggle, notifications) works on every page
- [ ] Breadcrumbs, active navigation, return-to-results links and contextual actions work without dead ends
- [ ] Global search covers projects, investigators, grants, publications, patents and milestones; results respect role/project scope
- [ ] Mobile off-canvas navigation is keyboard accessible; its focus returns to the menu button when closed
- [ ] Main user journeys in Section 4.3 pass for every role that is permitted to perform them
- [ ] Project report draft/submit/edit/resubmit/review flow works and returns to the project Reports tab
- [ ] Every visible action has a real route/handler and is hidden for roles that cannot use it
- [ ] All 6.1–6.15 wireframe sections are implemented; modal/partial wireframes are implemented as components, not mistaken for standalone pages
- [ ] Role-based menu visibility and 403 handling verified for all four roles
- [ ] Grant wizard shows live unallocated amount and blocks over-allocation
- [ ] Expenditure form shows live remaining balance and blocks overspend; server message shown if the DB rejects
- [ ] Assign modal shows live workload impact and blocks > 100% effort and a second PI
- [ ] Publication form: DOI uniqueness check, author ordering, project linking in one transaction; PI link pickers search the catalogue without revealing unrelated project affiliations
- [ ] Role-specific buttons are hidden where unauthorized; `/expenditure` and `/my-workload` links resolve to their documented routes
- [ ] All 10 reports render table + chart + CSV export + print view
- [ ] Loading / empty / error / success states present on every list and form
- [ ] Responsive at 1440 / 1024 / 768 / 390 with no horizontal page scroll; tables become cards on phone
- [ ] Dark mode works and charts follow the theme
- [ ] Keyboard-only walkthrough of login → register project → record expense succeeds
- [ ] Screenshots saved in `docs/screens/` and `docs/wireframes.md` written


---

# PART B — RPGMS DATABASE, BUSINESS LOGIC, TESTING & DELIVERY

> **How to use this file (for the human):** Put this integrated master spec in the root of the project folder, open it in Antigravity, and tell the agent:
> *"Read FINAL_RPGMS_SPEC.md completely. Build the integrated Flask + MySQL project phase by phase exactly as specified. Stop at the end of each phase, run the Gate checks, show me the results, then continue."*

---

## 0. INSTRUCTIONS TO THE AI AGENT (READ FIRST)

You are building a **complete, runnable, submission-ready DBMS course project**. Follow this spec literally. Where the spec is silent, choose the simplest option that keeps the database correct, and write the decision into `docs/decisions.md`.

**Environment-specific rule:** The user has MySQL installed on macOS. Use only that local MySQL instance (typically `127.0.0.1:3306`). Docker, containers, and Docker Compose are prohibited and must not appear as setup dependencies or fallback options. Create/use only the `rpgms` and `rpgms_test` schemas. Ask for no passwords in source files; use `.env` and `.env.example` placeholders. Initialize those two schemas once with the installed MySQL administrator, then run `python db/setup_db.py --database rpgms --reset --seed --confirm-reset rpgms` or `python db/setup_db.py --database rpgms_test --reset --seed --confirm-reset rpgms_test`. The script must refuse missing or unexpected database names and must never issue `DROP DATABASE`; reset only objects inside the selected allowlisted schema. Resetting requires `--confirm-reset` to match the selected database exactly (for example, `--confirm-reset rpgms`). Automated test resets must target only `rpgms_test` and pass `--confirm-reset rpgms_test`; reject a mismatched confirmation value. Drop views and routines before dependent objects; clear table triggers as their tables are dropped; use foreign-key checks only within a guarded `try/finally` reset block and always restore them before returning the connection. If MySQL is not running, provide macOS-native instructions appropriate to the user’s MySQL installation.

**Non-negotiable rules**

1. **Work in phases (Section 17).** After each phase, run its Gate checks. Do not start the next phase until the gate passes. If something fails, fix it, re-run, and only then continue.
2. **Actually run everything.** Do not just write SQL — execute it against a real MySQL instance, load the seed data, run every query, run the tests, launch the app. Paste real outputs into the docs.
3. **No unfinished placeholders.** Final code and documentation must not contain TODOs, unimplemented stubs or "add more rows here" instructions. Ellipses are allowed only in illustrative wireframes where they clearly mean that repeated rows are omitted. Every deliverable must be complete.
4. **Database enforces integrity, not just the app.** Every rule in Section 5 must be enforced by an appropriate database constraint, trigger or transaction-owning stored procedure, with direct runtime writes restricted by least-privilege grants. The app adds friendly validation/messages but is not the final authority.
5. **Parameterized queries only.** Never build SQL with string formatting using user input.
6. **macOS-first, portable tooling.** The user’s target environment is macOS. Use Python scripts (not shell-only scripts) for setup/reset tasks and `pathlib` for paths.
7. **Explain in plain language.** Every doc should explain *why* in simple words, with real-world analogies where helpful (e.g., "a foreign key is like a library card number — it must belong to a real member"). Use Mermaid diagrams wherever a diagram helps.
8. **Don't invent features beyond this spec**, but do not skip any listed feature.

---

## 1. PROJECT SUMMARY

Research offices keep project, investigator, grant, milestone, expenditure, publication and patent records in separate spreadsheets, so tracking output and fund utilisation is hard. Build an **integrated relational database** plus a **small front-end** that lets a research office:

- register projects and assign investigators,
- enter grants and budget allocations,
- track milestones,
- record expenditure (with the DB blocking overspending),
- link publications and patents to projects,
- generate meaningful reports (progress, budget utilisation, researcher output, funding-agency portfolio, etc.).

The work must demonstrate: **ER modelling → relational schema → normalisation to 3NF → data integrity → transaction awareness → indexing → input validation → systematic testing.** These are acceptance goals, not claims that the implementation has already passed; only actual command output can mark a gate complete. Keep the setup/schema-owner account, test-only account and runtime account separate, and use the least-privileged account appropriate to each test.

---

## 2. TECH STACK (DECIDED — do not change)

| Layer | Choice | Why |
|---|---|---|
| Database | **MySQL 8.0.16+** (InnoDB, utf8mb4) | CHECK constraints are enforced from 8.0.16; window functions and CTEs available |
| Front-end | **Python 3.11+ with Flask 3 + Jinja2** | Fastest way to a clean multi-page CRUD + reporting UI |
| DB driver | `mysql-connector-python` | Official, supports transactions and parameterized queries |
| Other libraries | `bcrypt`, `python-dotenv`, `Flask-WTF`, `pytest` | Password hashing, environment config, CSRF protection, tests |
| Browser chart library | Chart.js 4.4.1 (pinned static/CDN asset as specified in Part A) | All dashboard/report charts; do not also introduce Plotly |
| DB setup | **Existing local MySQL on the user’s Mac only** | Use the installed MySQL service and existing local credentials; no containers or Docker dependencies |

Create `requirements.txt` with pinned, installable versions.

**Config and least privilege:** `.env` (git-ignored) + `.env.example` with `DB_HOST=127.0.0.1`, `DB_PORT=3306`, `DB_USER`, `DB_PASSWORD`, `DB_NAME=rpgms`, `TEST_DB_NAME=rpgms_test`, `DB_SETUP_USER`, `DB_SETUP_PASSWORD`, `DB_TEST_USER`, `DB_TEST_PASSWORD`, and `SECRET_KEY`. The Flask runtime user is not MySQL root and has no global privileges. Use a separate setup/schema-owner account only for local database initialization and schema-object creation; never use it in Flask. Create the two schemas once using the installed MySQL administrator account, with `utf8mb4` (for example: `CREATE DATABASE IF NOT EXISTS rpgms CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;` and the equivalent statement for `rpgms_test`), then grant setup/schema-owner privileges only on those two schemas. Grant `DB_TEST_USER` broad test-only privileges on `rpgms_test` for direct CHECK/UNIQUE/FK testing, and no privileges on `rpgms`; route/integration tests must also exercise the app using the restricted `DB_USER` against the test schema. `setup_db.py` must accept an explicit `--database` from the allowlist (`rpgms`, `rpgms_test`), refuse any other target, require the selected schema to exist, and never issue `DROP DATABASE`; `--reset` drops/recreates tables, views, triggers and routines only inside the selected schema and requires `--confirm-reset` to equal the selected schema name. Use a delimiter-aware SQL-file executor. MySQL client `DELIMITER` commands must be interpreted by the runner and must never be sent to the server; do not naïvely split trigger/procedure files on every semicolon.

---

## 3. UNIFIED FOLDER STRUCTURE (create this integrated layout)

The browser UI uses Flask/Jinja2 from Part A. Database and business logic use the MySQL schema, procedures, triggers, services and tests from Part B. Do not create a separate application or a second database layer.

```text
rpgms/
├── README.md
├── FINAL_RPGMS_SPEC.md
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py                             # Flask development entry point
├── app/
│   ├── __init__.py                    # create_app(), register blueprints, filters, error handlers
│   ├── config.py
│   ├── db.py                          # MySQL connection pool, parameterized queries, transactions
│   ├── auth.py                        # bcrypt login, session and role checks
│   ├── validators.py
│   ├── utils.py                         # Jinja filters, date/currency formatting, safe URL helpers
│   ├── errors.py                      # BR-xx database errors → friendly messages
│   ├── services/                      # projects, investigators, grants, milestones, expenditures,
│   │                                  # publications, patents, reports, dashboard, admin
│   ├── blueprints/                    # auth, dashboard, projects, investigators, grants,
│   │                                  # milestones, expenditure, publications, patents, reports,
│   │                                  # admin, api
│   ├── templates/                     # all templates and macros specified in Part A
│   └── static/                        # CSS, JS and SVG assets specified in Part A
├── db/
│   ├── 01_schema.sql
│   ├── 02_triggers.sql
│   ├── 03_procedures.sql
│   ├── 04_views.sql
│   ├── 05_indexes.sql
│   ├── 06_seed.sql
│   ├── 07_queries.sql
│   ├── 08_reports.sql
│   ├── 09_transaction_demo.sql
│   └── setup_db.py                    # allowlisted DB target; reset confirmation required; delimiter-aware SQL runner
├── tests/
│   ├── conftest.py
│   ├── test_schema_constraints.py
│   ├── test_business_rules.py
│   ├── test_queries_views.py
│   ├── test_transactions.py
│   ├── test_validators.py
│   ├── test_auth_roles.py
│   └── test_routes.py
└── docs/
    ├── requirements_analysis.md
    ├── er_model.md
    ├── relational_schema.md
    ├── normalization.md
    ├── business_rules.md
    ├── indexing.md
    ├── transactions.md
    ├── test_report.md
    ├── user_guide.md
    ├── decisions.md
    ├── viva_prep.md
    ├── wireframes.md
    └── screens/
```

**Single-source integration rules:** routes call services; services use `app/db.py`; direct writes use parameterized SQL and transaction helpers; stored-procedure calls use transaction-owning procedures without an outer transaction helper; MySQL procedures/triggers remain the final authority for business rules; API widgets read the same database through the same services; never put demo numbers into templates. The route table, UI page requirements and design tokens in Part A apply to this folder structure.

---

## 4. DATABASE DESIGN

### 4.1 Entities and relationships (conceptual)

| # | Entity | Meaning |
|---|---|---|
| 1 | DEPARTMENT | Academic department hosting researchers/projects |
| 2 | RESEARCHER | Faculty, scholar or fellow (a person who does research) |
| 3 | USER_ACCOUNT | Login for the application, linked to a role (and optionally a researcher) |
| 4 | FUNDING_AGENCY | Body that provides money (DST, SERB, DBT, ICMR, CSIR, ISRO, industry…) |
| 5 | PROJECT | A research project |
| 6 | PROJECT_INVESTIGATOR | Who works on which project, in what role (associative) |
| 7 | GRANT_AWARD | A sanctioned grant from one agency to one project (named `grant_award` because `GRANT` is a reserved word) |
| 8 | BUDGET_HEAD | Expense category (Equipment, Consumables, Travel, Manpower, Contingency, Overheads) |
| 9 | GRANT_BUDGET_ALLOCATION | How much of a grant is allocated to each budget head (associative) |
| 10 | EXPENDITURE | Money actually spent against a grant + head |
| 11 | MILESTONE | Planned deliverable of a project with due/completion date |
| 12 | PUBLICATION | Journal/conference paper, book chapter etc. |
| 13 | PUBLICATION_AUTHOR | Which researchers authored which publication, in what order (associative) |
| 14 | PROJECT_PUBLICATION | Links publications to the projects that produced them (associative) |
| 15 | PATENT | Patent application/grant |
| 16 | PATENT_INVENTOR | Researchers who invented a patent (associative) |
| 17 | PROJECT_PATENT | Links patents to projects (associative) |
| 18 | REPORT | Progress / financial / utilisation / final report submitted for a project |
| 19 | AUDIT_LOG | Who changed what, when (filled by triggers) |

**Relationships (cardinality):**

| Relationship | Cardinality |
|---|---|
| DEPARTMENT employs RESEARCHER | 1 : N |
| DEPARTMENT hosts PROJECT | 1 : N |
| PROJECT ↔ RESEARCHER via PROJECT_INVESTIGATOR | M : N (role attribute: PI / Co-PI / Researcher / Research Scholar; exactly one PI per project) |
| FUNDING_AGENCY sanctions GRANT_AWARD | 1 : N |
| PROJECT receives GRANT_AWARD | 1 : N |
| GRANT_AWARD ↔ BUDGET_HEAD via GRANT_BUDGET_ALLOCATION | M : N (allocated_amount) |
| GRANT_BUDGET_ALLOCATION incurs EXPENDITURE | 1 : N (composite FK `(grant_id, head_id)`) |
| PROJECT has MILESTONE | 1 : N |
| PROJECT has REPORT | 1 : N |
| PUBLICATION ↔ RESEARCHER via PUBLICATION_AUTHOR | M : N (author_order, is_corresponding) |
| PUBLICATION ↔ PROJECT via PROJECT_PUBLICATION | M : N |
| PATENT ↔ RESEARCHER via PATENT_INVENTOR | M : N |
| PATENT ↔ PROJECT via PROJECT_PATENT | M : N |
| USER_ACCOUNT ↔ RESEARCHER | 0..1 : 0..1 |
| USER_ACCOUNT submits REPORT | 1 : N; a Draft report has no submitter until submission |

### 4.2 User roles

| Role | Can do |
|---|---|
| `ADMIN` | Everything, including user management and audit log |
| `RESEARCH_OFFICER` | Register projects, grants, budget, expenditure, milestones, publications, patents, reports. No user management |
| `PI` | Sees only projects where they are the PI; can manage milestones, link existing publications/patents, and submit project reports on those projects. Can view (not edit) grants/expenditure on own projects and view only the investigator details needed for own project teams. |
| `VIEWER` | Read-only aggregate Dashboard and R1–R10 analytical Reports only; no record-level operational pages or global record search |

### 4.3 Relational schema (DDL — implement in `db/01_schema.sql`)

Use `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4` on every table. Money is always `DECIMAL(14,2)` (never FLOAT). Use `ON DELETE RESTRICT` for financial/historical records and project/team records; use `ON DELETE CASCADE` only where a pure junction row can safely disappear with its parent. A researcher linked to a login, project assignment, authored publication, or patent must be deactivated rather than deleted. Projects and their milestone/report history are not physically deleted through the app.

```sql
-- IMPORTANT: This file contains table DDL only. It must not DROP, CREATE or USE a database.
-- db/setup_db.py selects the explicitly allowlisted target (`rpgms` or `rpgms_test`),
-- optionally resets only that target, and executes this file inside the selected schema.
CREATE TABLE department (
  dept_id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  dept_code      VARCHAR(10)  NOT NULL UNIQUE,
  dept_name      VARCHAR(100) NOT NULL UNIQUE,
  building       VARCHAR(60),
  contact_email  VARCHAR(120),
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_dept_email CHECK (contact_email IS NULL OR contact_email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE researcher (
  researcher_id  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  employee_code  VARCHAR(20) NOT NULL UNIQUE,
  first_name     VARCHAR(50) NOT NULL,
  last_name      VARCHAR(50) NOT NULL,
  email          VARCHAR(120) NOT NULL UNIQUE,
  phone          VARCHAR(15),
  designation    ENUM('Professor','Associate Professor','Assistant Professor',
                      'Research Scholar','Postdoctoral Fellow','Research Associate') NOT NULL,
  dept_id        INT UNSIGNED NOT NULL,
  orcid_id       CHAR(19) UNIQUE,
  joined_date    DATE NOT NULL,
  is_active      BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT fk_res_dept  FOREIGN KEY (dept_id) REFERENCES department(dept_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_res_email CHECK (email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}$'),
  CONSTRAINT chk_res_phone CHECK (phone IS NULL OR phone REGEXP '^[0-9+() -]{7,15}$'),
  CONSTRAINT chk_res_orcid CHECK (orcid_id IS NULL OR
                                  orcid_id REGEXP '^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user_account (
  user_id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  username       VARCHAR(40)  NOT NULL UNIQUE,
  password_hash  VARCHAR(100) NOT NULL,                 -- bcrypt hash, never plain text
  role           ENUM('ADMIN','RESEARCH_OFFICER','PI','VIEWER') NOT NULL DEFAULT 'VIEWER',
  researcher_id  INT UNSIGNED UNIQUE,                   -- required when role = 'PI'
  is_active      BOOLEAN NOT NULL DEFAULT TRUE,
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_user_res FOREIGN KEY (researcher_id) REFERENCES researcher(researcher_id)
                         ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_user_pi_link CHECK (role <> 'PI' OR researcher_id IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE funding_agency (
  agency_id      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  agency_name    VARCHAR(120) NOT NULL UNIQUE,
  agency_type    ENUM('Government','Private','Industry','International','Institutional') NOT NULL,
  country        VARCHAR(60) NOT NULL DEFAULT 'India',
  contact_email  VARCHAR(120),
  website        VARCHAR(200),
  CONSTRAINT chk_ag_email CHECK (contact_email IS NULL OR contact_email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project (
  project_id     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  project_code   VARCHAR(20)  NOT NULL UNIQUE,          -- e.g. RP-2024-001
  title          VARCHAR(200) NOT NULL,
  abstract       TEXT,
  dept_id        INT UNSIGNED NOT NULL,
  start_date     DATE NOT NULL,
  end_date       DATE NOT NULL,
  status         ENUM('Proposed','Active','On Hold','Completed','Cancelled') NOT NULL DEFAULT 'Proposed',
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_proj_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_proj_dates CHECK (end_date > start_date),                      -- BR-01
  CONSTRAINT chk_proj_code  CHECK (project_code REGEXP '^RP-[0-9]{4}-[0-9]{3}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project_investigator (
  project_id     INT UNSIGNED NOT NULL,
  researcher_id  INT UNSIGNED NOT NULL,
  role           ENUM('PI','Co-PI','Researcher','Research Scholar') NOT NULL,
  assigned_date  DATE NOT NULL,
  effort_percent DECIMAL(5,2) NOT NULL DEFAULT 10.00,
  -- trick: exactly one PI per project. pi_flag is 1 only for PI rows, NULL otherwise;
  -- UNIQUE allows many NULLs but only one '1' per project.
  pi_flag        TINYINT GENERATED ALWAYS AS (IF(role = 'PI', 1, NULL)) STORED,
  PRIMARY KEY (project_id, researcher_id),
  UNIQUE KEY uq_one_pi_per_project (project_id, pi_flag),                       -- BR-10
  CONSTRAINT fk_pi_proj FOREIGN KEY (project_id)    REFERENCES project(project_id)
                        ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_pi_res  FOREIGN KEY (researcher_id) REFERENCES researcher(researcher_id)
                        ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_pi_effort CHECK (effort_percent > 0 AND effort_percent <= 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE grant_award (
  grant_id       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  grant_number   VARCHAR(40) NOT NULL UNIQUE,
  project_id     INT UNSIGNED NOT NULL,
  agency_id      INT UNSIGNED NOT NULL,
  grant_amount   DECIMAL(14,2) NOT NULL,
  sanction_date  DATE NOT NULL,
  grant_start    DATE NOT NULL,
  grant_end      DATE NOT NULL,
  status         ENUM('Sanctioned','Active','Closed','Terminated') NOT NULL DEFAULT 'Sanctioned',
  CONSTRAINT fk_gr_proj   FOREIGN KEY (project_id) REFERENCES project(project_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_gr_agency FOREIGN KEY (agency_id)  REFERENCES funding_agency(agency_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_gr_amount CHECK (grant_amount > 0),                            -- BR-05
  CONSTRAINT chk_gr_dates  CHECK (grant_end > grant_start AND grant_start >= sanction_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE budget_head (
  head_id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  head_name      VARCHAR(50) NOT NULL UNIQUE,
  description    VARCHAR(200)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE grant_budget_allocation (
  grant_id         INT UNSIGNED NOT NULL,
  head_id          INT UNSIGNED NOT NULL,
  allocated_amount DECIMAL(14,2) NOT NULL,
  PRIMARY KEY (grant_id, head_id),
  CONSTRAINT fk_alloc_grant FOREIGN KEY (grant_id) REFERENCES grant_award(grant_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_alloc_head  FOREIGN KEY (head_id)  REFERENCES budget_head(head_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_alloc_amount CHECK (allocated_amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE expenditure (
  expenditure_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  grant_id       INT UNSIGNED NOT NULL,
  head_id        INT UNSIGNED NOT NULL,
  expense_date   DATE NOT NULL,
  amount         DECIMAL(14,2) NOT NULL,
  description    VARCHAR(250) NOT NULL,
  voucher_no     VARCHAR(30) NOT NULL UNIQUE,
  recorded_by    INT UNSIGNED,
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  -- composite FK: you can only spend on a head that was actually allocated for that grant
  CONSTRAINT fk_exp_alloc FOREIGN KEY (grant_id, head_id)
                          REFERENCES grant_budget_allocation(grant_id, head_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_exp_user  FOREIGN KEY (recorded_by) REFERENCES user_account(user_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_exp_amount CHECK (amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE milestone (
  milestone_id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  project_id     INT UNSIGNED NOT NULL,
  title          VARCHAR(150) NOT NULL,
  description    VARCHAR(500),
  due_date       DATE NOT NULL,
  completed_date DATE,
  status         ENUM('Pending','In Progress','Completed','Delayed') NOT NULL DEFAULT 'Pending',
  UNIQUE KEY uq_milestone_title (project_id, title),
  CONSTRAINT fk_ms_proj FOREIGN KEY (project_id) REFERENCES project(project_id)
                        ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_ms_completion CHECK (
      (status = 'Completed' AND completed_date IS NOT NULL) OR
      (status <> 'Completed' AND completed_date IS NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;                                  -- BR-04 (dates inside project) is a trigger

CREATE TABLE publication (
  publication_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title          VARCHAR(300) NOT NULL,
  pub_type       ENUM('Journal','Conference','Book Chapter','Book','Preprint') NOT NULL,
  venue          VARCHAR(200) NOT NULL,                -- journal / conference / publisher name
  doi            VARCHAR(100) UNIQUE,                  -- BR-08 unique publication identifier
  issn_isbn      VARCHAR(20),
  pub_date       DATE NOT NULL,
  indexing       ENUM('Scopus','SCI','SCIE','WoS','UGC-CARE','None') NOT NULL DEFAULT 'None',
  citation_count INT UNSIGNED NOT NULL DEFAULT 0,
  CONSTRAINT chk_pub_doi CHECK (doi IS NULL OR doi REGEXP '^10\\.[0-9]{4,9}/.+$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE publication_author (
  publication_id  INT UNSIGNED NOT NULL,
  researcher_id   INT UNSIGNED NOT NULL,
  author_order    TINYINT UNSIGNED NOT NULL,
  is_corresponding BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (publication_id, researcher_id),
  UNIQUE KEY uq_author_order (publication_id, author_order),
  CONSTRAINT fk_pa_pub FOREIGN KEY (publication_id) REFERENCES publication(publication_id)
                       ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_pa_res FOREIGN KEY (researcher_id)  REFERENCES researcher(researcher_id)
                       ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_pa_order CHECK (author_order >= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project_publication (
  project_id     INT UNSIGNED NOT NULL,
  publication_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (project_id, publication_id),
  CONSTRAINT fk_pp_proj FOREIGN KEY (project_id)     REFERENCES project(project_id)         ON DELETE CASCADE,
  CONSTRAINT fk_pp_pub  FOREIGN KEY (publication_id) REFERENCES publication(publication_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE patent (
  patent_id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  application_number VARCHAR(40) NOT NULL UNIQUE,
  patent_number      VARCHAR(40) UNIQUE,                -- NULL until granted
  title              VARCHAR(300) NOT NULL,
  jurisdiction       VARCHAR(40) NOT NULL DEFAULT 'India',
  filing_date        DATE NOT NULL,
  grant_date         DATE,
  status             ENUM('Filed','Published','Granted','Rejected','Lapsed') NOT NULL DEFAULT 'Filed',
  CONSTRAINT chk_pat_dates  CHECK (grant_date IS NULL OR grant_date >= filing_date),
  CONSTRAINT chk_pat_status CHECK ((status = 'Granted' AND grant_date IS NOT NULL AND patent_number IS NOT NULL)
                                   OR status <> 'Granted')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE patent_inventor (
  patent_id     INT UNSIGNED NOT NULL,
  researcher_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (patent_id, researcher_id),
  CONSTRAINT fk_pi2_pat FOREIGN KEY (patent_id)     REFERENCES patent(patent_id)       ON DELETE CASCADE,
  CONSTRAINT fk_pi2_res FOREIGN KEY (researcher_id) REFERENCES researcher(researcher_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project_patent (
  project_id INT UNSIGNED NOT NULL,
  patent_id  INT UNSIGNED NOT NULL,
  PRIMARY KEY (project_id, patent_id),
  CONSTRAINT fk_ppt_proj FOREIGN KEY (project_id) REFERENCES project(project_id) ON DELETE CASCADE,
  CONSTRAINT fk_ppt_pat  FOREIGN KEY (patent_id)  REFERENCES patent(patent_id)   ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE report (
  report_id      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  project_id     INT UNSIGNED NOT NULL,
  report_type    ENUM('Progress','Financial','Utilization Certificate','Final') NOT NULL,
  period_start   DATE NOT NULL,
  period_end     DATE NOT NULL,
  submitted_on   DATE,
  submitted_by   INT UNSIGNED,
  summary        TEXT,
  status         ENUM('Draft','Submitted','Accepted','Returned') NOT NULL DEFAULT 'Draft',
  CONSTRAINT fk_rep_proj FOREIGN KEY (project_id)   REFERENCES project(project_id)       ON DELETE RESTRICT,
  CONSTRAINT fk_rep_user FOREIGN KEY (submitted_by) REFERENCES user_account(user_id)     ON DELETE RESTRICT,
  CONSTRAINT chk_rep_period CHECK (period_end >= period_start),
  CONSTRAINT chk_rep_submit CHECK ((status = 'Draft' AND submitted_on IS NULL AND submitted_by IS NULL) OR
                                      (status <> 'Draft' AND submitted_on IS NOT NULL AND submitted_by IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE audit_log (
  log_id      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  table_name  VARCHAR(40) NOT NULL,
  record_id   VARCHAR(40) NOT NULL,
  action      ENUM('INSERT','UPDATE','DELETE') NOT NULL,
  old_values  JSON,
  new_values  JSON,
  changed_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  changed_by  VARCHAR(80) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Agent note:** If any statement above fails on the installed MySQL version, fix it minimally, record the change in `docs/decisions.md`, and keep the intent (the rule it enforces) identical.

---

## 5. BUSINESS RULES (each must be enforced in the DB and have a test)

| ID | Rule | Enforcement in the integrated design |
|---|---|---|
| BR-01 | Project `end_date` must be after `start_date` | CHECK `chk_proj_dates` |
| BR-02 | Grant dates must satisfy `grant_end > grant_start` and `grant_start >= sanction_date`; changing grant dates cannot strand existing expenditures | CHECK `chk_gr_dates` plus `grant_award` BEFORE UPDATE trigger verifies every existing expenditure remains inside the new period |
| BR-03 | Grant period must fit inside its project's dates; changing project dates cannot strand an existing grant | Triggers on `grant_award` (BEFORE INSERT/UPDATE) and `project` (BEFORE UPDATE) |
| BR-04 | Milestone due/completion dates must fit inside the project's dates; changing project dates cannot strand existing milestones | Triggers on `milestone` (BEFORE INSERT/UPDATE) and `project` (BEFORE UPDATE) |
| BR-05 | Grant amount, each budget allocation and each expenditure amount must be positive | CHECK constraints |
| BR-06 | Sum of expenditure for each grant+head ≤ that head's allocation, and sum of expenditure for a grant ≤ `grant_amount` | Transaction-owning `sp_record_expenditure`; lock grant row then allocation row, re-read totals at READ COMMITTED, insert atomically. Runtime app account has no direct expenditure DML. No aggregate expenditure check in a trigger. |
| BR-07 | Expense date must fall within the grant period | `sp_record_expenditure` and expenditure BEFORE INSERT/UPDATE triggers |
| BR-08 | DOI must be unique when present and match the DOI format | UNIQUE `publication.doi` + CHECK `chk_pub_doi`; application maps duplicate/format failures to BR-08 |
| BR-09 | Sum of a grant's budget allocations ≤ `grant_amount`; a grant amount cannot be reduced below existing allocations or spending | `sp_add_grant_with_budget` validates all allocations before insert; `grant_award` BEFORE UPDATE trigger rejects a reduction below allocations or spend. Runtime account has no direct grant/allocation DML. |
| BR-10 | Exactly one PI per committed project; PI transfer is atomic and a PI cannot be removed/demoted through a generic action | Generated-column UNIQUE key prevents more than one PI; `sp_register_project` creates project + PI atomically; `sp_change_project_pi` performs transfer; PI-protection triggers block removal/demotion except the controlled transfer path. Runtime account has no direct project/team DML. |
| BR-11 | A researcher's combined effort across Proposed/Active projects cannot exceed 100%, including when a project enters Proposed/Active | `sp_register_project`, `sp_assign_investigator`, `sp_change_project_pi` and `sp_update_project_status` lock affected researcher rows in ascending ID order and validate workload in the transaction. Runtime account has no direct project-status/team DML. |
| BR-12 | Only active researchers may be assigned to projects | `sp_register_project`, `sp_assign_investigator` and `sp_change_project_pi` validate active status; lightweight BEFORE INSERT/UPDATE triggers provide a defensive check. |
| BR-13 | A milestone is Completed if and only if `completed_date` is populated | CHECK `chk_ms_completion` |
| BR-14 | A Granted patent must have `grant_date` and `patent_number`; grant date cannot be before filing date | CHECK constraints `chk_pat_dates` and `chk_pat_status` |
| BR-15 | Expenditure must reference a budget head allocated to that grant | Composite FK `fk_exp_alloc(grant_id, head_id)` |
| BR-16 | Publication date cannot precede the start of any project linked to it | Triggers on `project_publication` (BEFORE INSERT/UPDATE), `publication` (BEFORE UPDATE), and `project` (BEFORE UPDATE of `start_date`) |
| BR-17 | Completed/Cancelled projects cannot receive new expenditures or milestones | Expenditure and milestone BEFORE INSERT/UPDATE triggers plus procedure validation |
| BR-18 | A researcher can appear only once per publication and author order must be unique within that publication | PRIMARY KEY and UNIQUE key on `publication_author` plus input validation |

**MySQL aggregate-rule design (important):** do not calculate BR-06 by selecting `SUM(expenditure)` from a trigger attached to `expenditure`, and do not enforce BR-11 by aggregating `project_investigator` from its own trigger. Such self-table trigger patterns can fail because of MySQL stored-program restrictions and do not provide a safe concurrency boundary. All guarded aggregate writes must pass through transaction-owning `SQL SECURITY DEFINER` stored procedures. The runtime app account is denied direct INSERT/UPDATE/DELETE on `project`, `project_investigator`, `grant_award`, `grant_budget_allocation` and `expenditure`; it also cannot update `project.status` directly. Setup/schema-owner credentials are separate from the Flask runtime credential. They are used only for schema initialization and controlled test setup; never use them in the running Flask app.

**Concurrency rules:**
- `sp_record_expenditure` locks the `grant_award` row first (serializing all spend attempts for that grant), then the relevant allocation row. It performs fresh aggregate reads under READ COMMITTED after obtaining those locks, validates head and grant limits, inserts the expenditure, and commits. This protects the grant-wide limit even when two spend attempts target different heads.
- Investigator assignment, removal, PI transfer and project status changes lock relevant researcher rows in ascending `researcher_id` order before calculating effort. Assignment also locks the target project row. This common lock order prevents concurrent changes from exceeding 100% or creating avoidable deadlocks.
- Project creation must go through `sp_register_project`, which inserts the project and its PI in a single transaction. The generated-column UNIQUE key guarantees **at most** one PI; the procedure and PI-protection triggers guarantee at least one PI after every committed application change.
- `sp_update_project_status` may set only Proposed / Active / On Hold and must reject an already Completed/Cancelled project. `sp_close_project` may transition a non-terminal project to Completed or Cancelled only. Completed requires no Pending/In Progress/Delayed milestones; Cancelled may retain unfinished milestones as historical records. On close, Sanctioned/Active grants become Closed for Completed projects or Terminated for Cancelled projects.
- The grant amount update trigger validates `NEW.grant_amount` against the existing allocation total and total expenditure. Allocation rows are inserted only by `sp_add_grant_with_budget`; any future allocation-edit feature must use a new transaction-owning procedure with the same aggregate check and locking. No application route currently edits allocation rows.
- BR-02/07: a `grant_award` BEFORE UPDATE trigger must reject any new grant period that would put an already-recorded expenditure outside the proposed `grant_start`/`grant_end`; it must also validate the new period against the sanction date and project dates. BR-16 is checked when a project-publication link is inserted/updated, when `publication.pub_date` changes, and when a linked project's `start_date` changes. Each cross-table update checks existing related rows before accepting the change.

**Error message convention:** trigger/procedure failures use a stable `BR-xx` prefix, for example:
`SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'BR-06: Expenditure exceeds the allocation for this budget head';`
Native MySQL CHECK, UNIQUE and FK failures cannot carry a custom BR message. `app/errors.py` maps native constraint names/MySQL error numbers to the same friendly BR message. Tests assert the prefix for custom trigger/procedure failures and verify the named constraint plus normalized error mapping for native errors; never claim the raw native SQL error has a prefix.

### Reference trigger (row-level expenditure checks only; no aggregate sums)

```sql
DELIMITER $$
CREATE TRIGGER trg_expenditure_bi BEFORE INSERT ON expenditure
FOR EACH ROW
BEGIN
  DECLARE v_start DATE;
  DECLARE v_end DATE;
  DECLARE v_project_status VARCHAR(20);

  SELECT g.grant_start, g.grant_end, p.status
    INTO v_start, v_end, v_project_status
    FROM grant_award AS g
    JOIN project AS p ON p.project_id = g.project_id
   WHERE g.grant_id = NEW.grant_id;

  IF v_project_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: Project is closed; no new expenditure allowed';
  END IF;
  IF NEW.expense_date < v_start OR NEW.expense_date > v_end THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-07: Expense date is outside the grant period';
  END IF;
  -- BR-06 is checked only by sp_record_expenditure after parent/allocation locks.
  -- Do not SELECT SUM(...) from expenditure in this trigger.
END$$
DELIMITER ;
```
Create an analogous BEFORE UPDATE trigger using `NEW.grant_id` and `NEW.expense_date` for BR-07/17. The runtime app account has no direct UPDATE permission on `expenditure`; the trigger remains defensive for setup/maintenance. Any future correction route must use a new transaction-owning procedure that revalidates both aggregate caps.

### Audit triggers
Create AFTER INSERT/UPDATE/DELETE audit triggers on `project`, `project_investigator`, `researcher`, `grant_award`, `grant_budget_allocation`, `expenditure`, `milestone`, `publication`, `publication_author`, `project_publication`, `patent`, `patent_inventor`, `project_patent`, `report` and `user_account`, writing `JSON_OBJECT(...)` old/new values into `audit_log`. Do not create audit triggers on `audit_log` itself. Use composite keys (for example, `project_id:researcher_id`) as `record_id` for junction tables. The runtime Flask account may INSERT into `user_account` only through the validated Admin user-creation service. Grant column-level UPDATE on `username`, `role`, `researcher_id` and `is_active` only; do not grant UPDATE on `password_hash`. It must not delete accounts. If password reset is added later, implement it as a dedicated validated service/procedure with a separately reviewed privilege path. Every audit insert must populate the now-required `changed_by` column with `COALESCE(@rpgms_actor, USER())`. For `user_account`, record only username, role, researcher_id and is_active—never `password_hash`. The application sets the session variable `@rpgms_actor` to the authenticated username on the checked-out connection before writes. Clear `@rpgms_actor` in a `finally` block before returning a pooled connection so the next request cannot inherit the previous user's identity. The same cleanup guarantee applies to the narrowly-scoped PI-transfer session flag.

---

## 6. STORED PROCEDURES (`db/03_procedures.sql`) — transaction awareness

Every transaction-owning routine is declared `SQL SECURITY DEFINER`, sets `SET TRANSACTION ISOLATION LEVEL READ COMMITTED` before `START TRANSACTION`, declares an `EXIT HANDLER FOR SQLEXCEPTION` that rolls back, clears any controlled session flag, and `RESIGNAL`s, and commits only after all validations and writes succeed. Set transaction characteristics before `START TRANSACTION`; never start a second transaction inside an existing transaction. Flask calls these routines using a dedicated `call_procedure()` helper on a connection with autocommit enabled and no active transaction; the helper drains every result set. Never wrap a transaction-owning procedure in `run_transaction()`. Direct multi-statement write flows not delegated to a procedure use `run_transaction()`.

| Procedure | What it must do atomically |
|---|---|
| `sp_register_project(code, title, abstract, dept_id, start, end, pi_researcher_id, pi_effort)` | Lock and validate the active PI; validate the project dates/code and combined workload (BR-01/11/12); insert project and PI assignment in one transaction. Roll back both on any failure. |
| `sp_assign_investigator(project_id, researcher_id, role, effort_percent)` | Lock the target project and researcher row; reject terminal projects, inactive researchers and role `PI` (PI changes use the separate transfer procedure); validate effort and total Proposed/Active workload ≤100; insert non-PI assignment atomically. |
| `sp_remove_investigator(project_id, researcher_id)` | Lock project and researcher; remove only a non-PI assignment; reject missing assignment/current PI/terminal project; commit atomically. |
| `sp_add_grant_with_budget(grant_number, project_id, agency_id, amount, sanction, gstart, gend, allocations_json)` | Lock and validate project; reject Completed/Cancelled projects; require a non-empty JSON array of distinct budget-head allocations, each positive; validate grant dates against project and sanction dates; ensure allocation total ≤ grant amount; insert grant + all allocations together. All-or-nothing. |
| `sp_record_expenditure(grant_id, head_id, expense_date, amount, description, voucher_no, user_id)` | Lock grant row first, then matching budget-allocation row; allow only Sanctioned/Active grants and non-terminal projects; validate date and positive amount; re-read spend totals under READ COMMITTED; enforce both per-head and grant-wide caps (BR-06/07/17); insert expense and return remaining head/grant balances. This is the only runtime path for expenditure inserts. |
| `sp_update_milestone_status(milestone_id, new_status)` | First read the milestone’s `project_id` without a lock; then lock the project row and afterward the milestone row, re-checking the relationship. Accept only Pending / In Progress / Delayed; reject terminal projects; revalidate due date within project dates; set status and clear `completed_date` atomically. This project-before-milestone lock order matches project closure/date changes and avoids lock-order deadlocks. |
| `sp_complete_milestone(milestone_id, completed_date)` | First read the milestone’s `project_id` without a lock; then lock the project row and afterward the milestone row, re-checking the relationship. Reject Completed or Cancelled projects; validate completion date inside project dates; set status Completed and `completed_date` together. Use the same project-before-milestone lock order as project closure. |
| `sp_update_project_status(project_id, new_status)` | Lock project; accept only Proposed / Active / On Hold; reject terminal projects; when switching into Proposed/Active, lock all assigned researchers in ascending ID order and enforce BR-11. |
| `sp_close_project(project_id, new_status)` | Lock project; accept only Completed/Cancelled from a non-terminal project. For Completed, block while any Pending/In Progress/Delayed milestone remains; for Cancelled, unfinished milestones remain as history. Update Sanctioned/Active grants to Closed (Completed) or Terminated (Cancelled) in the same transaction. |
| `sp_change_project_pi(project_id, new_researcher_id, new_effort)` | Lock project and old/new researcher rows in ascending researcher ID order; validate the new researcher is active and the workload remains ≤100; within one transaction, demote the old PI first and then promote the existing new member or insert the new PI row, avoiding the generated-column UNIQUE conflict; use a narrowly-scoped session flag for PI-protection triggers and clear it on both success and failure. Exactly one PI remains after commit. |

**Runtime privileges (implement as explicit GRANT statements and test them):** the Flask account gets SELECT on only the tables/views needed by the app and EXECUTE on the transaction-owning procedures. Deny direct INSERT/UPDATE/DELETE on `project`, `project_investigator`, `grant_award`, `grant_budget_allocation` and `expenditure`; those writes go only through their approved procedures. Deny direct UPDATE/DELETE on `milestone`; allow INSERT only through the validated service, with BR-04/BR-17 triggers authoritative. Permit INSERT/UPDATE on `researcher` for ADMIN/RESEARCH_OFFICER routes; INSERT/UPDATE on `publication` and `patent` only for ADMIN/RESEARCH_OFFICER; INSERT on `publication_author`, `project_publication`, `patent_inventor` and `project_patent` only through validated services; INSERT/UPDATE on `report` only through the report service; INSERT on `user_account` only through the Admin user-creation service and column-level UPDATE on `username`, `role`, `researcher_id` and `is_active` only (never `password_hash`). Deny direct DELETE on user, project, team, financial and historical records, and deny direct writes to `audit_log`. Scope route-level permissions in Flask services as well as in the UI. Procedure definers need the local schema privileges required for the routines and audit trigger writes. Never run Flask using the setup/schema-owner account. Add a startup/integration test that confirms the runtime account cannot bypass protected aggregate rules.

---

## 7. VIEWS (`db/04_views.sql`)

| View | Columns / purpose |
|---|---|
| `vw_project_overview` | project, dept, PI name, status, dates, total grant amount, total spent |
| `vw_project_progress` | project, total milestones, completed, % complete (NULL when no milestones), overdue count, days remaining, time-elapsed % (clamped 0–100); RAG presentation handles Proposed/future-start projects as `Not started`, no-milestone projects as `Not rated`, and terminal projects as described for R1 |
| `vw_budget_utilization` | grant, project, agency, grant_amount, total_spent, balance, utilization_pct, health flag: `Under 50%` for utilization <50%; `On Track` for ≥50% and <90%; `Near Limit` for ≥90% and <100%; `Exhausted` when balance is zero / utilization is 100% |
| `vw_budget_head_utilization` | grant, head, allocated, spent, remaining, pct |
| `vw_milestone_tracker` | milestone, project, due date, status, `days_overdue` (computed from `CURDATE()`), `is_overdue` flag |
| `vw_researcher_output` | researcher, dept, #projects, #as PI, #publications, #indexed publications, #patents, total grant value led as PI |
| `vw_agency_portfolio` | agency, #grants, #projects funded, total sanctioned, total spent, avg grant size |
| `vw_project_publications` | project, publication, type, venue, year, DOI, author list (use `GROUP_CONCAT`) |
| `vw_department_summary` | dept, #researchers, #projects, #active projects, total funding, #publications |

**Rule:** never store derived numbers (total spent, balance, % complete) as columns in base tables. Derive them in views. (This is part of staying in 3NF — document it.)

**Aggregate correctness rule:** whenever a view or report combines multiple one-to-many relationships (for example, projects → grants → expenditures alongside project → publications), aggregate each relationship to the correct grain in a separate derived table/CTE before joining. Never sum a grant amount after joining it to multiple expenditure rows, or count publications after joining them to multiple authors/projects, because join fan-out silently inflates totals. Tests must compare view/report totals with independent source-table sums and use a fixture containing multiple grants, expenses and publications per project.

---

## 8. SQL QUERY SET (`db/07_queries.sql`) — 40 numbered, commented queries

Each query must have a header comment: `-- Q07: <plain-language question>` and run successfully on the seed data. After running, copy a short sample of the output into `docs/test_report.md`.

**A. Basic retrieval (Q01–Q06)**
1. All active projects with start and end dates, sorted by end date.
2. Researchers of a given department (parameter-style with a variable).
3. Projects whose title or abstract contains a keyword (`LIKE` and also a `MATCH ... AGAINST` FULLTEXT version).
4. Grants sanctioned in a given calendar year.
5. Researchers who joined after a given date, with designation filter using `IN`.
6. Patents that are Granted, newest first.

**B. Joins (Q07–Q16)**
7. Project list with department name and PI full name (INNER JOIN, 3 tables).
8. Every project with its funding agency names (JOIN through `grant_award`).
9. Researchers with the number of projects they work on — **including those with zero** (LEFT JOIN).
10. Projects that have **no** grant yet (LEFT JOIN … IS NULL).
11. Publications with all authors in order, and the project(s) they are linked to.
12. Self-join: pairs of researchers who are co-authors on at least one publication.
13. Expenditure details: voucher, date, amount, head name, grant number, project title (5-table join).
14. Researchers who are both an inventor on a patent and an author of a publication (INNER JOIN of two derived sets).
15. Departments and their funding agencies (distinct) via projects and grants.
16. RIGHT JOIN/UNION demo: all researchers and all patents even where unmatched (FULL OUTER JOIN emulation).

**C. Aggregates (Q17–Q26)**
17. Total sanctioned grant amount per funding agency.
18. Average grant size per agency type.
19. Number of projects per department, with `HAVING` ≥ 2.
20. Total expenditure per project per budget head.
21. Publications per year and per type (`GROUP BY` with `ROLLUP`).
22. Top 5 researchers by number of publications.
23. Department-wise total funding and average funding per project.
24. Months with the highest total expenditure (`DATE_FORMAT`).
25. Count of milestones by status per project.
26. Max, min and average citation count per indexing category.

**D. Nested / subqueries (Q27–Q34)**
27. Projects whose total grant is above the average total grant (scalar subquery).
28. Researchers who have never authored a publication (`NOT EXISTS`).
29. Projects with at least one overdue milestone (`EXISTS`).
30. Grants where spending is above 80% of the grant amount (derived table).
31. Researchers who are PI on more than one project (`IN` + `GROUP BY`).
32. Agencies that fund projects in **every** department (relational division using double `NOT EXISTS`).
33. Projects with total expenditure greater than **all** milestone-less projects' expenditure (`> ALL`).
34. The latest expenditure for each grant (correlated subquery).

**E. Advanced (Q35–Q40)**
35. Rank researchers within each department by publication count (`RANK() OVER (PARTITION BY ...)`).
36. Running total of expenditure per grant by date (`SUM() OVER`).
37. Month-over-month spending change using `LAG()`.
38. CTE: project hierarchy summary — project → milestones done → spend → publications.
39. Set operations: researchers who authored publications `UNION`/`INTERSECT`-style (emulate INTERSECT with `IN`) with those who hold patents.
40. A query using a view (`vw_budget_utilization`) joined to `vw_project_progress` to flag "high spend, low progress" projects.

---

## 9. REPORTS (`db/08_reports.sql` + Reports page)

| # | Report | Content |
|---|---|---|
| R1 | **Project Progress** | Per project for ADMIN/RESEARCH_OFFICER and authorized PI: status, % milestones complete, elapsed-time %, overdue count and RAG. Red when at least one milestone is overdue and completion trails elapsed time by ≥15 percentage points; otherwise Amber when any milestone is overdue or completion trails elapsed time by >0 points; Green only when no milestone is overdue and completion is at/ahead of elapsed time. Proposed projects or projects whose start date is in the future are `Not started` with a neutral badge; zero-milestone active projects are `Not rated` (never divide by zero); Completed/Cancelled projects are `Closed` with a neutral badge. Viewer output is aggregated by department/status and omits project identifiers. |
| R2 | **Budget Utilization** | Per grant: amount, spent, balance, % used, health flag; with per-head breakdown drill-down |
| R3 | **Milestone Tracker** | All milestones with due date, status, days overdue; filter by project/department/status |
| R4 | **Researcher Output** | Per researcher: projects, publications (indexed vs not), patents, grant value led |
| R5 | **Funding Agency Portfolio** | Per agency: grants, projects, sanctioned, spent, average grant; share of total funding |
| R6 | **Publications Report** | By year/type/indexing/department, with linked projects |
| R7 | **Department Summary** | Researchers, projects, funding, output per department |
| R8 | **Expenditure Statement** | Date-range statement for a grant: every voucher + running balance |
| R9 | **Patent Status** | Patents by status and jurisdiction with linked projects and inventors |
| R10 | **Closing/Utilization Summary** | For completed projects: total granted, total spent, unspent balance, deliverables (publications + patents) |

**Viewer-safe report output (required):** use separate aggregate queries/serializers, not template-only hiding. R1 groups progress counts/RAG by department and status; R2 groups grant count and sums by health category; R3 groups milestone counts by month/status; R4 groups researcher output counts by department (no researcher names); R5 may show agency-level totals but no grant/project identifiers; R6 groups publications by year/type/indexing/department (no title, DOI, author or project identifiers); R7 is the department aggregate; R8 gives monthly totals and aggregate running balance (no vouchers or grant numbers); R9 groups patents by status/jurisdiction (no patent number, title, inventor or project); R10 gives a combined completed-project summary (no project identifiers). Viewer-safe filters must likewise be aggregate filters (date range, status, department or category), never a lookup by individual person, project, grant or record ID. Viewer chart datasets, tooltips and CSV exports must be built from these same aggregate result sets.

The Reports page must offer for each report: filters, a data table, a Chart.js chart where it meaningfully helps (R1 bar, R2 stacked/percent bar, R4 bar, R5 pie/donut, R6 grouped bar, plus charts defined in Part A), and a **Download CSV** button. Use Chart.js only; do not add Plotly as a second chart stack. CSV exports must use the same validated filters and authorization scope as the visible report. ADMIN/RESEARCH_OFFICER and authorized PI views use the report’s detailed output within their scope. VIEWER gets a dedicated aggregate/sanitized output for each R1–R10 report; no record-level identifiers or personal details may leak through tables, tooltips, downloadable CSV, DOM attributes, API JSON, error messages, or chart datasets.

---

## 10. INDEXING (`db/05_indexes.sql` + `docs/indexing.md`)

Primary/unique keys and MySQL-created foreign-key support indexes already create indexes. Do not create duplicate copies of the simple child-key indexes on `researcher.dept_id`, `grant_award.project_id`, `expenditure(grant_id, head_id)`, `publication_author.researcher_id` or `project_investigator.researcher_id`. Add the following additional indexes for frequently searched/filtered/joined columns:

```sql
CREATE INDEX idx_proj_status_dept   ON project(status, dept_id);
CREATE INDEX idx_proj_dates         ON project(start_date, end_date);
CREATE INDEX idx_res_name           ON researcher(last_name, first_name);
CREATE INDEX idx_grant_agency       ON grant_award(agency_id, status);
CREATE INDEX idx_exp_grant_date     ON expenditure(grant_id, expense_date);
CREATE INDEX idx_ms_proj_status_due ON milestone(project_id, status, due_date);
CREATE INDEX idx_pub_date           ON publication(pub_date);
CREATE FULLTEXT INDEX ft_project_text ON project(title, abstract);
CREATE FULLTEXT INDEX ft_pub_title    ON publication(title);
```

**Evidence required in `docs/indexing.md`:** for at least 4 queries, show `EXPLAIN` **before** and **after** creating the index (use `DROP INDEX` / `CREATE INDEX` to demonstrate; seed enough extra rows — e.g., a script that bulk-inserts 20,000 expenditure rows into a **separate scratch table** — so the difference is visible). Explain in plain words: *an index is like the index at the back of a book — without it MySQL reads every page.*

---

## 11. SAMPLE DATA (`db/06_seed.sql`)

Plain `INSERT` statements in dependency order, deterministic, rerunnable after a reset. Realistic Indian-university context, amounts in INR, dates between 2022 and 2027. The seeded records should remain useful for repeatable tests; computed overdue/utilization values must be derived using `CURDATE()` rather than hard-coded into the UI.

**Minimum volumes**

| Table | Rows |
|---|---|
| department | 6 (CSE, ECE, Mechanical, Civil, Biotechnology, Chemistry) |
| researcher | 24 (mix of designations, one inactive) |
| user_account | 6 (1 ADMIN, 1 RESEARCH_OFFICER, 3 PI, 1 VIEWER) — bcrypt hashes; demo password documented in README |
| funding_agency | 9 (e.g., DST, SERB, DBT, ICMR, CSIR, ISRO, AICTE, one industry sponsor, one international) |
| budget_head | 6 |
| project | 15 (mix of Proposed/Active/On Hold/Completed/Cancelled) |
| project_investigator | ~45 |
| grant_award | 16 (some projects with 2 grants, 2 projects with none) |
| grant_budget_allocation | ~60 |
| expenditure | ~90 |
| milestone | ~55 |
| publication | 30 (all types, indexed and not) |
| publication_author | ~80 |
| project_publication | ~35 |
| patent | 7 (Filed, Published, Granted, Rejected, Lapsed) |
| patent_inventor / project_patent | ~12 / ~8 |
| report | ~20 |

**Deliberate edge cases the data must contain** (so queries and reports have something to show):
- one grant at ≥ 95% utilisation and one head fully exhausted,
- at least 4 milestones with due dates safely in the past (for example, in 2025), still Pending/In Progress/Delayed, attached to projects whose date ranges include those milestones;
- one Cancelled project with partial spending,
- two researchers with zero publications and one with zero projects,
- one researcher who is PI on two projects,
- one publication linked to two projects,
- two agencies funding projects in several departments,
- one researcher who is both patent inventor and publication author,
- a project with a grant but no expenditure yet.

All seed rows must pass every trigger — the seed script itself is a test of the business rules. After loading, run row counts for every table and paste them into `docs/test_report.md`.

---

## 12. APPLICATION (integrated Flask/Jinja2 implementation)

### 12.1 Global behaviour
- **Login page** (`auth` blueprint): username + password, bcrypt verify, Flask session holds `user_id`, `username`, `role`, `researcher_id`. Failed login shows a generic message; rotate the session on successful login. Logout is a CSRF-protected POST.
- **Role-based page access** enforced in `auth.py` (`require_role([...])` at the top of each page). A PI only sees projects where they are PI.
- **DB layer** (`db.py`): connection pool; `run_query(sql, params)` returns rows as dictionaries suitable for Jinja templates; `run_transaction()` is a context manager that commits on success and rolls back on any exception. Configure pooled sessions for `READ COMMITTED`, use parameterized SQL, set the authenticated actor variable for write requests, and clear that variable before returning a connection. Calls to transaction-owning stored procedures must not be wrapped by `run_transaction()`.
- **Security config** (`__init__.py` / `config.py`): read `SECRET_KEY` from `.env` and refuse startup if absent in every non-test environment (tests may inject a unique ephemeral key explicitly); enable CSRF protection on every POST form (including login/logout); set session cookies `HttpOnly` and `SameSite=Lax`, and enable `Secure` when serving over HTTPS. Never commit `.env`; `.env.example` contains placeholders only. Do not put password hashes or secrets in logs.
- **Errors**: catch `mysql.connector.Error`, pass through `errors.py` → friendly text such as *"This expense would exceed the remaining budget for 'Equipment' (₹ 1,25,000 left)."* Never show raw stack traces to the user.
- **Currency** formatted in Indian style (₹ 12,34,567.00).

### 12.2 Pages and required functions

| Page | Features |
|---|---|
| **Dashboard** | KPI cards (active projects, total sanctioned, total spent, overdue milestones, publications this year); chart of spend by agency; list of top 5 overdue milestones; budget-health table (Near Limit/Exhausted grants) |
| **Projects** | *Register project* form (calls `sp_register_project`), searchable/filterable list (status, dept, keyword), project detail view (investigators, grants, milestones, publications, patents, reports), status changes use `sp_update_project_status` for Proposed/Active/On Hold and `sp_close_project` for Completed/Cancelled |
| **Investigators** | Assign researcher to project with role and effort %; remove assignment; view a researcher's workload; add/edit researcher records |
| **Grants & Budget** | Enter grant + budget allocations in one form (calls `sp_add_grant_with_budget`); live "unallocated amount" counter; view grant list and per-head allocation chart |
| **Milestones** | Add milestone; update status through `sp_update_milestone_status`; complete through `sp_complete_milestone`; tracker table with overdue highlighting |
| **Expenditure** | Searchable recent-expense list at `/expenditure`; ADMIN/RESEARCH_OFFICER can open the entry form, while PI has read-only own-project rows. Entry flow picks grant → head → **live remaining balance** → amount/date/voucher → submit via `sp_record_expenditure`; statement view has running balance; blocked spending shows a friendly BR-06 message. |
| **Publications** | Add publication with DOI validation, add authors with order + corresponding flag, link to one or more projects; list/search/filter |
| **Patents** | Add patent, inventors, link to projects, update status (Granted requires number + date) |
| **Reports** | R1–R10 with filters, charts and CSV download; project report drafts can be edited/resubmitted and Submitted reports reviewed by ADMIN/RESEARCH_OFFICER |
| **Admin** | Create/disable users, assign role, view `audit_log` with filters (ADMIN only) |

### 12.3 Input validation (`validators.py`)
Validate **before** hitting the DB (and the DB still re-checks): required fields; date order; positive money amounts with ≤ 2 decimals; project-code regex `RP-YYYY-NNN`; DOI regex; ORCID regex; email regex; phone regex; effort 1–100; max lengths; strip whitespace; reject empty strings; protect against SQL injection (parameterised queries only) and show clear field-level error messages. Unit-test each validator with valid, invalid and boundary values.

---

## 13. TRANSACTION AWARENESS (`db/09_transaction_demo.sql`, `docs/transactions.md`)

Demonstrate, with real executed output, only against `rpgms_test` or a clearly identified isolated scratch schema:
1. **Atomicity** — call `sp_register_project` with a bad PI id and prove no project or PI assignment remains.
2. **COMMIT / ROLLBACK** — use a controlled test transaction and test-only fixture to insert a disposable row, verify it within the transaction, `ROLLBACK`, and prove it vanished. Do not bypass runtime privileges to insert expenditure in the live `rpgms` schema.
3. **SAVEPOINT** — demonstrate with disposable rows in the test schema; roll back to a savepoint and verify only later test changes were undone.
4. **Isolation / locking** — two sessions call `sp_record_expenditure` concurrently against the same grant/head where only ₹ 50,000 remains; exactly one overspending attempt may succeed. `SELECT ... FOR UPDATE` belongs in the transaction-owning procedure, not the trigger. Automate using two threads/connections in `tests/test_transactions.py`.
5. **Durability / consistency** — explain each ACID letter in plain words with a project example (such as an ATM withdrawal). Never use production sample records for destructive transaction demos.

---

## 14. NORMALISATION (`docs/normalization.md`)

Show a concrete walk-through, not theory:

1. **UNF:** a single wide "Research_Master" sheet like the one research offices actually use — columns for project, PI, department, agency, grant amount, multiple investigators in one cell, multiple publications in one cell, expenditure lines, milestones. Show 5 sample rows.
2. **1NF:** remove repeating groups (one fact per cell, atomic values, a key).
3. **2NF:** remove partial dependencies (e.g., in a table keyed by `(project_id, researcher_id)`, attributes like `project_title` depend only on `project_id` → move out).
4. **3NF:** remove transitive dependencies (e.g., `researcher → dept_id → dept_name`; `grant → agency_id → agency_name/type`; `expenditure → head_id → head_name`).
5. For **every final table**, list its functional dependencies and state "determinant is a candidate key ⇒ in 3NF/BCNF".
6. Explain why **total_spent, balance, % complete** are not stored (derived data would create update anomalies) and show the view that computes them instead.
7. Show an insertion / update / deletion anomaly from the unnormalised sheet and how the final design prevents it. Include Mermaid diagrams for the before/after.

---

## 15. TESTING (`tests/` + `docs/test_report.md`)

Use `pytest` against a **separate** database `rpgms_test`, rebuilt through `python db/setup_db.py --database rpgms_test --reset --seed --confirm-reset rpgms_test` by `conftest.py`. Use `DB_TEST_USER` only for direct CHECK/UNIQUE/FK tests and fixture preparation inside `rpgms_test`; test procedure-enforced business rules and all Flask routes through the restricted runtime `DB_USER` pointed at `rpgms_test`. The schema SQL files contain no `DROP DATABASE`, `CREATE DATABASE` or `USE` statements; the setup script chooses the allowlisted target. Tests must refuse any database name outside `rpgms` and `rpgms_test`, and must never reset `rpgms` as a side effect.

**Must cover**
- every NOT NULL, UNIQUE, CHECK and FK (including composite FK and `ON DELETE RESTRICT/CASCADE` behaviour) — valid and invalid cases; for each DEFAULT, verify the correct value is applied when the column is omitted (a DEFAULT is not itself a rejection constraint),
- every business rule BR-01…BR-18 — positive and negative. Assert the `BR-xx` prefix for custom trigger/procedure errors; for native CHECK/UNIQUE/FK failures, assert the expected constraint/error mapping and friendly normalized BR message instead of expecting the native MySQL text to contain `BR-xx`,
- the 40 queries and 10 reports execute without error; spot-check aggregates (e.g., agency totals equal the sum of grants),
- every view returns rows and the arithmetic is right (spent + balance = grant amount); aggregate-view and report totals are checked against independent source-table totals to detect join fan-out,
- stored-procedure atomicity and rollback, plus the **concurrent overspend test**; confirm every route reaches its documented procedure and no stored-procedure call is wrapped in a second transaction,
- validators (valid / invalid / boundary),
- role permissions (`VIEWER` cannot write; Viewer-safe report queries, charts and CSV never expose row-level identifiers/personal data; `PI` cannot see other PIs' projects); prevent disabling/demoting the last active ADMIN. Add explicit tests for Viewer redaction on R1–R10 and CSV/chart payloads.

`docs/test_report.md` must be a table: `Test ID | Area | Description | Input | Expected | Actual | Pass/Fail` filled with **real results** from running pytest (include the final pytest summary line). Also include a manual UI test checklist (login, register project, assign investigator, add grant, add milestone, record expenditure that succeeds, record expenditure that is blocked, link publication, run each report) with results.

---

## 16. DOCUMENTATION REQUIREMENTS

- **`requirements_analysis.md`** — problem statement, stakeholders, functional/non-functional requirements, entity list with attributes, user roles, assumptions.
- **`er_model.md`** — Mermaid `erDiagram` containing all 19 entities with PK/FK and cardinalities, plus a short plain-language tour of the diagram.
- **`relational_schema.md`** — each table written as `TABLE(pk, attr, ..., fk→OTHER)`, ER-to-relational mapping rules used (1:N → FK on the many side; M:N → associative table; attributes on relationships move to the associative table), and a Mermaid schema diagram.
- **`business_rules.md`** — Section 5 table extended with the test IDs.
- **`user_guide.md`** — one section per role with screenshots descriptions or steps.
- **`viva_prep.md`** — 30 questions (e.g., "Why composite FK on expenditure?", "Why is `grant_award` not called `grant`?", "Why a transaction-owning stored procedure with row locks instead of a CHECK or aggregate trigger for BR-06?", "What is 3NF and where did you apply it?", "What happens if two users overspend simultaneously?") with short, plain-language answers.
- **`README.md`** — prerequisites, a Mac-local quick start: start the already-installed MySQL service using the method that matches its installation; connect with the local MySQL administrator and create only `rpgms` and `rpgms_test` as `utf8mb4` schemas; create a virtual environment; install pinned `requirements.txt`; copy `.env.example` to `.env` and set credentials; run `python db/setup_db.py --database rpgms --reset --seed --confirm-reset rpgms`; then run `python run.py`. For tests, use only `python db/setup_db.py --database rpgms_test --reset --seed --confirm-reset rpgms_test` and `pytest -v`. `--reset` must never issue `DROP DATABASE`; document the target-matching `--confirm-reset` flag in every setup/test command. Include demo logins, re-seeding instructions and troubleshooting. Never point a destructive test reset at `rpgms`.

---

## 17. EXECUTION PLAN WITH GATES

**Phase 1 — Analysis & design docs.** Write `requirements_analysis.md`, `er_model.md`, `relational_schema.md`.
*Gate:* Mermaid diagrams render without syntax errors; all 19 entities present.

**Phase 2 — Database core.** Write and run `01_schema.sql`, `02_triggers.sql`, `03_procedures.sql`, `05_indexes.sql`; write `setup_db.py`.
*Gate:* the explicitly selected existing schema resets with zero errors; `SHOW TABLES` returns 19 tables; `SHOW TRIGGERS` lists all defensive/rule triggers. The script must accept only `rpgms` or `rpgms_test`, must never issue `DROP DATABASE`, and must not touch the other schema.

**Phase 3 — Data.** Write `04_views.sql`, `06_seed.sql`.
*Gate:* seed loads clean (no trigger violations); row counts meet Section 11 minimums; every view returns rows; edge cases from Section 11 are verifiable by query. Seed/test setup runs only against the explicitly selected database.

**Phase 4 — Queries & reports.** Write `07_queries.sql`, `08_reports.sql`, `09_transaction_demo.sql`.
*Gate:* every numbered query runs and returns sensible output; outputs pasted into docs.

**Phase 5 — Normalisation, indexing, transactions docs.** Write `normalization.md`, `indexing.md` (with real EXPLAIN output), `transactions.md`, `business_rules.md`.
*Gate:* EXPLAIN evidence shows a real before/after difference for ≥ 4 queries.

**Phase 6 — Application.** Build `app/`.
*Gate:* `python run.py` starts; log in as each role; complete one full flow (register project → assign investigator → add grant + budget → add milestone → record expenditure → link publication → open every report).

**Phase 7 — Testing.** Write all tests; run `pytest -v`; fill `test_report.md` and complete the manual checklist.
*Gate:* all tests pass; any failure is fixed in the code (never by weakening the test).

**Phase 8 — Polish.** Finish `user_guide.md`, `viva_prep.md` and `README.md`; perform a clean-clone dry run against `rpgms_test`, resetting objects only inside that selected schema, then follow the README from scratch and confirm it works. Never drop the database schema or run destructive verification against `rpgms`.
*Gate:* README steps work on a fresh environment and leave `rpgms` untouched.

---

## 18. FINAL ACCEPTANCE CHECKLIST (agent must tick each with evidence)

- [ ] 19 tables created; all PK/FK/UNIQUE/NOT NULL/CHECK/DEFAULT requirements present and tested; destructive setup targets are allowlisted
- [ ] ER diagram → relational schema → 3NF documented with functional dependencies
- [ ] BR-01…BR-18 enforced in the database, each with a passing positive and negative test
- [ ] Seed data loads clean and includes every edge case in Section 11
- [ ] 40 queries (joins, aggregates, nested, window/CTE) and 10 reports run correctly
- [ ] 9 views created and tested
- [ ] Indexes created; EXPLAIN before/after evidence for ≥ 4 queries
- [ ] Transaction demos run; concurrent overspend test passes
- [ ] Flask/Jinja2 app covers: project registration, investigator assignment, grant & budget entry, milestone tracking, expenditure, publication linkage, reporting
- [ ] Role-based access works for all 4 roles, including Viewer-safe report aggregation and CSV redaction
- [ ] Runtime database account cannot bypass protected project/team, grant/allocation or expenditure procedures
- [ ] Input validation present in the app, with unit tests
- [ ] `pytest` fully green; `test_report.md` contains real results
- [ ] README works from a clean clone
- [ ] All docs complete, plain-language, with diagrams

When everything is done, print a short summary: what was built, how to run it, demo logins, and anything the user must decide or install manually.
