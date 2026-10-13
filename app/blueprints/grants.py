"""
RPGMS Grants Blueprint
File: app/blueprints/grants.py
Author: Antigravity AI
"""

import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from app.auth import require_role, can_access_grant
from app.services.grants import get_grants_list, get_grant_detail, add_grant_with_budget
from app.errors import format_db_error
from app.db import run_query

grants_bp = Blueprint("grants", __name__)

@grants_bp.route("/grants")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def index():
    role = session.get("role")
    user_id = session.get("user_id")

    filters = {
        "q": request.args.get("q", ""),
        "agency_id": request.args.get("agency_id", ""),
        "status": request.args.get("status", "All"),
        "health": request.args.get("health", "All")
    }

    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("size", 10, type=int)
    sort_key = request.args.get("sort", "grant_number")
    sort_dir = request.args.get("dir", "asc")

    result = get_grants_list(filters, role, user_id, page=page, page_size=page_size, sort_key=sort_key, sort_dir=sort_dir)
    agencies = run_query("SELECT agency_id, agency_name FROM funding_agency ORDER BY agency_name ASC;")

    return render_template(
        "grants/list.html",
        grants=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
        filters=filters,
        agencies=agencies,
        sort_key=sort_key,
        sort_dir=sort_dir,
        role=role
    )

@grants_bp.route("/grants/<int:id>")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def detail(id: int):
    role = session.get("role")
    user_id = session.get("user_id")

    if not can_access_grant(id):
        abort(403)

    data = get_grant_detail(id, role, user_id)
    if not data:
        abort(404)

    return render_template("grants/detail.html", data=data, role=role)

@grants_bp.route("/grants/new", methods=["GET", "POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def new_grant():
    agencies = run_query("SELECT agency_id, agency_name FROM funding_agency ORDER BY agency_name ASC;")
    budget_heads = run_query("SELECT head_id, head_name FROM budget_head ORDER BY head_id ASC;")
    preselected_project_id = request.args.get("project_id", type=int)

    project_info = None
    if preselected_project_id:
        project_info = run_query(
            "SELECT project_id, project_code, title, start_date, end_date FROM project WHERE project_id = %s;",
            (preselected_project_project_id := preselected_project_id,),
            fetchone=True
        )

    if request.method == "POST":
        grant_number = request.form.get("grant_number", "").strip()
        project_id = request.form.get("project_id", type=int)
        agency_id = request.form.get("agency_id", type=int)
        amount = request.form.get("amount", type=float)
        sanction_date = request.form.get("sanction_date", "").strip()
        grant_start = request.form.get("grant_start", "").strip()
        grant_end = request.form.get("grant_end", "").strip()

        # Parse allocations: e.g. alloc_head_1, alloc_head_2
        allocations = []
        for bh in budget_heads:
            val_str = request.form.get(f"alloc_head_{bh['head_id']}", "0").strip()
            if val_str:
                try:
                    val = float(val_str)
                    if val > 0:
                        allocations.append({"head_id": bh["head_id"], "amount": val})
                except ValueError:
                    pass

        try:
            grant_id = add_grant_with_budget(
                grant_number, project_id, agency_id, amount,
                sanction_date, grant_start, grant_end, allocations
            )
            flash(f"Grant {grant_number} and budget heads created successfully.", "success")
            return redirect(url_for("grants.detail", id=grant_id))
        except Exception as e:
            flash(format_db_error(e), "danger")

    return render_template(
        "grants/new.html",
        agencies=agencies,
        budget_heads=budget_heads,
        preselected_project=project_info
    )
