"""
RPGMS Expenditure Blueprint
File: app/blueprints/expenditure.py
Author: Antigravity AI
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, Response
from app.auth import require_role, can_access_grant
from app.services.expenditures import (
    get_expenditures_list, record_expenditure, get_grant_statement, export_statement_csv
)
from app.errors import format_db_error
from app.db import run_query

expenditure_bp = Blueprint("expenditure", __name__)

@expenditure_bp.route("/expenditure")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def index():
    role = session.get("role")
    user_id = session.get("user_id")

    filters = {
        "q": request.args.get("q", ""),
        "grant_id": request.args.get("grant_id", ""),
        "head_id": request.args.get("head_id", ""),
        "from_date": request.args.get("from_date", ""),
        "to_date": request.args.get("to_date", "")
    }

    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("size", 20, type=int)
    sort_key = request.args.get("sort", "date")
    sort_dir = request.args.get("dir", "desc")

    result = get_expenditures_list(filters, role, user_id, page=page, page_size=page_size, sort_key=sort_key, sort_dir=sort_dir)
    budget_heads = run_query("SELECT head_id, head_name FROM budget_head ORDER BY head_name ASC;")

    return render_template(
        "expenditure/list.html",
        expenditures=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
        filters=filters,
        budget_heads=budget_heads,
        sort_key=sort_key,
        sort_dir=sort_dir,
        role=role
    )

@expenditure_bp.route("/expenditure/new", methods=["GET", "POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def new_expense():
    preselected_grant_id = request.args.get("grant_id", type=int)
    grants = run_query("""
        SELECT ga.grant_id, ga.grant_number, p.project_code, fa.agency_name AS agency_code
        FROM grant_award AS ga
        JOIN project AS p ON p.project_id = ga.project_id
        JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
        WHERE ga.status = 'Active' AND p.status IN ('Proposed', 'Active')
        ORDER BY ga.grant_number ASC;
    """)

    if request.method == "POST":
        grant_id = request.form.get("grant_id", type=int)
        head_id = request.form.get("head_id", type=int)
        expense_date = request.form.get("expense_date", "").strip()
        amount = request.form.get("amount", type=float)
        voucher_no = request.form.get("voucher_no", "").strip()
        description = request.form.get("description", "").strip()
        user_id = session.get("user_id")

        try:
            exp_id, head_rem, grant_rem = record_expenditure(
                grant_id, head_id, expense_date, amount, description, voucher_no, user_id
            )
            flash(f"Expenditure recorded successfully (Voucher: {voucher_no}).", "success")
            return redirect(url_for("expenditure.statement", grant_id=grant_id))
        except Exception as e:
            flash(format_db_error(e), "danger")

    return render_template(
        "expenditure/entry.html",
        grants=grants,
        preselected_grant_id=preselected_grant_id
    )

@expenditure_bp.route("/expenditure/statement/<int:grant_id>")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def statement(grant_id: int):
    role = session.get("role")
    user_id = session.get("user_id")

    if not can_access_grant(grant_id):
        abort(403)

    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")

    if request.args.get("format") == "csv":
        csv_data = export_statement_csv(grant_id, role, user_id, from_date, to_date)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=expenditure_statement_grant_{grant_id}.csv"}
        )

    stmt = get_grant_statement(grant_id, role, user_id, from_date, to_date)
    if not stmt:
        abort(404)

    return render_template(
        "expenditure/statement.html",
        statement=stmt,
        from_date=from_date,
        to_date=to_date,
        role=role
    )
