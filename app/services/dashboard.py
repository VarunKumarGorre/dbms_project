"""
RPGMS Dashboard Service
File: app/services/dashboard.py
Author: Antigravity AI

Aggregates high-level metrics, charts, budget positions, and deadlines.
Enforces role-based isolation:
- ADMIN/RESEARCH_OFFICER: Organization-wide metrics.
- PI: Scoped exclusively to projects where the user is PI.
- VIEWER: Aggregate metrics only; no row-level operational records.
"""

from typing import Any, Dict, List, Optional
from app.db import run_query
from app.auth import get_pi_project_ids

def get_dashboard_data(role: str, user_id: int, researcher_id: Optional[int] = None) -> Dict[str, Any]:
    """Generates all dashboard metrics, chart series, and widgets scoped by role."""
    data = {
        "kpis": {},
        "agency_chart": {"labels": [], "sanctioned": [], "spent": []},
        "health_chart": {"labels": ["Under 50%", "On Track", "Near Limit", "Exhausted"], "counts": [0, 0, 0, 0]},
        "pubs_year_chart": {"years": [], "types": {}, "datasets": []},
        "overdue_milestones": [],
        "near_limit_grants": [],
        "recent_activity": []
    }

    is_pi = (role == "PI")
    is_viewer = (role == "VIEWER")
    pi_proj_ids = list(get_pi_project_ids(user_id)) if is_pi else []

    # If PI has no projects, return clean empty dashboard state
    if is_pi and not pi_proj_ids:
        data["kpis"] = {
            "active_projects": 0, "total_projects": 0,
            "total_sanctioned": 0.0, "agencies_count": 0,
            "total_spent": 0.0, "spent_pct": 0.0,
            "overdue_milestones": 0, "overdue_projects_count": 0,
            "pubs_this_year": 0, "pubs_all_time": 0
        }
        return data

    # 1. KPI Aggregates
    proj_filter = ""
    proj_params = []
    if is_pi:
        placeholders = ",".join(["%s"] * len(pi_proj_ids))
        proj_filter = f"WHERE p.project_id IN ({placeholders})"
        proj_params = pi_proj_ids

    # Projects KPI
    sql_proj = f"""
    SELECT
      COUNT(*) AS total_projects,
      SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) AS active_projects
    FROM project AS p
    {proj_filter};
    """
    row_proj = run_query(sql_proj, proj_params, fetchone=True)
    data["kpis"]["active_projects"] = row_proj["active_projects"] or 0
    data["kpis"]["total_projects"] = row_proj["total_projects"] or 0

    # Funding & Spend KPI
    if is_pi:
        sql_funding = f"""
        SELECT
          COUNT(DISTINCT ga.agency_id) AS agencies_count,
          COALESCE(SUM(ga.grant_amount), 0.00) AS total_sanctioned,
          COALESCE(SUM(exp.amount), 0.00) AS total_spent
        FROM grant_award AS ga
        JOIN project AS p ON p.project_id = ga.project_id
        LEFT JOIN expenditure AS exp ON exp.grant_id = ga.grant_id
        WHERE p.project_id IN ({','.join(['%s']*len(pi_proj_ids))});
        """
        row_fund = run_query(sql_funding, pi_proj_ids, fetchone=True)
    else:
        sql_funding = """
        SELECT
          COUNT(DISTINCT ga.agency_id) AS agencies_count,
          COALESCE(SUM(ga.grant_amount), 0.00) AS total_sanctioned,
          COALESCE(SUM(exp.total_spent), 0.00) AS total_spent
        FROM grant_award AS ga
        LEFT JOIN (
          SELECT grant_id, SUM(amount) AS total_spent FROM expenditure GROUP BY grant_id
        ) AS exp ON exp.grant_id = ga.grant_id;
        """
        row_fund = run_query(sql_funding, fetchone=True)

    sanctioned = float(row_fund["total_sanctioned"] or 0.0)
    spent = float(row_fund["total_spent"] or 0.0)
    data["kpis"]["total_sanctioned"] = sanctioned
    data["kpis"]["agencies_count"] = row_fund["agencies_count"] or 0
    data["kpis"]["total_spent"] = spent
    data["kpis"]["spent_pct"] = round((spent / sanctioned * 100), 1) if sanctioned > 0 else 0.0

    # Overdue Milestones KPI
    if is_pi:
        sql_ms_kpi = f"""
        SELECT
          COUNT(*) AS overdue_milestones,
          COUNT(DISTINCT m.project_id) AS overdue_projects
        FROM milestone AS m
        WHERE m.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
          AND m.status <> 'Completed'
          AND m.due_date < CURDATE();
        """
        row_ms = run_query(sql_ms_kpi, pi_proj_ids, fetchone=True)
    else:
        sql_ms_kpi = """
        SELECT
          COUNT(*) AS overdue_milestones,
          COUNT(DISTINCT project_id) AS overdue_projects
        FROM milestone
        WHERE status <> 'Completed' AND due_date < CURDATE();
        """
        row_ms = run_query(sql_ms_kpi, fetchone=True)

    data["kpis"]["overdue_milestones"] = row_ms["overdue_milestones"] or 0
    data["kpis"]["overdue_projects_count"] = row_ms["overdue_projects"] or 0

    # Publications KPI
    if is_pi:
        sql_pubs = f"""
        SELECT
          COUNT(DISTINCT pub.publication_id) AS pubs_all_time,
          COUNT(DISTINCT CASE WHEN YEAR(pub.pub_date) = YEAR(CURDATE()) THEN pub.publication_id END) AS pubs_this_year
        FROM publication AS pub
        JOIN project_publication AS pp ON pp.publication_id = pub.publication_id
        WHERE pp.project_id IN ({','.join(['%s']*len(pi_proj_ids))});
        """
        row_pubs = run_query(sql_pubs, pi_proj_ids, fetchone=True)
    else:
        sql_pubs = """
        SELECT
          COUNT(*) AS pubs_all_time,
          SUM(CASE WHEN YEAR(pub_date) = YEAR(CURDATE()) THEN 1 ELSE 0 END) AS pubs_this_year
        FROM publication;
        """
        row_pubs = run_query(sql_pubs, fetchone=True)

    data["kpis"]["pubs_this_year"] = row_pubs["pubs_this_year"] or 0
    data["kpis"]["pubs_all_time"] = row_pubs["pubs_all_time"] or 0

    # 2. Funding vs Spend by Agency Chart
    if is_pi:
        sql_agency = f"""
        SELECT fa.agency_name,
               SUM(ga.grant_amount) AS sanctioned,
               COALESCE(SUM(exp.amount), 0.00) AS spent
        FROM funding_agency AS fa
        JOIN grant_award AS ga ON ga.agency_id = fa.agency_id
        JOIN project AS p ON p.project_id = ga.project_id
        LEFT JOIN expenditure AS exp ON exp.grant_id = ga.grant_id
        WHERE p.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
        GROUP BY fa.agency_id, fa.agency_name
        ORDER BY sanctioned DESC
        LIMIT 6;
        """
        rows_agency = run_query(sql_agency, pi_proj_ids)
    else:
        sql_agency = """
        SELECT fa.agency_name,
               SUM(ga.grant_amount) AS sanctioned,
               COALESCE(SUM(e.total_spent), 0.00) AS spent
        FROM funding_agency AS fa
        JOIN grant_award AS ga ON ga.agency_id = fa.agency_id
        LEFT JOIN (
          SELECT grant_id, SUM(amount) AS total_spent FROM expenditure GROUP BY grant_id
        ) AS e ON e.grant_id = ga.grant_id
        GROUP BY fa.agency_id, fa.agency_name
        ORDER BY sanctioned DESC
        LIMIT 6;
        """
        rows_agency = run_query(sql_agency)

    for r in rows_agency:
        data["agency_chart"]["labels"].append(r["agency_name"][:20])
        data["agency_chart"]["sanctioned"].append(float(r["sanctioned"]))
        data["agency_chart"]["spent"].append(float(r["spent"]))

    # 3. Budget Health Doughnut Chart
    if is_pi:
        sql_health = f"""
        SELECT health_status, COUNT(*) AS count
        FROM vw_budget_utilization
        WHERE project_id IN ({','.join(['%s']*len(pi_proj_ids))})
        GROUP BY health_status;
        """
        rows_health = run_query(sql_health, pi_proj_ids)
    else:
        sql_health = "SELECT health_status, COUNT(*) AS count FROM vw_budget_utilization GROUP BY health_status;"
        rows_health = run_query(sql_health)

    health_map = {"Under 50%": 0, "On Track": 1, "Near Limit": 2, "Exhausted": 3}
    for r in rows_health:
        idx = health_map.get(r["health_status"])
        if idx is not None:
            data["health_chart"]["counts"][idx] = r["count"]

    # 4. Overdue Milestones Widget (Omitted for VIEWER; scoped for PI)
    if not is_viewer:
        if is_pi:
            sql_overdue = f"""
            SELECT milestone_id, project_id, project_code, project_title, milestone_title, due_date, status, days_overdue
            FROM vw_milestone_tracker
            WHERE project_id IN ({','.join(['%s']*len(pi_proj_ids))})
              AND is_overdue = TRUE
            ORDER BY days_overdue DESC
            LIMIT 5;
            """
            data["overdue_milestones"] = run_query(sql_overdue, pi_proj_ids)
        else:
            sql_overdue = """
            SELECT milestone_id, project_id, project_code, project_title, milestone_title, due_date, status, days_overdue
            FROM vw_milestone_tracker
            WHERE is_overdue = TRUE
            ORDER BY days_overdue DESC
            LIMIT 5;
            """
            data["overdue_milestones"] = run_query(sql_overdue)

    # 5. Grants Near Limit Widget (Omitted for VIEWER; scoped for PI)
    if not is_viewer:
        if is_pi:
            sql_near = f"""
            SELECT grant_id, grant_number, project_id, project_code, agency_name, agency_name AS agency_code, grant_amount, total_spent AS spent_amount, utilization_pct, health_status AS health
            FROM vw_budget_utilization
            WHERE project_id IN ({','.join(['%s']*len(pi_proj_ids))})
            ORDER BY utilization_pct DESC
            LIMIT 5;
            """
            data["near_limit_grants"] = run_query(sql_near, pi_proj_ids)
        else:
            sql_near = """
            SELECT grant_id, grant_number, project_id, project_code, agency_name, agency_name AS agency_code, grant_amount, total_spent AS spent_amount, utilization_pct, health_status AS health
            FROM vw_budget_utilization
            ORDER BY utilization_pct DESC
            LIMIT 5;
            """
            data["near_limit_grants"] = run_query(sql_near)

    # 6. Publications per Year Stacked Column Chart
    sql_pub_types = """
    SELECT DISTINCT pub_type FROM publication ORDER BY pub_type;
    """
    types = [t["pub_type"] for t in run_query(sql_pub_types)]
    data["pubs_year_chart"]["types"] = types

    if is_pi:
        sql_pub_trend = f"""
        SELECT YEAR(pub.pub_date) AS pub_year, pub.pub_type, COUNT(*) AS count
        FROM publication AS pub
        JOIN project_publication AS pp ON pp.publication_id = pub.publication_id
        WHERE pp.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
        GROUP BY YEAR(pub.pub_date), pub.pub_type
        ORDER BY pub_year ASC;
        """
        pub_rows = run_query(sql_pub_trend, pi_proj_ids)
    else:
        sql_pub_trend = """
        SELECT YEAR(pub_date) AS pub_year, pub_type, COUNT(*) AS count
        FROM publication
        GROUP BY YEAR(pub_date), pub_type
        ORDER BY pub_year ASC;
        """
        pub_rows = run_query(sql_pub_trend)

    years = sorted(list({r["pub_year"] for r in pub_rows}))
    data["pubs_year_chart"]["years"] = years

    type_data = {t: [0] * len(years) for t in types}
    year_idx_map = {y: i for i, y in enumerate(years)}
    for r in pub_rows:
        y_idx = year_idx_map.get(r["pub_year"])
        if y_idx is not None and r["pub_type"] in type_data:
            type_data[r["pub_type"]][y_idx] = r["count"]

    for t in types:
        data["pubs_year_chart"]["datasets"].append({
            "label": t,
            "data": type_data[t]
        })

    # 7. Recent Activity Widget
    # ADMIN sees raw audit_log entries; RESEARCH_OFFICER sees recent expenditures; PI sees own expenses; VIEWER sees nothing
    if role == "ADMIN":
        sql_audit = """
        SELECT table_name, record_id, action, changed_at, changed_by
        FROM audit_log
        ORDER BY log_id DESC
        LIMIT 8;
        """
        data["recent_activity"] = run_query(sql_audit)
    elif role in ("RESEARCH_OFFICER", "PI"):
        if is_pi:
            sql_recent_exp = f"""
            SELECT e.voucher_no, e.amount, e.expense_date, e.created_at, p.project_code,
                   'Expenditure' AS activity_type, e.description
            FROM expenditure AS e
            JOIN grant_award AS ga ON ga.grant_id = e.grant_id
            JOIN project AS p ON p.project_id = ga.project_id
            WHERE p.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
            ORDER BY e.expenditure_id DESC
            LIMIT 8;
            """
            data["recent_activity"] = run_query(sql_recent_exp, pi_proj_ids)
        else:
            sql_recent_exp = """
            SELECT e.voucher_no, e.amount, e.expense_date, e.created_at, p.project_code,
                   'Expenditure' AS activity_type, e.description
            FROM expenditure AS e
            JOIN grant_award AS ga ON ga.grant_id = e.grant_id
            JOIN project AS p ON p.project_id = ga.project_id
            ORDER BY e.expenditure_id DESC
            LIMIT 8;
            """
            data["recent_activity"] = run_query(sql_recent_exp)

    return data
