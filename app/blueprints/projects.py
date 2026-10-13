"""
RPGMS Projects Blueprint
File: app/blueprints/projects.py
Author: Antigravity AI
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, Response
from app.auth import require_login, require_role, can_access_project
from app.services.projects import (
    get_projects_list, get_project_detail, export_projects_csv,
    register_project, update_project_status, assign_investigator,
    remove_investigator, change_project_pi, link_publication_to_project,
    link_patent_to_project, create_project_report, update_project_report,
    review_project_report
)
from app.errors import format_db_error
from app.db import run_query

projects_bp = Blueprint("projects", __name__)

@projects_bp.route("/projects")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def index():
    role = session.get("role")
    user_id = session.get("user_id")

    filters = {
        "q": request.args.get("q", ""),
        "dept_id": request.args.get("dept_id", ""),
        "status": request.args.get("status", "All"),
        "year": request.args.get("year", "")
    }

    if request.args.get("format") == "csv":
        csv_data = export_projects_csv(filters, role, user_id)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=projects_export.csv"}
        )

    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("size", 10, type=int)
    sort_key = request.args.get("sort", "code")
    sort_dir = request.args.get("dir", "asc")

    result = get_projects_list(filters, role, user_id, page=page, page_size=page_size, sort_key=sort_key, sort_dir=sort_dir)
    departments = run_query("SELECT dept_id, dept_name, dept_code FROM department ORDER BY dept_name ASC;")
    years = run_query("SELECT DISTINCT YEAR(start_date) AS yr FROM project ORDER BY yr DESC;")

    return render_template(
        "projects/list.html",
        projects=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
        filters=filters,
        departments=departments,
        years=[y["yr"] for y in years if y["yr"]],
        sort_key=sort_key,
        sort_dir=sort_dir
    )

@projects_bp.route("/projects/new", methods=["GET", "POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def new_project():
    departments = run_query("SELECT dept_id, dept_name, dept_code FROM department ORDER BY dept_name ASC;")
    if request.method == "POST":
        code = request.form.get("project_code", "").strip()
        title = request.form.get("title", "").strip()
        abstract = request.form.get("abstract", "").strip()
        dept_id = request.form.get("dept_id", type=int)
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        pi_res_id = request.form.get("pi_res_id", type=int) or request.form.get("pi_id", type=int)
        pi_effort = request.form.get("pi_effort", type=float)
        if pi_effort is None:
            pi_effort = 25.0

        try:
            proj_id = register_project(code, title, abstract, dept_id, start_date, end_date, pi_res_id, pi_effort)
            flash(f"Project {code} registered successfully.", "success")
            return redirect(url_for("projects.detail", id=proj_id))
        except Exception as e:
            flash(format_db_error(e), "danger")

    return render_template("projects/new.html", departments=departments)

@projects_bp.route("/projects/<int:id>")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def detail(id: int):
    role = session.get("role")
    user_id = session.get("user_id")

    if not can_access_project(id):
        abort(403)

    data = get_project_detail(id, role, user_id)
    if not data:
        abort(404)

    active_tab = request.args.get("tab", "overview")
    return render_template("projects/detail.html", data=data, active_tab=active_tab, role=role)

@projects_bp.route("/projects/<int:id>/status", methods=["POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def change_status(id: int):
    new_status = request.form.get("status")
    try:
        update_project_status(id, new_status)
        flash(f"Project status updated to {new_status}.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")
    return redirect(url_for("projects.detail", id=id))

@projects_bp.route("/projects/<int:id>/investigators", methods=["POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def assign_member(id: int):
    res_id = request.form.get("researcher_id", type=int)
    role_assigned = request.form.get("role")
    effort = request.form.get("effort_percent", type=float)
    try:
        assign_investigator(id, res_id, role_assigned, effort)
        flash("Investigator assigned successfully.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")
    return redirect(url_for("projects.detail", id=id, tab="team"))

@projects_bp.route("/projects/<int:id>/investigators/<int:rid>/remove", methods=["POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def remove_member(id: int, rid: int):
    try:
        remove_investigator(id, rid)
        flash("Investigator removed from project.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")
    return redirect(url_for("projects.detail", id=id, tab="team"))

@projects_bp.route("/projects/<int:id>/pi", methods=["POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def transfer_pi(id: int):
    new_res_id = request.form.get("new_res_id", type=int)
    new_effort = request.form.get("new_effort", type=float)
    try:
        change_project_pi(id, new_res_id, new_effort)
        flash("Principal Investigator updated successfully.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")
    return redirect(url_for("projects.detail", id=id, tab="team"))

@projects_bp.route("/projects/<int:id>/publications", methods=["POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def link_pub(id: int):
    if not can_access_project(id):
        abort(403)
    pub_id = request.form.get("publication_id", type=int)
    try:
        link_publication_to_project(id, pub_id)
        flash("Publication linked to project.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")
    return redirect(url_for("projects.detail", id=id, tab="publications"))

@projects_bp.route("/projects/<int:id>/patents", methods=["POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def link_pat(id: int):
    if not can_access_project(id):
        abort(403)
    pat_id = request.form.get("patent_id", type=int)
    try:
        link_patent_to_project(id, pat_id)
        flash("Patent linked to project.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")
    return redirect(url_for("projects.detail", id=id, tab="patents"))

@projects_bp.route("/projects/<int:id>/reports/new", methods=["GET", "POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def new_report(id: int):
    if not can_access_project(id):
        abort(403)

    proj = run_query("SELECT project_id, project_code, title, start_date, end_date FROM project WHERE project_id = %s;", (id,), fetchone=True)
    if not proj:
        abort(404)

    if request.method == "POST":
        rep_type = request.form.get("report_type")
        p_start = request.form.get("period_start")
        p_end = request.form.get("period_end")
        summary = request.form.get("summary", "")
        action = request.form.get("action", "draft")
        is_submit = (action == "submit")
        user_id = session.get("user_id")

        try:
            create_project_report(id, rep_type, p_start, p_end, summary, is_submit, user_id)
            flash(f"Report {'submitted' if is_submit else 'saved as draft'}.", "success")
            return redirect(url_for("projects.detail", id=id, tab="reports"))
        except Exception as e:
            flash(format_db_error(e), "danger")

    return render_template("projects/report_form.html", project=proj, report=None)

@projects_bp.route("/projects/<int:id>/reports/<int:report_id>", methods=["GET", "POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def edit_report(id: int, report_id: int):
    if not can_access_project(id):
        abort(403)

    proj = run_query("SELECT project_id, project_code, title FROM project WHERE project_id = %s;", (id,), fetchone=True)
    rep = run_query("SELECT * FROM report WHERE report_id = %s AND project_id = %s;", (report_id, id), fetchone=True)
    if not proj or not rep:
        abort(404)

    if rep["status"] not in ("Draft", "Returned"):
        flash("Submitted and accepted reports cannot be edited.", "warning")
        return redirect(url_for("projects.detail", id=id, tab="reports"))

    if request.method == "POST":
        rep_type = request.form.get("report_type")
        p_start = request.form.get("period_start")
        p_end = request.form.get("period_end")
        summary = request.form.get("summary", "")
        action = request.form.get("action", "draft")
        is_submit = (action == "submit")
        user_id = session.get("user_id")

        try:
            update_project_report(report_id, id, rep_type, p_start, p_end, summary, is_submit, user_id)
            flash(f"Report {'submitted' if is_submit else 'updated'}.", "success")
            return redirect(url_for("projects.detail", id=id, tab="reports"))
        except Exception as e:
            flash(format_db_error(e), "danger")

    return render_template("projects/report_form.html", project=proj, report=rep)

@projects_bp.route("/projects/<int:id>/reports/<int:report_id>/review", methods=["POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def review_report(id: int, report_id: int):
    new_status = request.form.get("status")
    user_id = session.get("user_id")
    try:
        review_project_report(report_id, id, new_status, user_id)
        flash(f"Report {new_status.lower()}.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")
    return redirect(url_for("projects.detail", id=id, tab="reports"))
