"""
RPGMS Milestones Blueprint
File: app/blueprints/milestones.py
Author: Antigravity AI
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from app.auth import require_role, can_access_project, get_pi_project_ids
from app.services.milestones import (
    get_milestones_list, create_milestone, update_milestone_status, complete_milestone
)
from app.errors import format_db_error
from app.db import run_query

milestones_bp = Blueprint("milestones", __name__)

@milestones_bp.route("/milestones")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def index():
    role = session.get("role")
    user_id = session.get("user_id")

    filters = {
        "q": request.args.get("q", ""),
        "project_id": request.args.get("project_id", ""),
        "dept_id": request.args.get("dept_id", ""),
        "status": request.args.get("status", "All"),
        "overdue_only": request.args.get("overdue") == "1"
    }

    view_mode = request.args.get("view", "table")
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("size", 20, type=int)
    sort_key = request.args.get("sort", "due_date")
    sort_dir = request.args.get("dir", "asc")

    result = get_milestones_list(filters, role, user_id, page=page, page_size=page_size, sort_key=sort_key, sort_dir=sort_dir)

    # Scoped projects for modal dropdown
    if role == "PI":
        pids = list(get_pi_project_ids(user_id))
        if pids:
            projects = run_query(f"SELECT project_id, project_code, title, start_date, end_date FROM project WHERE project_id IN ({','.join(['%s']*len(pids))}) ORDER BY project_code ASC;", pids)
        else:
            projects = []
    else:
        projects = run_query("SELECT project_id, project_code, title, start_date, end_date FROM project ORDER BY project_code ASC;")

    departments = run_query("SELECT dept_id, dept_name, dept_code FROM department ORDER BY dept_name ASC;")

    return render_template(
        "milestones/list.html",
        milestones=result["items"],
        timeline_projects=result["timeline_projects"],
        view_mode=view_mode,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
        filters=filters,
        projects=projects,
        departments=departments,
        sort_key=sort_key,
        sort_dir=sort_dir,
        role=role
    )

@milestones_bp.route("/milestones/new", methods=["POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def new_milestone():
    project_id = request.form.get("project_id", type=int)
    if not can_access_project(project_id):
        abort(403)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_date = request.form.get("due_date", "").strip()
    status = request.form.get("status", "Pending")

    return_url = request.form.get("return_url") or url_for("milestones.index")

    try:
        create_milestone(project_id, title, description, due_date, status)
        flash("Milestone scheduled successfully.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")

    return redirect(return_url)

@milestones_bp.route("/milestones/<int:id>/status", methods=["POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def change_status(id: int):
    # Verify project access
    row = run_query("SELECT project_id FROM milestone WHERE milestone_id = %s;", (id,), fetchone=True)
    if not row or not can_access_project(row["project_id"]):
        abort(403)

    new_status = request.form.get("status")
    return_url = request.form.get("return_url") or url_for("milestones.index")

    try:
        update_milestone_status(id, new_status)
        flash(f"Milestone status updated to {new_status}.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")

    return redirect(return_url)

@milestones_bp.route("/milestones/<int:id>/complete", methods=["POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def complete(id: int):
    row = run_query("SELECT project_id FROM milestone WHERE milestone_id = %s;", (id,), fetchone=True)
    if not row or not can_access_project(row["project_id"]):
        abort(403)

    completed_date = request.form.get("completed_date")
    return_url = request.form.get("return_url") or url_for("milestones.index")

    try:
        complete_milestone(id, completed_date)
        flash("Milestone marked as completed.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")

    return redirect(return_url)
