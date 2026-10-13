"""
RPGMS Live API Endpoints Blueprint
File: app/blueprints/api.py
Author: Antigravity AI

Provides small JSON endpoints for interactive typeaheads, budget checks,
validation guards, and global search.
Enforces role-based isolation:
- Global search: ADMIN, RESEARCH_OFFICER, PI (scoped). VIEWER rejected (403).
- Catalog pickers: Redact unrelated project links.
- Procedure helpers: Role-protected.
"""

from flask import Blueprint, jsonify, request, session, abort
from app.auth import require_login, get_pi_project_ids, can_access_project, can_access_grant
from app.db import run_query
from app.services.investigators import get_researcher_workload_api
from app.services.grants import get_grant_heads_api
from app.services.publications import search_publications_for_linking
from app.services.patents import search_patents_for_linking
from app.services.milestones import get_overdue_milestones_count

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/search")
@require_login
def global_search():
    role = session.get("role")
    user_id = session.get("user_id")

    # VIEWER has no record-level search
    if role == "VIEWER":
        abort(403)

    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify({
            "projects": [], "researchers": [], "grants": [],
            "publications": [], "patents": [], "milestones": []
        })

    wildcard = f"%{q}%"
    is_pi = (role == "PI")
    pi_proj_ids = list(get_pi_project_ids(user_id)) if is_pi else []

    # 1. Projects
    if is_pi:
        if not pi_proj_ids:
            projects = []
        else:
            sql_p = f"""
            SELECT project_id AS id, project_code AS code, title, status
            FROM project
            WHERE (project_code LIKE %s OR title LIKE %s)
              AND project_id IN ({','.join(['%s']*len(pi_proj_ids))})
            LIMIT 5;
            """
            projects = run_query(sql_p, [wildcard, wildcard] + pi_proj_ids)
    else:
        sql_p = """
        SELECT project_id AS id, project_code AS code, title, status
        FROM project
        WHERE project_code LIKE %s OR title LIKE %s
        LIMIT 5;
        """
        projects = run_query(sql_p, (wildcard, wildcard))

    # 2. Researchers
    if is_pi:
        if not pi_proj_ids:
            researchers = []
        else:
            sql_r = f"""
            SELECT DISTINCT r.researcher_id AS id, CONCAT(r.first_name, ' ', r.last_name) AS name, d.dept_code AS dept
            FROM researcher AS r
            JOIN department AS d ON d.dept_id = r.dept_id
            JOIN project_investigator AS pi ON pi.researcher_id = r.researcher_id
            WHERE (CONCAT(r.first_name, ' ', r.last_name) LIKE %s OR r.email LIKE %s OR r.orcid_id LIKE %s)
              AND pi.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
            LIMIT 5;
            """
            researchers = run_query(sql_r, [wildcard, wildcard, wildcard] + pi_proj_ids)
    else:
        sql_r = """
        SELECT r.researcher_id AS id, CONCAT(r.first_name, ' ', r.last_name) AS name, d.dept_code AS dept
        FROM researcher AS r
        JOIN department AS d ON d.dept_id = r.dept_id
        WHERE CONCAT(r.first_name, ' ', r.last_name) LIKE %s OR r.email LIKE %s OR r.orcid_id LIKE %s
        LIMIT 5;
        """
        researchers = run_query(sql_r, (wildcard, wildcard, wildcard))

    # 3. Grants
    if is_pi:
        if not pi_proj_ids:
            grants = []
        else:
            sql_g = f"""
            SELECT ga.grant_id AS id, ga.grant_number, p.project_code, fa.agency_name AS agency_code
            FROM grant_award AS ga
            JOIN project AS p ON p.project_id = ga.project_id
            JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
            WHERE (ga.grant_number LIKE %s OR fa.agency_name LIKE %s)
              AND ga.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
            LIMIT 5;
            """
            grants = run_query(sql_g, [wildcard, wildcard] + pi_proj_ids)
    else:
        sql_g = """
        SELECT ga.grant_id AS id, ga.grant_number, p.project_code, fa.agency_name AS agency_code
        FROM grant_award AS ga
        JOIN project AS p ON p.project_id = ga.project_id
        JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
        WHERE ga.grant_number LIKE %s OR fa.agency_name LIKE %s OR p.project_code LIKE %s
        LIMIT 5;
        """
        grants = run_query(sql_g, (wildcard, wildcard, wildcard))

    # 4. Publications
    sql_pub = """
    SELECT publication_id AS id, title, venue, pub_date AS date, doi
    FROM publication
    WHERE title LIKE %s OR doi LIKE %s
    LIMIT 5;
    """
    publications = run_query(sql_pub, (wildcard, wildcard))

    # 5. Patents
    sql_pat = """
    SELECT patent_id AS id, title, application_number AS app_num, status
    FROM patent
    WHERE title LIKE %s OR application_number LIKE %s
    LIMIT 5;
    """
    patents = run_query(sql_pat, (wildcard, wildcard))

    # 6. Milestones
    if is_pi:
        if not pi_proj_ids:
            milestones = []
        else:
            sql_m = f"""
            SELECT m.milestone_id AS id, m.title, p.project_code, m.due_date, m.status
            FROM milestone AS m
            JOIN project AS p ON p.project_id = m.project_id
            WHERE m.title LIKE %s AND m.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
            LIMIT 5;
            """
            milestones = run_query(sql_m, [wildcard] + pi_proj_ids)
    else:
        sql_m = """
        SELECT m.milestone_id AS id, m.title, p.project_code, m.due_date, m.status
        FROM milestone AS m
        JOIN project AS p ON p.project_id = m.project_id
        WHERE m.title LIKE %s OR p.project_code LIKE %s
        LIMIT 5;
        """
        milestones = run_query(sql_m, (wildcard, wildcard))

    return jsonify({
        "projects": projects,
        "researchers": researchers,
        "grants": grants,
        "publications": publications,
        "patents": patents,
        "milestones": milestones
    })

@api_bp.route("/researchers/search")
@require_login
def search_researchers():
    role = session.get("role")
    if role not in ("ADMIN", "RESEARCH_OFFICER"):
        abort(403)

    q = request.args.get("q", "").strip()
    active_only = request.args.get("active", "1") == "1"

    sql = """
    SELECT r.researcher_id AS id, CONCAT(r.first_name, ' ', r.last_name) AS name,
           d.dept_name AS dept, r.designation, r.is_active
    FROM researcher AS r
    JOIN department AS d ON d.dept_id = r.dept_id
    WHERE (CONCAT(r.first_name, ' ', r.last_name) LIKE %s OR r.email LIKE %s)
    """
    params = [f"%{q}%", f"%{q}%"]
    if active_only:
        sql += " AND r.is_active = TRUE"
    sql += " ORDER BY r.last_name ASC LIMIT 10;"

    rows = run_query(sql, params)
    return jsonify(rows)

@api_bp.route("/projects/search")
@require_login
def search_projects():
    role = session.get("role")
    user_id = session.get("user_id")

    if role == "VIEWER":
        abort(403)

    q = request.args.get("q", "").strip()
    wildcard = f"%{q}%"

    if role == "PI":
        pids = list(get_pi_project_ids(user_id))
        if not pids:
            return jsonify([])
        sql = f"""
        SELECT project_id AS id, project_code AS code, title, start_date AS start, end_date AS end, status
        FROM project
        WHERE (project_code LIKE %s OR title LIKE %s)
          AND project_id IN ({','.join(['%s']*len(pids))})
        ORDER BY project_code ASC LIMIT 10;
        """
        rows = run_query(sql, [wildcard, wildcard] + pids)
    else:
        sql = """
        SELECT project_id AS id, project_code AS code, title, start_date AS start, end_date AS end, status
        FROM project
        WHERE project_code LIKE %s OR title LIKE %s
        ORDER BY project_code ASC LIMIT 10;
        """
        rows = run_query(sql, (wildcard, wildcard))

    return jsonify(rows)

@api_bp.route("/projects/code-exists")
@require_login
def check_project_code():
    role = session.get("role")
    if role not in ("ADMIN", "RESEARCH_OFFICER"):
        abort(403)

    code = request.args.get("code", "").strip()
    if not code:
        return jsonify({"exists": False})

    row = run_query("SELECT 1 FROM project WHERE project_code = %s LIMIT 1;", (code,), fetchone=True)
    return jsonify({"exists": bool(row)})

@api_bp.route("/researchers/<int:id>/workload")
@require_login
def researcher_workload(id: int):
    role = session.get("role")
    if role not in ("ADMIN", "RESEARCH_OFFICER"):
        abort(403)

    data = get_researcher_workload_api(id)
    return jsonify(data)

@api_bp.route("/grants/search")
@require_login
def search_grants():
    role = session.get("role")
    if role not in ("ADMIN", "RESEARCH_OFFICER"):
        abort(403)

    q = request.args.get("q", "").strip()
    wildcard = f"%{q}%"
    sql = """
    SELECT ga.grant_id AS id, ga.grant_number, p.project_code, fa.agency_name AS agency
    FROM grant_award AS ga
    JOIN project AS p ON p.project_id = ga.project_id
    JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
    WHERE ga.status = 'Active' AND p.status IN ('Proposed', 'Active')
      AND (ga.grant_number LIKE %s OR p.project_code LIKE %s OR fa.agency_name LIKE %s)
    ORDER BY ga.grant_number ASC LIMIT 10;
    """
    rows = run_query(sql, (wildcard, wildcard, wildcard))
    return jsonify(rows)

@api_bp.route("/grants/<int:id>/heads")
@require_login
def grant_heads(id: int):
    role = session.get("role")
    user_id = session.get("user_id")

    if not can_access_grant(id):
        abort(403)

    data = get_grant_heads_api(id, role, user_id)
    if not data:
        abort(404)
    return jsonify(data)

@api_bp.route("/doi-exists")
@require_login
def check_doi():
    role = session.get("role")
    if role not in ("ADMIN", "RESEARCH_OFFICER"):
        abort(403)

    doi = request.args.get("doi", "").strip()
    if not doi:
        return jsonify({"exists": False})

    row = run_query("SELECT 1 FROM publication WHERE doi = %s LIMIT 1;", (doi,), fetchone=True)
    return jsonify({"exists": bool(row)})

@api_bp.route("/publications/search")
@require_login
def search_pubs_link():
    role = session.get("role")
    user_id = session.get("user_id")
    target_project_id = request.args.get("project_id", type=int)

    if not target_project_id or not can_access_project(target_project_id):
        abort(403)

    q = request.args.get("q", "").strip()
    results = search_publications_for_linking(q, target_project_id, role, user_id)
    return jsonify(results)

@api_bp.route("/patents/search")
@require_login
def search_pats_link():
    role = session.get("role")
    user_id = session.get("user_id")
    target_project_id = request.args.get("project_id", type=int)

    if not target_project_id or not can_access_project(target_project_id):
        abort(403)

    q = request.args.get("q", "").strip()
    results = search_patents_for_linking(q, target_project_id, role, user_id)
    return jsonify(results)

@api_bp.route("/notifications/count")
@require_login
def notifications_count():
    role = session.get("role")
    user_id = session.get("user_id")
    count = get_overdue_milestones_count(role, user_id)
    return jsonify({"overdue": count})
