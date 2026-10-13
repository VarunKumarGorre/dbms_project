"""
RPGMS Admin Blueprint
File: app/blueprints/admin.py
Author: Antigravity AI
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.auth import require_role
from app.services.admin import (
    get_users_list, create_user, disable_user, update_user_role, get_audit_log
)
from app.errors import format_db_error
from app.db import run_query

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin/users", methods=["GET", "POST"])
@require_role(["ADMIN"])
def users():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "VIEWER")
        researcher_id = request.form.get("researcher_id", type=int)

        try:
            create_user(username, password, role, researcher_id)
            flash(f"User account '{username}' created successfully.", "success")
        except Exception as e:
            flash(format_db_error(e), "danger")
        return redirect(url_for("admin.users"))

    user_list = get_users_list()
    researchers = run_query("""
        SELECT r.researcher_id, CONCAT(r.first_name, ' ', r.last_name) AS name, d.dept_name
        FROM researcher AS r
        JOIN department AS d ON d.dept_id = r.dept_id
        WHERE r.is_active = TRUE
        ORDER BY r.last_name ASC;
    """)

    return render_template("admin/users.html", users=user_list, researchers=researchers)

@admin_bp.route("/admin/users/<int:id>/disable", methods=["POST"])
@require_role(["ADMIN"])
def disable(id: int):
    try:
        disable_user(id)
        flash("User account disabled.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")
    return redirect(url_for("admin.users"))

@admin_bp.route("/admin/users/<int:id>/role", methods=["POST"])
@require_role(["ADMIN"])
def change_role(id: int):
    new_role = request.form.get("role")
    researcher_id = request.form.get("researcher_id", type=int)
    try:
        update_user_role(id, new_role, researcher_id)
        flash("User role updated successfully.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")
    return redirect(url_for("admin.users"))

@admin_bp.route("/admin/audit")
@require_role(["ADMIN"])
def audit():
    table_name = request.args.get("table", "")
    action = request.args.get("action", "")
    record_id = request.args.get("record_id", "")
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("size", 25, type=int)

    log_data = get_audit_log(
        table_name=table_name,
        action=action,
        record_id=record_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size
    )

    tables = ["project", "grant_award", "grant_budget_allocation", "expenditure", "milestone", "user_account"]
    actions = ["INSERT", "UPDATE", "DELETE"]

    return render_template(
        "admin/audit.html",
        logs=log_data["items"],
        total=log_data["total"],
        page=log_data["page"],
        page_size=log_data["page_size"],
        total_pages=log_data["total_pages"],
        tables=tables,
        actions=actions,
        filters={
            "table": table_name,
            "action": action,
            "record_id": record_id,
            "from_date": from_date,
            "to_date": to_date
        }
    )
