"""
RPGMS Publications Blueprint
File: app/blueprints/publications.py
Author: Antigravity AI
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from app.auth import require_role
from app.services.publications import (
    get_publications_list, get_publication_detail, create_publication
)
from app.errors import format_db_error
from app.db import run_query

publications_bp = Blueprint("publications", __name__)

@publications_bp.route("/publications")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def index():
    role = session.get("role")
    user_id = session.get("user_id")

    filters = {
        "q": request.args.get("q", ""),
        "year": request.args.get("year", ""),
        "type": request.args.get("type", "All"),
        "indexing": request.args.get("indexing", "All"),
        "dept_id": request.args.get("dept_id", "")
    }

    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("size", 20, type=int)
    sort_key = request.args.get("sort", "date")
    sort_dir = request.args.get("dir", "desc")

    result = get_publications_list(filters, role, user_id, page=page, page_size=page_size, sort_key=sort_key, sort_dir=sort_dir)
    departments = run_query("SELECT dept_id, dept_name, dept_code FROM department ORDER BY dept_name ASC;")
    years = run_query("SELECT DISTINCT YEAR(pub_date) AS yr FROM publication ORDER BY yr DESC;")

    return render_template(
        "publications/list.html",
        publications=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
        filters=filters,
        departments=departments,
        years=[y["yr"] for y in years if y["yr"]],
        sort_key=sort_key,
        sort_dir=sort_dir,
        role=role
    )

@publications_bp.route("/publications/<int:id>")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI"])
def detail(id: int):
    role = session.get("role")
    user_id = session.get("user_id")

    data = get_publication_detail(id, role, user_id)
    if not data:
        abort(404)

    return render_template("publications/detail.html", data=data, role=role)

@publications_bp.route("/publications/new", methods=["GET", "POST"])
@require_role(["ADMIN", "RESEARCH_OFFICER"])
def new_publication():
    preselected_project_id = request.args.get("project_id", type=int)
    project_info = None
    if preselected_project_id:
        project_info = run_query(
            "SELECT project_id, project_code, title, start_date FROM project WHERE project_id = %s;",
            (preselected_project_id,),
            fetchone=True
        )

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        pub_type = request.form.get("publication_type", "Journal")
        venue = request.form.get("venue", "").strip()
        pub_date = request.form.get("publication_date", "").strip()
        doi = request.form.get("doi", "").strip() or None
        indexing = request.form.get("indexing", "None")
        issn_isbn = request.form.get("issn_isbn", "").strip() or None

        # Parse authors repeater
        author_ids = request.form.getlist("author_ids[]")
        corr_ids = request.form.getlist("is_corresponding[]")
        authors = []
        for idx, aid in enumerate(author_ids):
            if aid:
                try:
                    res_id = int(aid)
                    is_corr = str(res_id) in corr_ids or str(idx + 1) in corr_ids
                    authors.append({"researcher_id": res_id, "is_corresponding": is_corr})
                except ValueError:
                    pass

        # Linked projects
        proj_ids = [int(p) for p in request.form.getlist("linked_project_ids[]") if p]

        try:
            pub_id = create_publication(
                title, pub_type, venue, pub_date, doi, indexing, issn_isbn,
                authors, proj_ids
            )
            flash("Publication recorded successfully.", "success")
            return redirect(url_for("publications.detail", id=pub_id))
        except Exception as e:
            flash(format_db_error(e), "danger")

    return render_template(
        "publications/new.html",
        preselected_project=project_info
    )
