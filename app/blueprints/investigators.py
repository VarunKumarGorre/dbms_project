"""
RPGMS Investigators Blueprint
File: app/blueprints/investigators.py
Author: Antigravity AI
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from app.auth import require_role
from app.services.investigators import (
    get_investigators_list, get_investigator_detail, get_my_workload,
    create_researcher, update_researcher
)
from app.errors import format_db_error
from app.db import run_query

investigators_bp = Blueprint("investigators", __name__)

@investigators_bp.route("/investigators")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def index():
    role = session.get("role")
    user_id = session.get("user_id")

    filters = {
        "q": request.args.get("q", ""),
        "dept_id": request.args.get("dept_id", ""),
        "designation": request.args.get("designation", "All"),
        "active_only": request.args.get("active_only") == "1"
    }

    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("size", 20, type=int)
    sort_key = request.args.get("sort", "name")
    sort_dir = request.args.get("dir", "asc")

    result = get_investigators_list(filters, role, user_id, page=page, page_size=page_size, sort_key=sort_key, sort_dir=sort_dir)
    departments = run_query("SELECT dept_id, dept_name, dept_code FROM department ORDER BY dept_name ASC;")
    designations = ["Professor", "Associate Professor", "Assistant Professor", "Research Scholar", "Postdoctoral Fellow"]

    return render_template(
        "investigators/list.html",
        investigators=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
        filters=filters,
        departments=departments,
        designations=designations,
        sort_key=sort_key,
        sort_dir=sort_dir,
        role=role
    )

@investigators_bp.route("/investigators/<int:id>")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def detail(id: int):
    role = session.get("role")
    user_id = session.get("user_id")

    data = get_investigator_detail(id, role, user_id)
    if not data:
        abort(404 if role != "PI" else 403)

    return render_template("investigators/detail.html", data=data, role=role)

@investigators_bp.route("/my-workload")
@require_role(["PI"])
def my_workload():
    user_id = session.get("user_id")
    data = get_my_workload(user_id)
    return render_template("investigators/workload.html", data=data)

@investigators_bp.route("/investigators/new", methods=["GET", "POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def new_researcher():
    departments = run_query("SELECT dept_id, dept_name, dept_code FROM department ORDER BY dept_name ASC;")
    if request.method == "POST":
        data = {
            "first_name": request.form.get("first_name", ""),
            "last_name": request.form.get("last_name", ""),
            "email": request.form.get("email", ""),
            "phone": request.form.get("phone", ""),
            "orcid": request.form.get("orcid", ""),
            "designation": request.form.get("designation", ""),
            "dept_id": request.form.get("dept_id"),
            "is_active": request.form.get("is_active") == "1"
        }
        try:
            rid = create_researcher(data)
            flash("Researcher profile created successfully.", "success")
            return redirect(url_for("investigators.detail", id=rid))
        except Exception as e:
            flash(format_db_error(e), "danger")

    return render_template("investigators/form.html", researcher=None, departments=departments)

@investigators_bp.route("/investigators/<int:id>/edit", methods=["GET", "POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def edit_researcher(id: int):
    res = run_query("SELECT * FROM researcher WHERE researcher_id = %s;", (id,), fetchone=True)
    if not res:
        abort(404)

    departments = run_query("SELECT dept_id, dept_name, dept_code FROM department ORDER BY dept_name ASC;")
    if request.method == "POST":
        data = {
            "first_name": request.form.get("first_name", ""),
            "last_name": request.form.get("last_name", ""),
            "email": request.form.get("email", ""),
            "phone": request.form.get("phone", ""),
            "orcid": request.form.get("orcid", ""),
            "designation": request.form.get("designation", ""),
            "dept_id": request.form.get("dept_id"),
            "is_active": request.form.get("is_active") == "1"
        }
        try:
            update_researcher(id, data)
            flash("Researcher profile updated successfully.", "success")
            return redirect(url_for("investigators.detail", id=id))
        except Exception as e:
            flash(format_db_error(e), "danger")

    return render_template("investigators/form.html", researcher=res, departments=departments)
