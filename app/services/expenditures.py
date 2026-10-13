"""
RPGMS Expenditure Service
File: app/services/expenditures.py
Author: Antigravity AI

Handles expenditure ledgers, running-balance statements, CSV statement exports,
and sp_record_expenditure procedure execution.
Enforces role-based isolation:
- ADMIN / RESEARCH_OFFICER: Organization-wide access and write privileges.
- PI: Read-only access scoped strictly to own projects.
- VIEWER: No operational expenditure list access.
"""

import io
import csv
from typing import Any, Dict, List, Optional, Tuple
from app.db import run_query, call_procedure
from app.auth import get_pi_project_ids, can_access_grant

ALLOWED_SORT_COLS = {
    "date": "exp.expense_date",
    "voucher": "exp.voucher_no",
    "project": "p.project_code",
    "grant": "ga.grant_number",
    "head": "bh.head_name",
    "amount": "exp.amount",
}

def get_expenditures_list(
    filters: Dict[str, Any],
    role: str,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    sort_key: str = "date",
    sort_dir: str = "desc"
) -> Dict[str, Any]:
    """Retrieves paginated, role-scoped list of expenditures."""
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
        where_clauses.append("(exp.voucher_no LIKE %s OR exp.description LIKE %s)")
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard])

    grant_id = filters.get("grant_id")
    if grant_id:
        try:
            where_clauses.append("exp.grant_id = %s")
            params.append(int(grant_id))
        except ValueError:
            pass

    project_id = filters.get("project_id")
    if project_id:
        try:
            where_clauses.append("ga.project_id = %s")
            params.append(int(project_id))
        except ValueError:
            pass

    head_id = filters.get("head_id")
    if head_id:
        try:
            where_clauses.append("exp.head_id = %s")
            params.append(int(head_id))
        except ValueError:
            pass

    from_date = filters.get("from_date")
    if from_date:
        where_clauses.append("exp.expense_date >= %s")
        params.append(from_date)

    to_date = filters.get("to_date")
    if to_date:
        where_clauses.append("exp.expense_date <= %s")
        params.append(to_date)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Count
    count_sql = f"""
    SELECT COUNT(*) AS total
    FROM expenditure AS exp
    JOIN grant_award AS ga ON ga.grant_id = exp.grant_id
    JOIN project AS p ON p.project_id = ga.project_id
    JOIN budget_head AS bh ON bh.head_id = exp.head_id
    {where_sql};
    """
    count_row = run_query(count_sql, params, fetchone=True)
    total_count = count_row["total"] if count_row else 0
    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

    offset = max(0, (page - 1) * page_size)
    direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
    sort_col = ALLOWED_SORT_COLS.get(sort_key.lower(), "exp.expense_date")

    data_sql = f"""
    SELECT
      exp.expenditure_id,
      exp.expense_date,
      exp.voucher_no,
      p.project_id,
      p.project_code,
      p.title AS project_title,
      ga.grant_id,
      ga.grant_number,
      bh.head_id,
      bh.head_name,
      exp.description,
      exp.amount,
      u.username AS recorded_by
    FROM expenditure AS exp
    JOIN grant_award AS ga ON ga.grant_id = exp.grant_id
    JOIN project AS p ON p.project_id = ga.project_id
    JOIN budget_head AS bh ON bh.head_id = exp.head_id
    LEFT JOIN user_account AS u ON u.user_id = exp.recorded_by
    {where_sql}
    ORDER BY {sort_col} {direction}, exp.expenditure_id DESC
    LIMIT %s OFFSET %s;
    """
    query_params = list(params) + [page_size, offset]
    rows = run_query(data_sql, query_params)

    items = []
    for r in rows:
        items.append({
            "expenditure_id": r["expenditure_id"],
            "expense_date": r["expense_date"],
            "voucher_no": r["voucher_no"],
            "project_id": r["project_id"],
            "project_code": r["project_code"],
            "project_title": r["project_title"],
            "grant_id": r["grant_id"],
            "grant_number": r["grant_number"],
            "head_id": r["head_id"],
            "head_name": r["head_name"],
            "description": r["description"],
            "amount": float(r["amount"]),
            "recorded_by": r["recorded_by"]
        })

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

def record_expenditure(
    grant_id: int,
    head_id: int,
    expense_date: str,
    amount: float,
    description: str,
    voucher_no: str,
    user_id: int
) -> Tuple[int, float, float]:
    """Invokes transaction-owning sp_record_expenditure procedure."""
    out_params, _ = call_procedure(
        "sp_record_expenditure",
        (grant_id, head_id, expense_date, amount,
         description.strip(), voucher_no.strip(), user_id, None, None, None)
    )
    # out_params: (grant_id, head_id, date, amount, desc, voucher, user_id, p_exp_id, p_head_rem, p_grant_rem)
    exp_id = out_params[7]
    head_remaining = float(out_params[8])
    grant_remaining = float(out_params[9])
    return exp_id, head_remaining, grant_remaining

def get_grant_statement(
    grant_id: int,
    role: str,
    user_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Calculates chronological running balance statement for a grant award."""
    if not can_access_grant(grant_id, role=role, user_id=user_id):
        return None

    # Grant header
    sql_grant = """
    SELECT
      ga.grant_id, ga.grant_number, ga.grant_amount, ga.sanction_date,
      ga.grant_start, ga.grant_end, ga.status,
      p.project_id, p.project_code, p.title AS project_title,
      fa.agency_name
    FROM grant_award AS ga
    JOIN project AS p ON p.project_id = ga.project_id
    JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
    WHERE ga.grant_id = %s;
    """
    grant = run_query(sql_grant, (grant_id,), fetchone=True)
    if not grant:
        return None

    grant_total = float(grant["grant_amount"])

    # All transactions chronologically to accurately maintain running balance
    sql_tx = """
    SELECT
      exp.expenditure_id, exp.expense_date, exp.voucher_no,
      bh.head_name, exp.description, exp.amount,
      u.username AS recorded_by
    FROM expenditure AS exp
    JOIN budget_head AS bh ON bh.head_id = exp.head_id
    LEFT JOIN user_account AS u ON u.user_id = exp.recorded_by
    WHERE exp.grant_id = %s
    ORDER BY exp.expense_date ASC, exp.expenditure_id ASC;
    """
    all_expenses = run_query(sql_tx, (grant_id,))

    running = grant_total
    transactions = []
    total_spent = 0.0

    for tx in all_expenses:
        amt = float(tx["amount"])
        total_spent += amt
        running -= amt

        # Filter check
        include = True
        if from_date and str(tx["expense_date"]) < from_date:
            include = False
        if to_date and str(tx["expense_date"]) > to_date:
            include = False

        if include:
            transactions.append({
                "expenditure_id": tx["expenditure_id"],
                "expense_date": tx["expense_date"],
                "voucher_no": tx["voucher_no"],
                "head_name": tx["head_name"],
                "description": tx["description"],
                "amount": amt,
                "running_balance": round(running, 2),
                "recorded_by": tx["recorded_by"]
            })

    return {
        "grant": grant,
        "grant_amount": grant_total,
        "total_spent": total_spent,
        "final_balance": round(grant_total - total_spent, 2),
        "transactions": transactions
    }

def export_statement_csv(
    grant_id: int,
    role: str,
    user_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> str:
    """Exports grant statement as CSV."""
    statement = get_grant_statement(grant_id, role, user_id, from_date, to_date)
    if not statement:
        return ""

    g = statement["grant"]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Statement of Expenditure"])
    writer.writerow(["Grant Number", g["grant_number"]])
    writer.writerow(["Project Code", g["project_code"]])
    writer.writerow(["Project Title", g["project_title"]])
    writer.writerow(["Agency", g["agency_name"]])
    writer.writerow(["Sanctioned Amount (INR)", f"{statement['grant_amount']:.2f}"])
    writer.writerow([])
    writer.writerow(["Date", "Voucher No", "Budget Head", "Description", "Debit (INR)", "Running Balance (INR)", "Recorded By"])

    for tx in statement["transactions"]:
        writer.writerow([
            tx["expense_date"],
            tx["voucher_no"],
            tx["head_name"],
            tx["description"],
            f"{tx['amount']:.2f}",
            f"{tx['running_balance']:.2f}",
            tx["recorded_by"] or ""
        ])

    writer.writerow([])
    writer.writerow(["Total Spent (INR)", f"{statement['total_spent']:.2f}"])
    writer.writerow(["Remaining Balance (INR)", f"{statement['final_balance']:.2f}"])

    return output.getvalue()
