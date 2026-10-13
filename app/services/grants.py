"""
RPGMS Grants & Budget Service
File: app/services/grants.py
Author: Antigravity AI

Handles grant portfolios, budget allocations, live balance checks,
and atomic grant registration with budget heads.
Enforces role-based isolation:
- ADMIN / RESEARCH_OFFICER: Organization-wide access.
- PI: Scoped exclusively to grants belonging to own projects.
- VIEWER: No operational grant detail access.
"""

import json
from typing import Any, Dict, List, Optional
from app.db import run_query, call_procedure
from app.auth import get_pi_project_ids, can_access_grant

ALLOWED_SORT_COLS = {
    "grant_number": "ga.grant_number",
    "project": "p.project_code",
    "agency": "fa.agency_name",
    "amount": "ga.grant_amount",
    "spent": "spent_amount",
    "balance": "balance_amount",
    "status": "ga.status",
}

def get_grants_list(
    filters: Dict[str, Any],
    role: str,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
    sort_key: str = "grant_number",
    sort_dir: str = "asc"
) -> Dict[str, Any]:
    """Retrieves paginated, role-scoped list of grant awards."""
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
        where_clauses.append(f"ga.project_id IN ({placeholders})")
        params.extend(pi_proj_ids)

    q = filters.get("q", "").strip()
    if q:
        where_clauses.append("(ga.grant_number LIKE %s OR p.project_code LIKE %s OR p.title LIKE %s OR fa.agency_name LIKE %s)")
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    agency_id = filters.get("agency_id")
    if agency_id:
        try:
            where_clauses.append("ga.agency_id = %s")
            params.append(int(agency_id))
        except ValueError:
            pass

    status = filters.get("status")
    if status and status != "All":
        where_clauses.append("ga.status = %s")
        params.append(status)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Count
    count_sql = f"""
    SELECT COUNT(*) AS total
    FROM grant_award AS ga
    JOIN project AS p ON p.project_id = ga.project_id
    JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
    {where_sql};
    """
    count_row = run_query(count_sql, params, fetchone=True)
    total_count = count_row["total"] if count_row else 0
    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

    offset = max(0, (page - 1) * page_size)
    direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
    sort_col = ALLOWED_SORT_COLS.get(sort_key.lower(), "ga.grant_number")

    data_sql = f"""
    SELECT
      ga.grant_id,
      ga.grant_number,
      ga.project_id,
      p.project_code,
      p.title AS project_title,
      ga.agency_id,
      fa.agency_name,
      fa.agency_name AS agency_code,
      ga.grant_amount,
      ga.sanction_date,
      ga.grant_start,
      ga.grant_end,
      ga.status,
      COALESCE(e_agg.total_spent, 0.00) AS spent_amount,
      (ga.grant_amount - COALESCE(e_agg.total_spent, 0.00)) AS balance_amount
    FROM grant_award AS ga
    JOIN project AS p ON p.project_id = ga.project_id
    JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
    LEFT JOIN (
      SELECT grant_id, SUM(amount) AS total_spent
      FROM expenditure
      GROUP BY grant_id
    ) AS e_agg ON e_agg.grant_id = ga.grant_id
    {where_sql}
    ORDER BY {sort_col} {direction}
    LIMIT %s OFFSET %s;
    """
    query_params = list(params) + [page_size, offset]
    rows = run_query(data_sql, query_params)

    health_filter = filters.get("health")
    items = []
    for r in rows:
        amt = float(r["grant_amount"])
        spent = float(r["spent_amount"])
        bal = max(0.0, amt - spent)
        pct = round(spent / amt * 100, 1) if amt > 0 else 0.0

        if pct >= 100.0:
            h_class = "Exhausted"
        elif pct >= 90.0:
            h_class = "Near Limit"
        elif pct >= 50.0:
            h_class = "On Track"
        else:
            h_class = "Under 50%"

        if health_filter and health_filter != "All" and h_class != health_filter:
            continue

        items.append({
            "grant_id": r["grant_id"],
            "grant_number": r["grant_number"],
            "project_id": r["project_id"],
            "project_code": r["project_code"],
            "project_title": r["project_title"],
            "agency_id": r["agency_id"],
            "agency_name": r["agency_name"],
            "agency_code": r["agency_code"],
            "grant_amount": amt,
            "spent_amount": spent,
            "balance_amount": bal,
            "spent_pct": pct,
            "sanction_date": r["sanction_date"],
            "grant_start": r["grant_start"],
            "grant_end": r["grant_end"],
            "status": r["status"],
            "health_class": h_class
        })

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

def get_grant_detail(grant_id: int, role: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves grant detail, budget allocations, and expense history."""
    if not can_access_grant(grant_id):
        return None

    sql_grant = """
    SELECT
      ga.grant_id, ga.grant_number, ga.project_id, ga.agency_id,
      ga.grant_amount, ga.sanction_date, ga.grant_start, ga.grant_end, ga.status,
      p.project_code, p.title AS project_title, p.status AS project_status,
      fa.agency_name, fa.agency_name AS agency_code,
      CONCAT(r_pi.first_name, ' ', r_pi.last_name) AS pi_name
    FROM grant_award AS ga
    JOIN project AS p ON p.project_id = ga.project_id
    JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
    LEFT JOIN (
      SELECT pi.project_id, r.first_name, r.last_name
      FROM project_investigator AS pi
      JOIN researcher AS r ON r.researcher_id = pi.researcher_id
      WHERE pi.role = 'PI'
    ) AS r_pi ON r_pi.project_id = p.project_id
    WHERE ga.grant_id = %s;
    """
    grant = run_query(sql_grant, (grant_id,), fetchone=True)
    if not grant:
        return None

    # Budget head allocations
    sql_alloc = """
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
    alloc_rows = run_query(sql_alloc, (grant_id,))
    allocations = []
    total_spent = 0.0
    for a in alloc_rows:
        al = float(a["allocated_amount"])
        sp = float(a["spent_amount"])
        total_spent += sp
        rem = max(0.0, al - sp)
        pct = round(sp / al * 100, 1) if al > 0 else 0.0
        allocations.append({
            "head_id": a["head_id"],
            "head_name": a["head_name"],
            "allocated": al,
            "spent": sp,
            "remaining": rem,
            "spent_pct": pct
        })

    grant_amt = float(grant["grant_amount"])
    balance = max(0.0, grant_amt - total_spent)
    used_pct = round(total_spent / grant_amt * 100, 1) if grant_amt > 0 else 0.0

    if used_pct >= 100.0:
        health_class = "Exhausted"
    elif used_pct >= 90.0:
        health_class = "Near Limit"
    elif used_pct >= 50.0:
        health_class = "On Track"
    else:
        health_class = "Under 50%"

    # Expenditures for this grant
    sql_exp = """
    SELECT
      exp.expenditure_id, exp.expense_date, exp.voucher_no,
      bh.head_name, exp.description, exp.amount,
      u.username AS recorded_by
    FROM expenditure AS exp
    JOIN budget_head AS bh ON bh.head_id = exp.head_id
    LEFT JOIN user_account AS u ON u.user_id = exp.recorded_by
    WHERE exp.grant_id = %s
    ORDER BY exp.expense_date DESC, exp.expenditure_id DESC;
    """
    expenditures = run_query(sql_exp, (grant_id,))

    return {
        "grant": grant,
        "kpis": {
            "amount": grant_amt,
            "spent": total_spent,
            "balance": balance,
            "used_pct": used_pct,
            "health_class": health_class
        },
        "allocations": allocations,
        "expenditures": expenditures
    }

def add_grant_with_budget(
    grant_number: str,
    project_id: int,
    agency_id: int,
    amount: float,
    sanction_date: str,
    grant_start: str,
    grant_end: str,
    allocations_list: List[Dict[str, Any]]
) -> int:
    """Invokes transaction-owning sp_add_grant_with_budget procedure."""
    # Convert allocations to JSON: [{"head_id": 1, "amount": 100000.0}, ...]
    alloc_json = json.dumps(allocations_list)
    out_params, _ = call_procedure(
        "sp_add_grant_with_budget",
        (grant_number.strip(), project_id, agency_id, amount,
         sanction_date, grant_start, grant_end, alloc_json, None)
    )
    # out_params: (grant_num, proj_id, agency_id, amount, sanction, start, end, json, p_grant_id)
    return out_params[8]

def get_grant_heads_api(grant_id: int, role: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Returns allocations with live balances and date constraints for expenditure form."""
    if not can_access_grant(grant_id):
        return None

    detail = get_grant_detail(grant_id, role, user_id)
    if not detail:
        return None

    g = detail["grant"]
    return {
        "grant_id": g["grant_id"],
        "grant_number": g["grant_number"],
        "project_code": g["project_code"],
        "grant_start": g["grant_start"].isoformat() if hasattr(g["grant_start"], "isoformat") else str(g["grant_start"]),
        "grant_end": g["grant_end"].isoformat() if hasattr(g["grant_end"], "isoformat") else str(g["grant_end"]),
        "totals": detail["kpis"],
        "heads": detail["allocations"]
    }
