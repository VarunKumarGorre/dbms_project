"""
RPGMS Analytical Reports Service (R1 - R10)
File: app/services/reports.py
Author: Antigravity AI

Defines report definitions, operational queries, Viewer-safe redacted queries,
summary KPI tiles, Chart.js payload generators, and CSV exporters.
Enforces role-based isolation:
- ADMIN / RESEARCH_OFFICER: Full operational queries with record-level granularity.
- PI: Operational queries strictly scoped to own projects; cross-project data excluded.
- VIEWER: Sanitized aggregate queries omitting individual codes, titles, names, vouchers, DOIs.
"""

import io
import csv
from typing import Any, Dict, List, Optional
from app.db import run_query
from app.auth import get_pi_project_ids

REPORTS_META = {
    "R1": {
        "code": "R1",
        "title": "Project Progress",
        "description": "Progress tracking, milestone completion rates, schedule elapsed time, and RAG health indicators.",
        "chart_type": "horizontalBar",
        "filter_fields": ["status", "dept_id"]
    },
    "R2": {
        "code": "R2",
        "title": "Budget Utilization",
        "description": "Comprehensive grant financial position, sanctioned amounts, total spending, balances, and utilization health classes.",
        "chart_type": "stackedHorizontalBar",
        "filter_fields": ["agency_id", "health"]
    },
    "R3": {
        "code": "R3",
        "title": "Milestone Tracker",
        "description": "Monthly milestone delivery timeline, completion ratios, and overdue task monitoring.",
        "chart_type": "bar",
        "filter_fields": ["status", "dept_id"]
    },
    "R4": {
        "code": "R4",
        "title": "Researcher Output",
        "description": "Scholarly publications and patent filings per researcher and active workload percentages.",
        "chart_type": "groupedBar",
        "filter_fields": ["dept_id"]
    },
    "R5": {
        "code": "R5",
        "title": "Agency Portfolio",
        "description": "External funding agency contribution shares, active grant counts, and total sanctioned capital.",
        "chart_type": "doughnut",
        "filter_fields": []
    },
    "R6": {
        "code": "R6",
        "title": "Publications by Indexing",
        "description": "Annual publication trends classified across SCIE, Scopus, UGC-CARE, and conference proceedings.",
        "chart_type": "stackedColumn",
        "filter_fields": ["year", "indexing"]
    },
    "R7": {
        "code": "R7",
        "title": "Department Summary",
        "description": "Departmental research capacity: active projects, total sanctioned funding, scholars, and research output.",
        "chart_type": "groupedBar",
        "filter_fields": []
    },
    "R8": {
        "code": "R8",
        "title": "Expenditure Statement",
        "description": "Chronological spending ledger and running balance statement for sanctioned research grants.",
        "chart_type": "line",
        "filter_fields": ["grant_id"]
    },
    "R9": {
        "code": "R9",
        "title": "Patent Status Portfolio",
        "description": "Intellectual property distribution across filing, publication, examination, grant, and maintenance states.",
        "chart_type": "doughnut",
        "filter_fields": ["jurisdiction"]
    },
    "R10": {
        "code": "R10",
        "title": "Project Closing Summary",
        "description": "Financial closure audits for completed and cancelled projects: sanctioned vs utilized funds and unspent balances.",
        "chart_type": "stackedBar",
        "filter_fields": ["dept_id"]
    }
}

def get_reports_hub_data() -> List[Dict[str, Any]]:
    """Returns directory list for the Reports Hub page."""
    return list(REPORTS_META.values())

def generate_report(
    report_code: str,
    filters: Dict[str, Any],
    role: str,
    user_id: int
) -> Optional[Dict[str, Any]]:
    """Generates report table rows, summary tiles, and chart configuration."""
    code = report_code.upper()
    if code not in REPORTS_META:
        return None

    meta = REPORTS_META[code]
    is_viewer = (role == "VIEWER")
    is_pi = (role == "PI")
    pi_proj_ids = list(get_pi_project_ids(user_id)) if is_pi else []

    if code == "R1":
        return _gen_r1(meta, filters, role, is_viewer, is_pi, pi_proj_ids)
    elif code == "R2":
        return _gen_r2(meta, filters, role, is_viewer, is_pi, pi_proj_ids)
    elif code == "R3":
        return _gen_r3(meta, filters, role, is_viewer, is_pi, pi_proj_ids)
    elif code == "R4":
        return _gen_r4(meta, filters, role, is_viewer, is_pi, pi_proj_ids)
    elif code == "R5":
        return _gen_r5(meta, filters, role, is_viewer, is_pi, pi_proj_ids)
    elif code == "R6":
        return _gen_r6(meta, filters, role, is_viewer, is_pi, pi_proj_ids)
    elif code == "R7":
        return _gen_r7(meta, filters, role, is_viewer, is_pi, pi_proj_ids)
    elif code == "R8":
        return _gen_r8(meta, filters, role, is_viewer, is_pi, pi_proj_ids, user_id)
    elif code == "R9":
        return _gen_r9(meta, filters, role, is_viewer, is_pi, pi_proj_ids)
    elif code == "R10":
        return _gen_r10(meta, filters, role, is_viewer, is_pi, pi_proj_ids)

    return None

# ==============================================================================
# Helper generators for R1 - R10
# ==============================================================================

def _gen_r1(meta, filters, role, is_viewer, is_pi, pi_proj_ids):
    if is_viewer:
        # Viewer-safe aggregate by department and status
        sql = """
        SELECT
          d.dept_code, d.dept_name, p.status AS project_status,
          COUNT(p.project_id) AS total_projects,
          SUM(COALESCE(m.total_milestones, 0)) AS total_milestones,
          SUM(COALESCE(m.completed_milestones, 0)) AS completed_milestones,
          SUM(COALESCE(m.overdue_milestones, 0)) AS overdue_milestones,
          ROUND(AVG(
            CASE
              WHEN CURDATE() <= p.start_date THEN 0.00
              WHEN CURDATE() >= p.end_date THEN 100.00
              ELSE ROUND((DATEDIFF(CURDATE(), p.start_date) / DATEDIFF(p.end_date, p.start_date)) * 100, 2)
            END
          ), 2) AS avg_time_elapsed_pct
        FROM project AS p
        JOIN department AS d ON d.dept_id = p.dept_id
        LEFT JOIN (
          SELECT project_id,
                 COUNT(*) AS total_milestones,
                 SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_milestones,
                 SUM(CASE WHEN status <> 'Completed' AND due_date < CURDATE() THEN 1 ELSE 0 END) AS overdue_milestones
          FROM milestone
          GROUP BY project_id
        ) AS m ON m.project_id = p.project_id
        GROUP BY d.dept_id, d.dept_code, d.dept_name, p.status
        ORDER BY d.dept_code, p.status;
        """
        rows = run_query(sql)
        cols = [
            {"key": "dept_code", "label": "Dept Code"},
            {"key": "dept_name", "label": "Department"},
            {"key": "project_status", "label": "Status"},
            {"key": "total_projects", "label": "Projects"},
            {"key": "total_milestones", "label": "Milestones"},
            {"key": "completed_milestones", "label": "Completed"},
            {"key": "overdue_milestones", "label": "Overdue"},
            {"key": "avg_time_elapsed_pct", "label": "Avg Time Elapsed %"}
        ]
        tot_proj = sum(r["total_projects"] for r in rows)
        tot_ms = sum(r["total_milestones"] for r in rows)
        tot_overdue = sum(r["overdue_milestones"] for r in rows)
        tiles = [
            {"label": "Total Projects", "value": tot_proj},
            {"label": "Total Milestones", "value": tot_ms},
            {"label": "Overdue Milestones", "value": tot_overdue}
        ]
        chart = {
            "type": "bar",
            "labels": [f"{r['dept_code']} ({r['project_status']})" for r in rows],
            "datasets": [
                {"label": "Completed Milestones", "data": [int(r["completed_milestones"]) for r in rows]},
                {"label": "Overdue Milestones", "data": [int(r["overdue_milestones"]) for r in rows]}
            ]
        }
        return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

    # Operational & PI
    where = []
    params = []
    if is_pi:
        if not pi_proj_ids:
            return {"meta": meta, "columns": [], "rows": [], "tiles": [], "chart": None}
        where.append(f"p.project_id IN ({','.join(['%s']*len(pi_proj_ids))})")
        params.extend(pi_proj_ids)

    if filters.get("status") and filters["status"] != "All":
        where.append("p.status = %s")
        params.append(filters["status"])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
    SELECT
      p.project_id, p.project_code, p.title, d.dept_code, p.status,
      p.start_date, p.end_date,
      CASE
        WHEN CURDATE() <= p.start_date THEN 0.00
        WHEN CURDATE() >= p.end_date THEN 100.00
        ELSE ROUND((DATEDIFF(CURDATE(), p.start_date) / DATEDIFF(p.end_date, p.start_date)) * 100, 2)
      END AS time_elapsed_pct,
      COALESCE(m.total_milestones, 0) AS total_milestones,
      COALESCE(m.completed_milestones, 0) AS completed_milestones,
      COALESCE(m.overdue_milestones, 0) AS overdue_milestones,
      CASE
        WHEN COALESCE(m.total_milestones, 0) > 0
        THEN ROUND((m.completed_milestones / m.total_milestones) * 100, 1)
        ELSE 0.0
      END AS milestone_completion_pct,
      CASE
        WHEN p.status IN ('Completed', 'Cancelled') THEN 'Closed'
        WHEN p.status = 'Proposed' OR CURDATE() < p.start_date THEN 'Not started'
        WHEN COALESCE(m.total_milestones, 0) = 0 THEN 'Not rated'
        WHEN m.overdue_milestones > 1 OR (COALESCE(m.total_milestones, 0) > 0 AND (m.completed_milestones / m.total_milestones * 100) < 60 AND CURDATE() > p.end_date) THEN 'Red'
        WHEN m.overdue_milestones > 0 THEN 'Amber'
        ELSE 'Green'
      END AS rag_status
    FROM project AS p
    JOIN department AS d ON d.dept_id = p.dept_id
    LEFT JOIN (
      SELECT project_id,
             COUNT(*) AS total_milestones,
             SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_milestones,
             SUM(CASE WHEN status <> 'Completed' AND due_date < CURDATE() THEN 1 ELSE 0 END) AS overdue_milestones
      FROM milestone
      GROUP BY project_id
    ) AS m ON m.project_id = p.project_id
    {where_sql}
    ORDER BY p.project_code ASC;
    """
    rows = run_query(sql, params)
    cols = [
        {"key": "project_code", "label": "Project Code"},
        {"key": "title", "label": "Title"},
        {"key": "dept_code", "label": "Dept"},
        {"key": "status", "label": "Status"},
        {"key": "total_milestones", "label": "Milestones"},
        {"key": "completed_milestones", "label": "Completed"},
        {"key": "overdue_milestones", "label": "Overdue"},
        {"key": "milestone_completion_pct", "label": "% Complete"},
        {"key": "time_elapsed_pct", "label": "% Time Elapsed"},
        {"key": "rag_status", "label": "RAG"}
    ]
    tot_proj = len(rows)
    red_cnt = sum(1 for r in rows if r["rag_status"] == "Red")
    amber_cnt = sum(1 for r in rows if r["rag_status"] == "Amber")
    green_cnt = sum(1 for r in rows if r["rag_status"] == "Green")
    tiles = [
        {"label": "Total Projects", "value": tot_proj},
        {"label": "Green Health", "value": green_cnt},
        {"label": "Amber Health", "value": amber_cnt},
        {"label": "Red Health", "value": red_cnt}
    ]
    chart = {
        "type": "horizontalBar",
        "labels": [r["project_code"] for r in rows],
        "datasets": [
            {"label": "Milestone Completion %", "data": [float(r["milestone_completion_pct"] or 0) for r in rows]},
            {"label": "Time Elapsed %", "data": [float(r["time_elapsed_pct"] or 0) for r in rows]}
        ]
    }
    return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

def _gen_r2(meta, filters, role, is_viewer, is_pi, pi_proj_ids):
    if is_viewer:
        sql = """
        SELECT
          fa.agency_id, fa.agency_name,
          COUNT(ga.grant_id) AS total_grants,
          SUM(ga.grant_amount) AS total_sanctioned,
          SUM(COALESCE(e.total_spent, 0.00)) AS total_spent,
          SUM(ga.grant_amount - COALESCE(e.total_spent, 0.00)) AS total_balance,
          ROUND((SUM(COALESCE(e.total_spent, 0.00)) / SUM(ga.grant_amount)) * 100, 2) AS utilization_pct
        FROM grant_award AS ga
        JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
        LEFT JOIN (
          SELECT grant_id, SUM(amount) AS total_spent FROM expenditure GROUP BY grant_id
        ) AS e ON e.grant_id = ga.grant_id
        GROUP BY fa.agency_id, fa.agency_name
        ORDER BY total_sanctioned DESC;
        """
        rows = run_query(sql)
        cols = [
            {"key": "agency_name", "label": "Funding Agency"},
            {"key": "total_grants", "label": "Grants"},
            {"key": "total_sanctioned", "label": "Sanctioned (INR)", "is_money": True},
            {"key": "total_spent", "label": "Spent (INR)", "is_money": True},
            {"key": "total_balance", "label": "Balance (INR)", "is_money": True},
            {"key": "utilization_pct", "label": "Utilization %"}
        ]
        sanc = sum(float(r["total_sanctioned"]) for r in rows)
        spent = sum(float(r["total_spent"]) for r in rows)
        bal = sum(float(r["total_balance"]) for r in rows)
        tiles = [
            {"label": "Total Sanctioned", "value": sanc, "is_money": True},
            {"label": "Total Spent", "value": spent, "is_money": True},
            {"label": "Remaining Balance", "value": bal, "is_money": True}
        ]
        chart = {
            "type": "bar",
            "labels": [r["agency_name"] for r in rows],
            "datasets": [
                {"label": "Spent (INR)", "data": [float(r["total_spent"]) for r in rows]},
                {"label": "Sanctioned (INR)", "data": [float(r["total_sanctioned"]) for r in rows]},
                {"label": "Balance (INR)", "data": [float(r["total_balance"]) for r in rows]}
            ]
        }
        return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

    # Operational / PI
    where = []
    params = []
    if is_pi:
        if not pi_proj_ids:
            return {"meta": meta, "columns": [], "rows": [], "tiles": [], "chart": None}
        where.append(f"ga.project_id IN ({','.join(['%s']*len(pi_proj_ids))})")
        params.extend(pi_proj_ids)

    if filters.get("agency_id"):
        where.append("ga.agency_id = %s")
        params.append(filters["agency_id"])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
    SELECT
      ga.grant_id, ga.grant_number, p.project_code, fa.agency_name,
      ga.grant_amount,
      COALESCE(e.total_spent, 0.00) AS spent_amount,
      (ga.grant_amount - COALESCE(e.total_spent, 0.00)) AS balance_amount,
      ROUND((COALESCE(e.total_spent, 0.00) / ga.grant_amount) * 100, 1) AS utilization_pct,
      ga.status
    FROM grant_award AS ga
    JOIN project AS p ON p.project_id = ga.project_id
    JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
    LEFT JOIN (
      SELECT grant_id, SUM(amount) AS total_spent FROM expenditure GROUP BY grant_id
    ) AS e ON e.grant_id = ga.grant_id
    {where_sql}
    ORDER BY utilization_pct DESC;
    """
    rows = run_query(sql, params)
    for r in rows:
        u = float(r["utilization_pct"] or 0)
        if u >= 100:
            r["health"] = "Exhausted"
        elif u >= 90:
            r["health"] = "Near Limit"
        elif u >= 50:
            r["health"] = "On Track"
        else:
            r["health"] = "Under 50%"

    if filters.get("health") and filters["health"] != "All":
        rows = [r for r in rows if r["health"] == filters["health"]]

    cols = [
        {"key": "grant_number", "label": "Grant Number"},
        {"key": "project_code", "label": "Project"},
        {"key": "agency_name", "label": "Agency"},
        {"key": "grant_amount", "label": "Sanctioned (INR)", "is_money": True},
        {"key": "spent_amount", "label": "Spent (INR)", "is_money": True},
        {"key": "balance_amount", "label": "Balance (INR)", "is_money": True},
        {"key": "utilization_pct", "label": "Used %"},
        {"key": "health", "label": "Health"}
    ]
    sanc = sum(float(r["grant_amount"]) for r in rows)
    spent = sum(float(r["spent_amount"]) for r in rows)
    tiles = [
        {"label": "Total Sanctioned", "value": sanc, "is_money": True},
        {"label": "Total Spent", "value": spent, "is_money": True},
        {"label": "Near Limit / Exhausted", "value": sum(1 for r in rows if r["health"] in ("Near Limit", "Exhausted"))}
    ]
    chart = {
        "type": "horizontalBar",
        "labels": [r["grant_number"] for r in rows[:10]],
        "datasets": [
            {"label": "Spent (INR)", "data": [float(r["spent_amount"]) for r in rows[:10]]},
            {"label": "Balance (INR)", "data": [float(r["balance_amount"]) for r in rows[:10]]}
        ]
    }
    return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

def _gen_r3(meta, filters, role, is_viewer, is_pi, pi_proj_ids):
    if is_viewer:
        sql = """
        SELECT
          DATE_FORMAT(m.due_date, '%Y-%m') AS due_month,
          COUNT(m.milestone_id) AS total_milestones,
          SUM(CASE WHEN m.status = 'Completed' THEN 1 ELSE 0 END) AS completed_milestones,
          SUM(CASE WHEN m.status = 'Delayed' OR (m.status IN ('Pending','In Progress') AND m.due_date < CURDATE()) THEN 1 ELSE 0 END) AS overdue_milestones,
          SUM(CASE WHEN m.status IN ('Pending','In Progress') AND m.due_date >= CURDATE() THEN 1 ELSE 0 END) AS on_track_milestones
        FROM milestone AS m
        GROUP BY due_month
        ORDER BY due_month ASC;
        """
        rows = run_query(sql)
        cols = [
            {"key": "due_month", "label": "Month"},
            {"key": "total_milestones", "label": "Total Due"},
            {"key": "completed_milestones", "label": "Completed"},
            {"key": "on_track_milestones", "label": "On Track"},
            {"key": "overdue_milestones", "label": "Overdue / Delayed"}
        ]
        tot = sum(r["total_milestones"] for r in rows)
        done = sum(r["completed_milestones"] for r in rows)
        over = sum(r["overdue_milestones"] for r in rows)
        tiles = [
            {"label": "Total Milestones", "value": tot},
            {"label": "Completed", "value": done},
            {"label": "Overdue", "value": over}
        ]
        chart = {
            "type": "bar",
            "labels": [r["due_month"] for r in rows],
            "datasets": [
                {"label": "Completed", "data": [int(r["completed_milestones"]) for r in rows]},
                {"label": "On Track", "data": [int(r["on_track_milestones"]) for r in rows]},
                {"label": "Overdue", "data": [int(r["overdue_milestones"]) for r in rows]}
            ]
        }
        return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

    where = []
    params = []
    if is_pi:
        if not pi_proj_ids:
            return {"meta": meta, "columns": [], "rows": [], "tiles": [], "chart": None}
        where.append(f"m.project_id IN ({','.join(['%s']*len(pi_proj_ids))})")
        params.extend(pi_proj_ids)

    if filters.get("status") and filters["status"] != "All":
        where.append("m.status = %s")
        params.append(filters["status"])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
    SELECT
      m.milestone_id, m.title, p.project_code, m.due_date, m.completed_date, m.status,
      DATEDIFF(CURDATE(), m.due_date) AS days_late
    FROM milestone AS m
    JOIN project AS p ON p.project_id = m.project_id
    {where_sql}
    ORDER BY m.due_date ASC;
    """
    rows = run_query(sql, params)
    for r in rows:
        r["is_overdue"] = (r["status"] != "Completed" and r["due_date"] < r["due_date"].today())
        r["days_late"] = max(0, r["days_late"] or 0)

    cols = [
        {"key": "title", "label": "Milestone Title"},
        {"key": "project_code", "label": "Project"},
        {"key": "due_date", "label": "Due Date"},
        {"key": "status", "label": "Status"},
        {"key": "days_late", "label": "Days Late"}
    ]
    tot = len(rows)
    done = sum(1 for r in rows if r["status"] == "Completed")
    over = sum(1 for r in rows if r["is_overdue"])
    tiles = [
        {"label": "Total Milestones", "value": tot},
        {"label": "Completed", "value": done},
        {"label": "Overdue", "value": over}
    ]
    # Monthly status counts for chart
    chart_months = {}
    for r in rows:
        m_str = r["due_date"].strftime("%Y-%m")
        if m_str not in chart_months:
            chart_months[m_str] = {"Completed": 0, "Other": 0}
        if r["status"] == "Completed":
            chart_months[m_str]["Completed"] += 1
        else:
            chart_months[m_str]["Other"] += 1

    sorted_m = sorted(chart_months.keys())
    chart = {
        "type": "bar",
        "labels": sorted_m,
        "datasets": [
            {"label": "Completed", "data": [chart_months[k]["Completed"] for k in sorted_m]},
            {"label": "Pending/Delayed", "data": [chart_months[k]["Other"] for k in sorted_m]}
        ]
    }
    return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

def _gen_r4(meta, filters, role, is_viewer, is_pi, pi_proj_ids):
    if is_viewer:
        # Viewer-safe by department
        sql = """
        SELECT
          d.dept_code, d.dept_name,
          COUNT(DISTINCT r.researcher_id) AS total_researchers,
          COUNT(DISTINCT pa.publication_id) AS total_publications,
          COUNT(DISTINCT p_inv.patent_id) AS total_patents,
          ROUND(AVG(COALESCE(proj_agg.total_effort, 0.00)), 2) AS avg_workload_pct
        FROM department AS d
        JOIN researcher AS r ON r.dept_id = d.dept_id
        LEFT JOIN publication_author AS pa ON pa.researcher_id = r.researcher_id
        LEFT JOIN patent_inventor AS p_inv ON p_inv.researcher_id = r.researcher_id
        LEFT JOIN (
          SELECT pi.researcher_id, SUM(pi.effort_percent) AS total_effort
          FROM project_investigator AS pi
          JOIN project AS p ON p.project_id = pi.project_id
          WHERE p.status IN ('Proposed', 'Active')
          GROUP BY pi.researcher_id
        ) AS proj_agg ON proj_agg.researcher_id = r.researcher_id
        GROUP BY d.dept_id, d.dept_code, d.dept_name
        ORDER BY total_publications DESC;
        """
        rows = run_query(sql)
        cols = [
            {"key": "dept_code", "label": "Dept Code"},
            {"key": "dept_name", "label": "Department"},
            {"key": "total_researchers", "label": "Researchers"},
            {"key": "total_publications", "label": "Publications"},
            {"key": "total_patents", "label": "Patents"},
            {"key": "avg_workload_pct", "label": "Avg Workload %"}
        ]
        tot_pub = sum(r["total_publications"] for r in rows)
        tot_pat = sum(r["total_patents"] for r in rows)
        tiles = [
            {"label": "Total Publications", "value": tot_pub},
            {"label": "Total Patents", "value": tot_pat}
        ]
        chart = {
            "type": "bar",
            "labels": [r["dept_code"] for r in rows],
            "datasets": [
                {"label": "Publications", "data": [int(r["total_publications"]) for r in rows]},
                {"label": "Patents", "data": [int(r["total_patents"]) for r in rows]}
            ]
        }
        return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

    # Operational / PI (PI count only when linked to own project!)
    if is_pi:
        if not pi_proj_ids:
            return {"meta": meta, "columns": [], "rows": [], "tiles": [], "chart": None}
        sql = f"""
        SELECT
          r.researcher_id,
          CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
          d.dept_code, r.designation,
          COUNT(DISTINCT pp.publication_id) AS total_publications,
          COUNT(DISTINCT ppt.patent_id) AS total_patents,
          COALESCE(SUM(pi.effort_percent), 0.0) AS active_workload_pct
        FROM researcher AS r
        JOIN department AS d ON d.dept_id = r.dept_id
        JOIN project_investigator AS pi ON pi.researcher_id = r.researcher_id AND pi.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
        LEFT JOIN publication_author AS pa ON pa.researcher_id = r.researcher_id
        LEFT JOIN project_publication AS pp ON pp.publication_id = pa.publication_id AND pp.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
        LEFT JOIN patent_inventor AS p_inv ON p_inv.researcher_id = r.researcher_id
        LEFT JOIN project_patent AS ppt ON ppt.patent_id = p_inv.patent_id AND ppt.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
        GROUP BY r.researcher_id, r.first_name, r.last_name, d.dept_code, r.designation
        ORDER BY total_publications DESC, total_patents DESC;
        """
        rows = run_query(sql, pi_proj_ids + pi_proj_ids + pi_proj_ids)
    else:
        sql = """
        SELECT
          r.researcher_id,
          CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
          d.dept_code, r.designation,
          COUNT(DISTINCT pa.publication_id) AS total_publications,
          COUNT(DISTINCT p_inv.patent_id) AS total_patents,
          COALESCE(proj_agg.total_effort, 0.00) AS active_workload_pct
        FROM researcher AS r
        JOIN department AS d ON d.dept_id = r.dept_id
        LEFT JOIN publication_author AS pa ON pa.researcher_id = r.researcher_id
        LEFT JOIN patent_inventor AS p_inv ON p_inv.researcher_id = r.researcher_id
        LEFT JOIN (
          SELECT pi.researcher_id, SUM(pi.effort_percent) AS total_effort
          FROM project_investigator AS pi
          JOIN project AS p ON p.project_id = pi.project_id
          WHERE p.status IN ('Proposed', 'Active')
          GROUP BY pi.researcher_id
        ) AS proj_agg ON proj_agg.researcher_id = r.researcher_id
        GROUP BY r.researcher_id, r.first_name, r.last_name, d.dept_code, r.designation, proj_agg.total_effort
        ORDER BY total_publications DESC, total_patents DESC;
        """
        rows = run_query(sql)

    cols = [
        {"key": "researcher_name", "label": "Researcher Name"},
        {"key": "dept_code", "label": "Dept"},
        {"key": "designation", "label": "Designation"},
        {"key": "total_publications", "label": "Publications"},
        {"key": "total_patents", "label": "Patents"},
        {"key": "active_workload_pct", "label": "Workload %"}
    ]
    tot_pubs = sum(r["total_publications"] for r in rows)
    tot_pats = sum(r["total_patents"] for r in rows)
    tiles = [
        {"label": "Total Publications", "value": tot_pubs},
        {"label": "Total Patents", "value": tot_pats},
        {"label": "Researchers Active", "value": len(rows)}
    ]
    top10 = rows[:10]
    chart = {
        "type": "bar",
        "labels": [r["researcher_name"] for r in top10],
        "datasets": [
            {"label": "Publications", "data": [int(r["total_publications"]) for r in top10]},
            {"label": "Patents", "data": [int(r["total_patents"]) for r in top10]}
        ]
    }
    return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

def _gen_r5(meta, filters, role, is_viewer, is_pi, pi_proj_ids):
    # Agency portfolio
    where = []
    params = []
    if is_pi:
        if not pi_proj_ids:
            return {"meta": meta, "columns": [], "rows": [], "tiles": [], "chart": None}
        where.append(f"ga.project_id IN ({','.join(['%s']*len(pi_proj_ids))})")
        params.extend(pi_proj_ids)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
    SELECT
      fa.agency_id, fa.agency_name,
      COUNT(ga.grant_id) AS total_grants,
      COALESCE(SUM(ga.grant_amount), 0.00) AS total_sanctioned,
      COALESCE(SUM(e.total_spent), 0.00) AS total_spent
    FROM funding_agency AS fa
    JOIN grant_award AS ga ON ga.agency_id = fa.agency_id
    LEFT JOIN (
      SELECT grant_id, SUM(amount) AS total_spent FROM expenditure GROUP BY grant_id
    ) AS e ON e.grant_id = ga.grant_id
    {where_sql}
    GROUP BY fa.agency_id, fa.agency_name
    ORDER BY total_sanctioned DESC;
    """
    rows = run_query(sql, params)
    tot_sanc = sum(float(r["total_sanctioned"]) for r in rows)
    for r in rows:
        amt = float(r["total_sanctioned"])
        r["share_pct"] = round(amt / tot_sanc * 100, 1) if tot_sanc > 0 else 0.0

    cols = [
        {"key": "agency_name", "label": "Funding Agency"},
        {"key": "total_grants", "label": "Total Grants"},
        {"key": "total_sanctioned", "label": "Sanctioned (INR)", "is_money": True},
        {"key": "total_spent", "label": "Spent (INR)", "is_money": True},
        {"key": "share_pct", "label": "Portfolio Share %"}
    ]
    tot_gr = sum(r["total_grants"] for r in rows)
    tot_sp = sum(float(r["total_spent"]) for r in rows)
    tiles = [
        {"label": "Total Sanctioned", "value": tot_sanc, "is_money": True},
        {"label": "Total Spent", "value": tot_sp, "is_money": True},
        {"label": "Agencies Represented", "value": len(rows)}
    ]
    chart = {
        "type": "doughnut",
        "labels": [r["agency_name"] for r in rows],
        "datasets": [
            {"label": "Sanctioned Funding", "data": [float(r["total_sanctioned"]) for r in rows]}
        ]
    }
    return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

def _gen_r6(meta, filters, role, is_viewer, is_pi, pi_proj_ids):
    # Publications by indexing
    where = []
    params = []
    if is_pi:
        if not pi_proj_ids:
            return {"meta": meta, "columns": [], "rows": [], "tiles": [], "chart": None}
        where.append(f"pp.project_id IN ({','.join(['%s']*len(pi_proj_ids))})")
        params.extend(pi_proj_ids)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    if is_pi:
        sql = f"""
        SELECT
          YEAR(p.pub_date) AS pub_year,
          p.indexing,
          COUNT(DISTINCT p.publication_id) AS total_count
        FROM publication AS p
        JOIN project_publication AS pp ON pp.publication_id = p.publication_id
        {where_sql}
        GROUP BY pub_year, p.indexing
        ORDER BY pub_year DESC, p.indexing ASC;
        """
    else:
        sql = """
        SELECT
          YEAR(p.pub_date) AS pub_year,
          p.indexing,
          COUNT(*) AS total_count
        FROM publication AS p
        GROUP BY pub_year, p.indexing
        ORDER BY pub_year DESC, p.indexing ASC;
        """
    rows = run_query(sql, params)
    cols = [
        {"key": "pub_year", "label": "Year"},
        {"key": "indexing", "label": "Indexing"},
        {"key": "total_count", "label": "Publication Count"}
    ]
    tot = sum(r["total_count"] for r in rows)
    tiles = [
        {"label": "Total Publications", "value": tot},
        {"label": "Indexing Categories", "value": len(set(r["indexing"] for r in rows))}
    ]
    years = sorted(list(set(r["pub_year"] for r in rows)))
    indexings = ["SCIE", "Scopus", "UGC-CARE", "Other"]
    datasets = []
    for idx in indexings:
        data = []
        for y in years:
            match = next((r["total_count"] for r in rows if r["pub_year"] == y and r["indexing"] == idx), 0)
            data.append(match)
        datasets.append({"label": idx, "data": data})

    chart = {
        "type": "bar",
        "labels": years,
        "datasets": datasets
    }
    return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

def _gen_r7(meta, filters, role, is_viewer, is_pi, pi_proj_ids):
    # Department summary
    if is_pi:
        if not pi_proj_ids:
            return {"meta": meta, "columns": [], "rows": [], "tiles": [], "chart": None}
        sql = f"""
        SELECT
          d.dept_code, d.dept_name,
          COUNT(DISTINCT p.project_id) AS total_projects,
          COALESCE(SUM(ga.grant_amount), 0.00) AS total_funding,
          COUNT(DISTINCT pp.publication_id) AS total_publications
        FROM department AS d
        JOIN project AS p ON p.dept_id = d.dept_id AND p.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
        LEFT JOIN grant_award AS ga ON ga.project_id = p.project_id
        LEFT JOIN project_publication AS pp ON pp.project_id = p.project_id
        GROUP BY d.dept_id, d.dept_code, d.dept_name
        ORDER BY total_funding DESC;
        """
        rows = run_query(sql, pi_proj_ids)
    else:
        sql = """
        SELECT
          d.dept_code, d.dept_name,
          COUNT(DISTINCT p.project_id) AS total_projects,
          COALESCE(SUM(ga.grant_amount), 0.00) AS total_funding,
          COUNT(DISTINCT pa.publication_id) AS total_publications
        FROM department AS d
        LEFT JOIN project AS p ON p.dept_id = d.dept_id
        LEFT JOIN grant_award AS ga ON ga.project_id = p.project_id
        LEFT JOIN researcher AS r ON r.dept_id = d.dept_id
        LEFT JOIN publication_author AS pa ON pa.researcher_id = r.researcher_id
        GROUP BY d.dept_id, d.dept_code, d.dept_name
        ORDER BY total_funding DESC;
        """
        rows = run_query(sql)

    cols = [
        {"key": "dept_code", "label": "Dept Code"},
        {"key": "dept_name", "label": "Department"},
        {"key": "total_projects", "label": "Projects"},
        {"key": "total_funding", "label": "Funding (INR)", "is_money": True},
        {"key": "total_publications", "label": "Publications"}
    ]
    tot_fund = sum(float(r["total_funding"]) for r in rows)
    tot_proj = sum(r["total_projects"] for r in rows)
    tiles = [
        {"label": "Total Funding", "value": tot_fund, "is_money": True},
        {"label": "Active Projects", "value": tot_proj}
    ]
    chart = {
        "type": "bar",
        "labels": [r["dept_code"] for r in rows],
        "datasets": [
            {"label": "Projects", "data": [int(r["total_projects"]) for r in rows]},
            {"label": "Publications", "data": [int(r["total_publications"]) for r in rows]}
        ]
    }
    return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

def _gen_r8(meta, filters, role, is_viewer, is_pi, pi_proj_ids, user_id=None):
    # Expenditure statement / running balance
    if is_viewer:
        # Redacted summary per agency/month
        sql = """
        SELECT
          DATE_FORMAT(exp.expense_date, '%Y-%m') AS expense_month,
          bh.head_name,
          COUNT(exp.expenditure_id) AS expense_count,
          SUM(exp.amount) AS total_amount
        FROM expenditure AS exp
        JOIN budget_head AS bh ON bh.head_id = exp.head_id
        GROUP BY expense_month, bh.head_name
        ORDER BY expense_month DESC;
        """
        rows = run_query(sql)
        cols = [
            {"key": "expense_month", "label": "Month"},
            {"key": "head_name", "label": "Budget Head"},
            {"key": "expense_count", "label": "Transactions"},
            {"key": "total_amount", "label": "Total (INR)", "is_money": True}
        ]
        tot = sum(float(r["total_amount"]) for r in rows)
        tiles = [{"label": "Total Recorded Expenditure", "value": tot, "is_money": True}]
        chart = {
            "type": "bar",
            "labels": [r["expense_month"] for r in rows[:12]],
            "datasets": [{"label": "Monthly Spend", "data": [float(r["total_amount"]) for r in rows[:12]]}]
        }
        return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

    grant_id = filters.get("grant_id")
    from app.services.expenditures import get_grant_statement
    if not grant_id:
        # Default to first available grant
        if is_pi:
            if not pi_proj_ids:
                return {"meta": meta, "columns": [], "rows": [], "tiles": [], "chart": None}
            chk_sql = f"SELECT grant_id FROM grant_award WHERE project_id IN ({','.join(['%s']*len(pi_proj_ids))}) LIMIT 1;"
            chk_row = run_query(chk_sql, pi_proj_ids, fetchone=True)
        else:
            chk_row = run_query("SELECT grant_id FROM grant_award ORDER BY grant_id ASC LIMIT 1;", fetchone=True)
        grant_id = chk_row["grant_id"] if chk_row else None

    if not grant_id:
        return {"meta": meta, "columns": [], "rows": [], "tiles": [], "chart": None}

    stmt = get_grant_statement(int(grant_id), role, user_id)
    if not stmt:
        return {"meta": meta, "columns": [], "rows": [], "tiles": [], "chart": None}

    cols = [
        {"key": "expense_date", "label": "Date"},
        {"key": "voucher_no", "label": "Voucher"},
        {"key": "head_name", "label": "Budget Head"},
        {"key": "description", "label": "Description"},
        {"key": "amount", "label": "Debit (INR)", "is_money": True},
        {"key": "running_balance", "label": "Running Balance (INR)", "is_money": True}
    ]
    tiles = [
        {"label": "Grant Total", "value": stmt["grant_amount"], "is_money": True},
        {"label": "Total Spent", "value": stmt["total_spent"], "is_money": True},
        {"label": "Remaining Balance", "value": stmt["final_balance"], "is_money": True}
    ]
    chart = {
        "type": "line",
        "labels": [tx["expense_date"].strftime("%d %b") if hasattr(tx["expense_date"], "strftime") else str(tx["expense_date"]) for tx in stmt["transactions"]],
        "datasets": [
            {"label": "Running Balance (INR)", "data": [float(tx["running_balance"]) for tx in stmt["transactions"]]}
        ]
    }
    return {"meta": meta, "columns": cols, "rows": stmt["transactions"], "tiles": tiles, "chart": chart}

def _gen_r9(meta, filters, role, is_viewer, is_pi, pi_proj_ids):
    # Patent status
    where = []
    params = []
    if is_pi:
        if not pi_proj_ids:
            return {"meta": meta, "columns": [], "rows": [], "tiles": [], "chart": None}
        where.append(f"pp.project_id IN ({','.join(['%s']*len(pi_proj_ids))})")
        params.extend(pi_proj_ids)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    if is_pi:
        sql = f"""
        SELECT
          pat.status,
          pat.jurisdiction,
          COUNT(DISTINCT pat.patent_id) AS total_patents
        FROM patent AS pat
        JOIN project_patent AS pp ON pp.patent_id = pat.patent_id
        {where_sql}
        GROUP BY pat.status, pat.jurisdiction
        ORDER BY pat.status ASC;
        """
    else:
        sql = """
        SELECT
          pat.status,
          pat.jurisdiction,
          COUNT(pat.patent_id) AS total_patents
        FROM patent AS pat
        GROUP BY pat.status, pat.jurisdiction
        ORDER BY pat.status ASC;
        """
    rows = run_query(sql, params)
    cols = [
        {"key": "status", "label": "Status"},
        {"key": "jurisdiction", "label": "Jurisdiction"},
        {"key": "total_patents", "label": "Count"}
    ]
    tot = sum(r["total_patents"] for r in rows)
    granted = sum(r["total_patents"] for r in rows if r["status"] == "Granted")
    tiles = [
        {"label": "Total Patents", "value": tot},
        {"label": "Granted Patents", "value": granted}
    ]
    statuses = ["Filed", "Published", "Granted", "Rejected", "Lapsed"]
    status_counts = []
    for s in statuses:
        cnt = sum(r["total_patents"] for r in rows if r["status"] == s)
        status_counts.append(cnt)

    chart = {
        "type": "doughnut",
        "labels": statuses,
        "datasets": [{"label": "Patents", "data": status_counts}]
    }
    return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

def _gen_r10(meta, filters, role, is_viewer, is_pi, pi_proj_ids):
    # Project closing summary (Completed & Cancelled)
    where = ["p.status IN ('Completed', 'Cancelled')"]
    params = []
    if is_pi:
        if not pi_proj_ids:
            return {"meta": meta, "columns": [], "rows": [], "tiles": [], "chart": None}
        where.append(f"p.project_id IN ({','.join(['%s']*len(pi_proj_ids))})")
        params.extend(pi_proj_ids)

    where_sql = "WHERE " + " AND ".join(where)

    if is_viewer:
        sql = f"""
        SELECT
          d.dept_code, d.dept_name, p.status,
          COUNT(p.project_id) AS closed_projects_count,
          SUM(COALESCE(ga.total_grant, 0.00)) AS total_grant,
          SUM(COALESCE(e.total_spent, 0.00)) AS total_spent,
          SUM(COALESCE(ga.total_grant, 0.00) - COALESCE(e.total_spent, 0.00)) AS unspent_balance
        FROM project AS p
        JOIN department AS d ON d.dept_id = p.dept_id
        LEFT JOIN (
          SELECT project_id, SUM(grant_amount) AS total_grant FROM grant_award GROUP BY project_id
        ) AS ga ON ga.project_id = p.project_id
        LEFT JOIN (
          SELECT g.project_id, SUM(exp.amount) AS total_spent
          FROM grant_award AS g
          JOIN expenditure AS exp ON exp.grant_id = g.grant_id
          GROUP BY g.project_id
        ) AS e ON e.project_id = p.project_id
        {where_sql}
        GROUP BY d.dept_id, d.dept_code, d.dept_name, p.status
        ORDER BY total_grant DESC;
        """
        rows = run_query(sql, params)
        cols = [
            {"key": "dept_code", "label": "Dept Code"},
            {"key": "status", "label": "Final Status"},
            {"key": "closed_projects_count", "label": "Closed Projects"},
            {"key": "total_grant", "label": "Sanctioned (INR)", "is_money": True},
            {"key": "total_spent", "label": "Spent (INR)", "is_money": True},
            {"key": "unspent_balance", "label": "Unspent Balance (INR)", "is_money": True}
        ]
    else:
        sql = f"""
        SELECT
          p.project_code, p.title, d.dept_code, p.status,
          COALESCE(ga.total_grant, 0.00) AS total_grant,
          COALESCE(e.total_spent, 0.00) AS total_spent,
          (COALESCE(ga.total_grant, 0.00) - COALESCE(e.total_spent, 0.00)) AS unspent_balance
        FROM project AS p
        JOIN department AS d ON d.dept_id = p.dept_id
        LEFT JOIN (
          SELECT project_id, SUM(grant_amount) AS total_grant FROM grant_award GROUP BY project_id
        ) AS ga ON ga.project_id = p.project_id
        LEFT JOIN (
          SELECT g.project_id, SUM(exp.amount) AS total_spent
          FROM grant_award AS g
          JOIN expenditure AS exp ON exp.grant_id = g.grant_id
          GROUP BY g.project_id
        ) AS e ON e.project_id = p.project_id
        {where_sql}
        ORDER BY total_grant DESC;
        """
        rows = run_query(sql, params)
        cols = [
            {"key": "project_code", "label": "Project Code"},
            {"key": "title", "label": "Title"},
            {"key": "dept_code", "label": "Dept"},
            {"key": "status", "label": "Final Status"},
            {"key": "total_grant", "label": "Sanctioned (INR)", "is_money": True},
            {"key": "total_spent", "label": "Spent (INR)", "is_money": True},
            {"key": "unspent_balance", "label": "Unspent Balance (INR)", "is_money": True}
        ]

    tot_grant = sum(float(r["total_grant"]) for r in rows)
    tot_spent = sum(float(r["total_spent"]) for r in rows)
    tot_unspent = sum(float(r["unspent_balance"]) for r in rows)
    tiles = [
        {"label": "Closed Projects", "value": len(rows)},
        {"label": "Total Sanctioned", "value": tot_grant, "is_money": True},
        {"label": "Total Utilized", "value": tot_spent, "is_money": True},
        {"label": "Surplus Unspent", "value": tot_unspent, "is_money": True}
    ]
    chart = {
        "type": "bar",
        "labels": [r.get("project_code") or r.get("dept_code") for r in rows],
        "datasets": [
            {"label": "Spent (INR)", "data": [float(r["total_spent"]) for r in rows]},
            {"label": "Unspent Balance (INR)", "data": [float(r["unspent_balance"]) for r in rows]}
        ]
    }
    return {"meta": meta, "columns": cols, "rows": rows, "tiles": tiles, "chart": chart}

def export_report_csv(report_code: str, filters: Dict[str, Any], role: str, user_id: int) -> str:
    """Exports generated report rows to CSV respecting role redactions."""
    data = generate_report(report_code, filters, role, user_id)
    if not data or not data["rows"]:
        return ""

    output = io.StringIO()
    writer = csv.writer(output)
    meta = data["meta"]
    writer.writerow([f"Report {meta['code']}: {meta['title']}"])
    writer.writerow([meta["description"]])
    writer.writerow([])

    # Header
    headers = [col["label"] for col in data["columns"]]
    writer.writerow(headers)

    # Rows
    for row in data["rows"]:
        line = []
        for col in data["columns"]:
            val = row.get(col["key"])
            if col.get("is_money") and val is not None:
                line.append(f"{float(val):.2f}")
            else:
                line.append(val if val is not None else "")
        writer.writerow(line)

    return output.getvalue()
