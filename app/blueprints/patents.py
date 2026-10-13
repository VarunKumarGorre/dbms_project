"""
RPGMS Patents Blueprint
File: app/blueprints/patents.py
Author: Antigravity AI
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from app.auth import require_role
from app.services.patents import (
    get_patents_list, get_patent_detail, create_patent, update_patent_status
)
from app.errors import format_db_error

patents_bp = Blueprint("patents", __name__)

@patents_bp.route("/patents")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def index():
    role = session.get("role")
    user_id = session.get("user_id")

    filters = {
        "q": request.args.get("q", ""),
        "status": request.args.get("status", "All"),
        "jurisdiction": request.args.get("jurisdiction", "All")
    }

    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("size", 20, type=int)
    sort_key = request.args.get("sort", "filing_date")
    sort_dir = request.args.get("dir", "desc")

    result = get_patents_list(filters, role, user_id, page=page, page_size=page_size, sort_key=sort_key, sort_dir=sort_dir)
    statuses = ["Filed", "Published", "Granted", "Rejected", "Lapsed"]
    jurisdictions = ["India", "USA", "EPO", "WIPO", "Other"]

    return render_template(
        "patents/list.html",
        patents=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
        filters=filters,
        statuses=statuses,
        jurisdictions=jurisdictions,
        sort_key=sort_key,
        sort_dir=sort_dir,
        role=role
    )

@patents_bp.route("/patents/<int:id>")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def detail(id: int):
    role = session.get("role")
    user_id = session.get("user_id")

    data = get_patent_detail(id, role, user_id)
    if not data:
        abort(404)

    return render_template("patents/detail.html", data=data, role=role)

@patents_bp.route("/patents/new", methods=["GET", "POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def new_patent():
    if request.method == "POST":
        app_num = request.form.get("application_number", "").strip()
        title = request.form.get("title", "").strip()
        jurisdiction = request.form.get("jurisdiction", "India").strip()
        filing_date = request.form.get("filing_date", "").strip()
        status = request.form.get("status", "Filed")
        patent_num = request.form.get("patent_number", "").strip() or None
        grant_date = request.form.get("grant_date", "").strip() or None

        inventor_ids = [int(i) for i in request.form.getlist("inventor_ids[]") if i]
        linked_project_ids = [int(p) for p in request.form.getlist("linked_project_ids[]") if p]

        try:
            pat_id = create_patent(
                app_num, title, jurisdiction, filing_date, status,
                patent_num, grant_date, inventor_ids, linked_project_ids
            )
            flash("Patent registered successfully.", "success")
            return redirect(url_for("patents.detail", id=pat_id))
        except Exception as e:
            flash(format_db_error(e), "danger")

    return render_template("patents/new.html")

@patents_bp.route("/patents/<int:id>/status", methods=["POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def change_status(id: int):
    status = request.form.get("status")
    patent_number = request.form.get("patent_number", "").strip() or None
    grant_date = request.form.get("grant_date", "").strip() or None

    try:
        update_patent_status(id, status, patent_number, grant_date)
        flash(f"Patent status updated to {status}.", "success")
    except Exception as e:
        flash(format_db_error(e), "danger")

    return redirect(url_for("patents.detail", id=id))
