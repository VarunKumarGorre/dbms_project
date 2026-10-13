"""
RPGMS Projects Service
File: app/services/projects.py
Author: Antigravity AI

Handles project queries, details, aggregations, and procedure calls.
Enforces strict role scoping for PI and ADMIN/RESEARCH_OFFICER.
"""

import io
import csv
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from app.db import run_query, call_procedure, run_transaction
from app.auth import get_pi_project_ids, can_access_project

ALLOWED_SORT_COLS = {
    "code": "p.project_code",
    "title": "p.title",
    "status": "p.status",
    "period": "p.start_date",
    "start_date": "p.start_date",
    "funding": "total_funding",
    "spent": "total_spent",
}

def get_projects_list(
    filters: Dict[str, Any],
    role: str,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
    sort_key: str = "code",
    sort_dir: str = "asc"
) -> Dict[str, Any]:
    """Retrieves paginated, filtered, role-scoped list of projects."""
    is_pi = (role == "PI")
    pi_proj_ids = list(get_pi_project_ids(user_id)) if is_pi else []

    if is_pi and not pi_proj_ids:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0
        }

    where_clauses = []
    params: List[Any] = []

    if is_pi:
        placeholders = ",".join(["%s"] * len(pi_proj_ids))
        where_clauses.append(f"p.project_id IN ({placeholders})")
        params.extend(pi_proj_ids)

    q = filters.get("q", "").strip()
    if q:
        where_clauses.append("(p.project_code LIKE %s OR p.title LIKE %s OR p.abstract LIKE %s)")
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard, wildcard])

    dept_id = filters.get("dept_id")
    if dept_id:
        try:
            where_clauses.append("p.dept_id = %s")
            params.append(int(dept_id))
        except ValueError:
            pass

    status = filters.get("status")
    if status and status != "All":
        where_clauses.append("p.status = %s")
        params.append(status)

    year = filters.get("year")
    if year:
        try:
            where_clauses.append("YEAR(p.start_date) = %s")
            params.append(int(year))
        except ValueError:
            pass

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Sort column validation
    sort_col = ALLOWED_SORT_COLS.get(sort_key.lower(), "p.project_code")
    direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"

    # Count total
    count_sql = f"""
    SELECT COUNT(*) AS total
    FROM project AS p
    {where_sql};
    """
    count_row = run_query(count_sql, params, fetchone=True)
    total_count = count_row["total"] if count_row else 0
    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

    # Offset & limit
    offset = max(0, (page - 1) * page_size)

    # Data query joining funding, spend, PI, and milestones
    data_sql = f"""
    SELECT
      p.project_id,
      p.project_code,
      p.title,
      p.status,
      p.start_date,
      p.end_date,
      d.dept_name,
      d.dept_code,
      CONCAT(r_pi.first_name, ' ', r_pi.last_name) AS pi_name,
      r_pi.researcher_id AS pi_id,
      COALESCE(g_agg.total_funding, 0.00) AS total_funding,
      COALESCE(e_agg.total_spent, 0.00) AS total_spent,
      COALESCE(m_agg.milestones_done, 0) AS milestones_done,
      COALESCE(m_agg.milestones_total, 0) AS milestones_total,
      COALESCE(m_agg.overdue_count, 0) AS overdue_count
    FROM project AS p
    JOIN department AS d ON d.dept_id = p.dept_id
    LEFT JOIN (
      SELECT pi.project_id, r.researcher_id, r.first_name, r.last_name
      FROM project_investigator AS pi
      JOIN researcher AS r ON r.researcher_id = pi.researcher_id
      WHERE pi.role = 'PI'
    ) AS r_pi ON r_pi.project_id = p.project_id
    LEFT JOIN (
      SELECT project_id, SUM(grant_amount) AS total_funding
      FROM grant_award
      GROUP BY project_id
    ) AS g_agg ON g_agg.project_id = p.project_id
    LEFT JOIN (
      SELECT ga.project_id, SUM(exp.amount) AS total_spent
      FROM grant_award AS ga
      JOIN expenditure AS exp ON exp.grant_id = ga.grant_id
      GROUP BY ga.project_id
    ) AS e_agg ON e_agg.project_id = p.project_id
    LEFT JOIN (
      SELECT
        project_id,
        COUNT(*) AS milestones_total,
        SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS milestones_done,
        SUM(CASE WHEN status IN ('Pending','In Progress','Delayed') AND due_date < CURDATE() THEN 1 ELSE 0 END) AS overdue_count
      FROM milestone
      GROUP BY project_id
    ) AS m_agg ON m_agg.project_id = p.project_id
    {where_sql}
    ORDER BY {sort_col} {direction}
    LIMIT %s OFFSET %s;
    """
    query_params = list(params) + [page_size, offset]
    rows = run_query(data_sql, query_params)

    items = []
    today = date.today()
    for row in rows:
        funding = float(row["total_funding"] or 0.0)
        spent = float(row["total_spent"] or 0.0)
        spent_pct = round((spent / funding * 100), 1) if funding > 0 else 0.0

        # Time elapsed %
        start = row["start_date"]
        end = row["end_date"]
        if start and end and end > start:
            total_days = (end - start).days
            elapsed_days = (today - start).days
            time_pct = max(0.0, min(100.0, round(elapsed_days / total_days * 100, 1)))
        else:
            time_pct = 0.0

        items.append({
            "project_id": row["project_id"],
            "project_code": row["project_code"],
            "title": row["title"],
            "status": row["status"],
            "dept_name": row["dept_name"],
            "dept_code": row["dept_code"],
            "pi_name": row["pi_name"] or "Unassigned",
            "pi_id": row["pi_id"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "total_funding": funding,
            "total_spent": spent,
            "spent_pct": spent_pct,
            "time_pct": time_pct,
            "milestones_done": row["milestones_done"],
            "milestones_total": row["milestones_total"],
            "overdue_count": row["overdue_count"]
        })

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

def export_projects_csv(filters: Dict[str, Any], role: str, user_id: int) -> str:
    """Exports filtered projects as a CSV string."""
    result = get_projects_list(filters, role, user_id, page=1, page_size=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Project Code", "Title", "Department", "PI", "Status",
        "Start Date", "End Date", "Total Funding (INR)", "Total Spent (INR)",
        "Budget Used %", "Milestones Done", "Milestones Total", "Overdue Milestones"
    ])
    for item in result["items"]:
        writer.writerow([
            item["project_code"],
            item["title"],
            item["dept_name"],
            item["pi_name"],
            item["status"],
            item["start_date"],
            item["end_date"],
            f"{item['total_funding']:.2f}",
            f"{item['total_spent']:.2f}",
            f"{item['spent_pct']:.1f}%",
            item["milestones_done"],
            item["milestones_total"],
            item["overdue_count"]
        ])
    return output.getvalue()

def get_project_detail(project_id: int, role: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves complete project detail view including all tabs and health indicators."""
    is_pi = (role == "PI")
    if is_pi:
        allowed = get_pi_project_ids(user_id)
        if project_id not in allowed:
            return None

    # Base project info
    sql_base = """
    SELECT
      p.project_id, p.project_code, p.title, p.abstract, p.dept_id,
      p.start_date, p.end_date, p.status, p.created_at,
      d.dept_name, d.dept_code
    FROM project AS p
    JOIN department AS d ON d.dept_id = p.dept_id
    WHERE p.project_id = %s;
    """
    proj = run_query(sql_base, (project_id,), fetchone=True)
    if not proj:
        return None

    today = date.today()
    start = proj["start_date"]
    end = proj["end_date"]
    if start and end and end > start:
        total_days = (end - start).days
        elapsed_days = (today - start).days
        time_pct = max(0.0, min(100.0, round(elapsed_days / total_days * 100, 1)))
        days_left = max(0, (end - today).days)
        months_left = max(0, round(days_left / 30.4))
    else:
        time_pct = 0.0
        days_left = 0
        months_left = 0

    # Team members
    sql_team = """
    SELECT
      pi.researcher_id, pi.role, pi.effort_percent, pi.assigned_date,
      CONCAT(r.first_name, ' ', r.last_name) AS name,
      r.email, r.designation, r.orcid_id AS orcid, r.is_active,
      d.dept_name
    FROM project_investigator AS pi
    JOIN researcher AS r ON r.researcher_id = pi.researcher_id
    JOIN department AS d ON d.dept_id = r.dept_id
    WHERE pi.project_id = %s
    ORDER BY (pi.role = 'PI') DESC, pi.effort_percent DESC, r.last_name ASC;
    """
    team = run_query(sql_team, (project_id,))
    pi_member = next((m for m in team if m["role"] == "PI"), None)

    # Grants with budget heads & allocations
    sql_grants = """
    SELECT
      ga.grant_id, ga.grant_number, ga.agency_id, ga.grant_amount,
      ga.sanction_date, ga.grant_start, ga.grant_end, ga.status,
      fa.agency_name, fa.agency_name AS agency_code,
      COALESCE(SUM(exp.amount), 0.00) AS spent_amount
    FROM grant_award AS ga
    JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
    LEFT JOIN expenditure AS exp ON exp.grant_id = ga.grant_id
    WHERE ga.project_id = %s
    GROUP BY ga.grant_id, ga.grant_number, ga.agency_id, ga.grant_amount,
             ga.sanction_date, ga.grant_start, ga.grant_end, ga.status,
             fa.agency_name
    ORDER BY ga.grant_start DESC;
    """
    grants_raw = run_query(sql_grants, (project_id,))

    # For each grant, fetch budget allocations and head expenditures
    grants = []
    total_grant_funding = 0.0
    total_grant_spent = 0.0
    for g in grants_raw:
        g_amount = float(g["grant_amount"])
        g_spent = float(g["spent_amount"])
        total_grant_funding += g_amount
        total_grant_spent += g_spent
        g_bal = max(0.0, g_amount - g_spent)
        g_pct = round(g_spent / g_amount * 100, 1) if g_amount > 0 else 0.0

        sql_allocs = """
        SELECT
          gba.head_id, bh.head_name, gba.allocated_amount,
          COALESCE(SUM(exp.amount), 0.00) AS spent_amount
        FROM grant_budget_allocation AS gba
        JOIN budget_head AS bh ON bh.head_id = gba.head_id
        LEFT JOIN expenditure AS exp ON exp.grant_id = gba.grant_id AND exp.head_id = gba.head_id
        WHERE gba.grant_id = %s
        GROUP BY gba.head_id, bh.head_name, gba.allocated_amount
        ORDER BY gba.allocated_amount DESC;
        """
        allocs_raw = run_query(sql_allocs, (g["grant_id"],))
        allocations = []
        for a in allocs_raw:
            a_alloc = float(a["allocated_amount"])
            a_spent = float(a["spent_amount"])
            a_rem = max(0.0, a_alloc - a_spent)
            a_pct = round(a_spent / a_alloc * 100, 1) if a_alloc > 0 else 0.0
            allocations.append({
                "head_id": a["head_id"],
                "head_name": a["head_name"],
                "allocated": a_alloc,
                "spent": a_spent,
                "remaining": a_rem,
                "spent_pct": a_pct
            })

        grants.append({
            "grant_id": g["grant_id"],
            "grant_number": g["grant_number"],
            "agency_id": g["agency_id"],
            "agency_name": g["agency_name"],
            "agency_code": g["agency_code"],
            "amount": g_amount,
            "spent": g_spent,
            "balance": g_bal,
            "spent_pct": g_pct,
            "sanction_date": g["sanction_date"],
            "grant_start": g["grant_start"],
            "grant_end": g["grant_end"],
            "status": g["status"],
            "allocations": allocations
        })

    # Milestones
    sql_ms = """
    SELECT
      milestone_id, title, description, due_date, completed_date, status,
      DATEDIFF(CURDATE(), due_date) AS days_late
    FROM milestone
    WHERE project_id = %s
    ORDER BY due_date ASC;
    """
    ms_raw = run_query(sql_ms, (project_id,))
    milestones = []
    ms_done = 0
    ms_overdue = 0
    next_due_ms = None
    for m in ms_raw:
        is_done = (m["status"] == "Completed")
        is_delayed = (not is_done and m["due_date"] < today)
        if is_done:
            ms_done += 1
        elif is_delayed:
            ms_overdue += 1

        if not is_done and (next_due_ms is None or m["due_date"] < next_due_ms["due_date"]):
            next_due_ms = m

        milestones.append({
            "milestone_id": m["milestone_id"],
            "title": m["title"],
            "description": m["description"],
            "due_date": m["due_date"],
            "completed_date": m["completed_date"],
            "status": m["status"],
            "is_overdue": is_delayed,
            "days_late": max(0, m["days_late"] or 0)
        })

    # Recent expenditures (up to 25)
    sql_exp = """
    SELECT
      exp.expenditure_id, exp.expense_date, exp.voucher_no,
      bh.head_name, exp.description, exp.amount,
      ga.grant_number, u.username AS recorded_by
    FROM expenditure AS exp
    JOIN grant_award AS ga ON ga.grant_id = exp.grant_id
    JOIN budget_head AS bh ON bh.head_id = exp.head_id
    LEFT JOIN user_account AS u ON u.user_id = exp.recorded_by
    WHERE ga.project_id = %s
    ORDER BY exp.expense_date DESC, exp.expenditure_id DESC
    LIMIT 25;
    """
    expenditures = run_query(sql_exp, (project_id,))

    # Monthly expenditure sparkline series (last 12 months)
    sql_spark = """
    SELECT DATE_FORMAT(exp.expense_date, '%%Y-%%m') AS yyyymm, SUM(exp.amount) AS total
    FROM expenditure AS exp
    JOIN grant_award AS ga ON ga.grant_id = exp.grant_id
    WHERE ga.project_id = %s
    GROUP BY yyyymm
    ORDER BY yyyymm ASC;
    """
    sparkline_data = run_query(sql_spark, (project_id,))

    # Publications
    sql_pubs = """
    SELECT
      p.publication_id, p.title, p.pub_type AS publication_type, p.venue,
      p.pub_date AS publication_date, p.doi, p.indexing
    FROM project_publication AS pp
    JOIN publication AS p ON p.publication_id = pp.publication_id
    WHERE pp.project_id = %s
    ORDER BY p.pub_date DESC;
    """
    pubs_raw = run_query(sql_pubs, (project_id,))
    publications = []
    for pub in pubs_raw:
        sql_authors = """
        SELECT CONCAT(r.first_name, ' ', r.last_name) AS name, pa.is_corresponding, pa.author_order
        FROM publication_author AS pa
        JOIN researcher AS r ON r.researcher_id = pa.researcher_id
        WHERE pa.publication_id = %s
        ORDER BY pa.author_order ASC;
        """
        authors = run_query(sql_authors, (pub["publication_id"],))
        publications.append({
            "publication_id": pub["publication_id"],
            "title": pub["title"],
            "publication_type": pub["publication_type"],
            "venue": pub["venue"],
            "publication_date": pub["publication_date"],
            "doi": pub["doi"],
            "indexing": pub["indexing"],
            "authors": authors
        })

    # Patents
    sql_pats = """
    SELECT
      pat.patent_id, pat.title, pat.application_number, pat.patent_number,
      pat.jurisdiction, pat.filing_date, pat.grant_date, pat.status
    FROM project_patent AS pp
    JOIN patent AS pat ON pat.patent_id = pp.patent_id
    WHERE pp.project_id = %s
    ORDER BY pat.filing_date DESC;
    """
    pats_raw = run_query(sql_pats, (project_id,))
    patents = []
    for pat in pats_raw:
        sql_invs = """
        SELECT CONCAT(r.first_name, ' ', r.last_name) AS name
        FROM patent_inventor AS pi
        JOIN researcher AS r ON r.researcher_id = pi.researcher_id
        WHERE pi.patent_id = %s;
        """
        inventors = run_query(sql_invs, (pat["patent_id"],))
        patents.append({
            "patent_id": pat["patent_id"],
            "title": pat["title"],
            "application_number": pat["application_number"],
            "patent_number": pat["patent_number"],
            "jurisdiction": pat["jurisdiction"],
            "filing_date": pat["filing_date"],
            "grant_date": pat["grant_date"],
            "status": pat["status"],
            "inventors": inventors
        })

    # Reports
    sql_rep = """
    SELECT
      rep.report_id, rep.report_type, rep.period_start, rep.period_end,
      rep.submitted_on, rep.status, rep.summary,
      u.username AS submitted_by_name, rep.submitted_by
    FROM report AS rep
    LEFT JOIN user_account AS u ON u.user_id = rep.submitted_by
    WHERE rep.project_id = %s
    ORDER BY rep.period_end DESC, rep.report_id DESC;
    """
    reports = run_query(sql_rep, (project_id,))

    # Health evaluation & RAG logic (from R1)
    tot_spent_pct = round(total_grant_spent / total_grant_funding * 100, 1) if total_grant_funding > 0 else 0.0
    ms_total = len(milestones)
    ms_pct = round(ms_done / ms_total * 100, 1) if ms_total > 0 else 0.0

    # RAG rule
    if ms_overdue > 1 or (tot_spent_pct > 90 and ms_pct < 60):
        rag = "Red"
    elif ms_overdue == 1 or abs(tot_spent_pct - ms_pct) > 25:
        rag = "Amber"
    else:
        rag = "Green"

    # Health plain language sentences
    health_notes = []
    if total_grant_funding > 0:
        if tot_spent_pct > time_pct:
            diff = round(tot_spent_pct - time_pct, 1)
            health_notes.append(f"Spending is running ahead of elapsed time by {diff}% points.")
        else:
            diff = round(time_pct - tot_spent_pct, 1)
            health_notes.append(f"Spending is trailing behind elapsed time by {diff}% points.")
    else:
        health_notes.append("No grants have been sanctioned for this project yet.")

    if ms_overdue > 0:
        health_notes.append(f"{ms_overdue} milestone(s) are overdue and require immediate review.")
    elif ms_total > 0 and ms_done == ms_total:
        health_notes.append("All scheduled project milestones have been successfully completed.")
    else:
        health_notes.append(f"{ms_done} of {ms_total} milestones completed on schedule.")

    if days_left > 0:
        health_notes.append(f"{days_left} calendar days ({months_left} months) remaining until project completion.")
    else:
        health_notes.append("Project timeline has ended.")

    return {
        "project": proj,
        "pi": pi_member,
        "team": team,
        "grants": grants,
        "milestones": milestones,
        "expenditures": expenditures,
        "sparkline_data": sparkline_data,
        "publications": publications,
        "patents": patents,
        "reports": reports,
        "metrics": {
            "total_funding": total_grant_funding,
            "total_spent": total_grant_spent,
            "spent_pct": tot_spent_pct,
            "time_pct": time_pct,
            "days_left": days_left,
            "months_left": months_left,
            "ms_done": ms_done,
            "ms_total": ms_total,
            "ms_overdue": ms_overdue,
            "rag": rag,
            "health_notes": health_notes,
            "next_due_milestone": next_due_ms
        }
    }

def register_project(
    code: str,
    title: str,
    abstract: str,
    dept_id: int,
    start_date: str,
    end_date: str,
    pi_res_id: int,
    pi_effort: float
) -> int:
    """Executes sp_register_project transaction-owning stored procedure."""
    out_params, _ = call_procedure(
        "sp_register_project",
        (code.strip(), title.strip(), abstract.strip() if abstract else None,
         dept_id, start_date, end_date, pi_res_id, pi_effort, None)
    )
    # out_params: (code, title, abstract, dept_id, start, end, pi_res_id, pi_effort, p_project_id)
    return out_params[8]

def update_project_status(project_id: int, new_status: str):
    """Executes sp_update_project_status or sp_close_project depending on target status."""
    if new_status in ("Completed", "Cancelled"):
        call_procedure("sp_close_project", (project_id, new_status))
    else:
        call_procedure("sp_update_project_status", (project_id, new_status))

def assign_investigator(project_id: int, researcher_id: int, role: str, effort_percent: float):
    """Assigns team member via sp_assign_investigator."""
    call_procedure("sp_assign_investigator", (project_id, researcher_id, role, effort_percent))

def remove_investigator(project_id: int, researcher_id: int):
    """Removes non-PI team member via sp_remove_investigator."""
    call_procedure("sp_remove_investigator", (project_id, researcher_id))

def change_project_pi(project_id: int, new_res_id: int, new_effort: float):
    """Transfers PI leadership via sp_change_project_pi."""
    call_procedure("sp_change_project_pi", (project_id, new_res_id, new_effort))

def link_publication_to_project(project_id: int, publication_id: int):
    """Links an existing publication to project."""
    with run_transaction() as cursor:
        cursor.execute(
            "INSERT INTO project_publication (project_id, publication_id) VALUES (%s, %s);",
            (project_id, publication_id)
        )

def link_patent_to_project(project_id: int, patent_id: int):
    """Links an existing patent to project."""
    with run_transaction() as cursor:
        cursor.execute(
            "INSERT INTO project_patent (project_id, patent_id) VALUES (%s, %s);",
            (project_id, patent_id)
        )

def create_project_report(
    project_id: int,
    report_type: str,
    period_start: str,
    period_end: str,
    summary: str,
    is_submit: bool,
    user_id: int
) -> int:
    """Creates a draft or submitted project report record."""
    status = "Submitted" if is_submit else "Draft"
    sub_date = date.today().isoformat() if is_submit else None
    sub_by = user_id if is_submit else None

    with run_transaction() as cursor:
        cursor.execute("""
            INSERT INTO report (
              project_id, report_type, period_start, period_end,
              submitted_on, submitted_by, summary, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (project_id, report_type, period_start, period_end, sub_date, sub_by, summary, status))
        cursor.execute("SELECT LAST_INSERT_ID() AS id;")
        row = cursor.fetchone()
        return row["id"]

def update_project_report(
    report_id: int,
    project_id: int,
    report_type: str,
    period_start: str,
    period_end: str,
    summary: str,
    is_submit: bool,
    user_id: int
):
    """Updates a draft or returned project report."""
    status = "Submitted" if is_submit else "Draft"
    sub_date = date.today().isoformat() if is_submit else None
    sub_by = user_id if is_submit else None

    with run_transaction() as cursor:
        cursor.execute("""
            UPDATE report
            SET report_type = %s,
                period_start = %s,
                period_end = %s,
                summary = %s,
                status = %s,
                submitted_on = %s,
                submitted_by = %s
            WHERE report_id = %s AND project_id = %s AND status IN ('Draft', 'Returned');
        """, (report_type, period_start, period_end, summary, status, sub_date, sub_by, report_id, project_id))

def review_project_report(report_id: int, project_id: int, new_status: str, user_id: int):
    """Reviews a submitted report (Accept or Return)."""
    if new_status not in ("Accepted", "Returned"):
        raise ValueError("Invalid report review status")

    with run_transaction() as cursor:
        cursor.execute("""
            UPDATE report
            SET status = %s
            WHERE report_id = %s AND project_id = %s AND status = 'Submitted';
        """, (new_status, report_id, project_id))
