"""
RPGMS Investigators Service
File: app/services/investigators.py
Author: Antigravity AI

Handles researcher directory queries, workload calculations, profile details,
and researcher creation/editing.
Enforces role-based isolation:
- ADMIN / RESEARCH_OFFICER: Organization-wide access and workload calculation.
- PI: Access strictly limited to investigators associated with own projects;
      PIs receive no global workload totals.
- VIEWER: No operational investigator list access.
"""

from typing import Any, Dict, List, Optional
from app.db import run_query, run_transaction
from app.auth import get_pi_project_ids

ALLOWED_SORT_COLS = {
    "name": "r.last_name, r.first_name",
    "dept": "d.dept_code",
    "designation": "r.designation",
    "workload": "workload_percent",
    "projects": "active_projects_count",
}

def get_investigators_list(
    filters: Dict[str, Any],
    role: str,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    sort_key: str = "name",
    sort_dir: str = "asc"
) -> Dict[str, Any]:
    """Retrieves paginated, role-scoped list of investigators."""
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

    # PI scoping: only researchers on PI's projects
    if is_pi:
        placeholders = ",".join(["%s"] * len(pi_proj_ids))
        where_clauses.append(f"""
            r.researcher_id IN (
                SELECT DISTINCT researcher_id
                FROM project_investigator
                WHERE project_id IN ({placeholders})
            )
        """)
        params.extend(pi_proj_ids)

    q = filters.get("q", "").strip()
    if q:
        where_clauses.append("(CONCAT(r.first_name, ' ', r.last_name) LIKE %s OR r.email LIKE %s OR r.orcid_id LIKE %s)")
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard, wildcard])

    dept_id = filters.get("dept_id")
    if dept_id:
        try:
            where_clauses.append("r.dept_id = %s")
            params.append(int(dept_id))
        except ValueError:
            pass

    designation = filters.get("designation")
    if designation and designation != "All":
        where_clauses.append("r.designation = %s")
        params.append(designation)

    if filters.get("active_only"):
        where_clauses.append("r.is_active = TRUE")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Count total
    count_sql = f"""
    SELECT COUNT(*) AS total
    FROM researcher AS r
    JOIN department AS d ON d.dept_id = r.dept_id
    {where_sql};
    """
    count_row = run_query(count_sql, params, fetchone=True)
    total_count = count_row["total"] if count_row else 0
    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

    offset = max(0, (page - 1) * page_size)
    direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
    sort_col = ALLOWED_SORT_COLS.get(sort_key.lower(), "r.last_name, r.first_name")

    # Main query
    # Notice: for PI, workload calculation is strictly scoped to own projects
    if is_pi:
        data_sql = f"""
        SELECT
          r.researcher_id,
          r.first_name,
          r.last_name,
          CONCAT(r.first_name, ' ', r.last_name) AS full_name,
          r.email,
          r.phone,
          r.orcid_id AS orcid,
          r.designation,
          r.is_active,
          d.dept_id,
          d.dept_name,
          d.dept_code,
          COALESCE(proj_agg.active_projects_count, 0) AS active_projects_count,
          COALESCE(proj_agg.scoped_effort, 0.0) AS workload_percent,
          COALESCE(pub_agg.pubs_count, 0) AS pubs_count,
          COALESCE(pat_agg.patents_count, 0) AS patents_count
        FROM researcher AS r
        JOIN department AS d ON d.dept_id = r.dept_id
        LEFT JOIN (
          SELECT
            pi.researcher_id,
            COUNT(DISTINCT pi.project_id) AS active_projects_count,
            SUM(pi.effort_percent) AS scoped_effort
          FROM project_investigator AS pi
          JOIN project AS p ON p.project_id = pi.project_id
          WHERE p.status IN ('Proposed', 'Active')
            AND p.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
          GROUP BY pi.researcher_id
        ) AS proj_agg ON proj_agg.researcher_id = r.researcher_id
        LEFT JOIN (
          SELECT pa.researcher_id, COUNT(DISTINCT pa.publication_id) AS pubs_count
          FROM publication_author AS pa
          JOIN project_publication AS pp ON pp.publication_id = pa.publication_id
          WHERE pp.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
          GROUP BY pa.researcher_id
        ) AS pub_agg ON pub_agg.researcher_id = r.researcher_id
        LEFT JOIN (
          SELECT p_inv.researcher_id, COUNT(DISTINCT p_inv.patent_id) AS patents_count
          FROM patent_inventor AS p_inv
          JOIN project_patent AS pp ON pp.patent_id = p_inv.patent_id
          WHERE pp.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
          GROUP BY p_inv.researcher_id
        ) AS pat_agg ON pat_agg.researcher_id = r.researcher_id
        {where_sql}
        ORDER BY {sort_col} {direction}
        LIMIT %s OFFSET %s;
        """
        query_params = list(pi_proj_ids) + list(pi_proj_ids) + list(pi_proj_ids) + list(params) + [page_size, offset]
    else:
        data_sql = f"""
        SELECT
          r.researcher_id,
          r.first_name,
          r.last_name,
          CONCAT(r.first_name, ' ', r.last_name) AS full_name,
          r.email,
          r.phone,
          r.orcid_id AS orcid,
          r.designation,
          r.is_active,
          d.dept_id,
          d.dept_name,
          d.dept_code,
          COALESCE(proj_agg.active_projects_count, 0) AS active_projects_count,
          COALESCE(proj_agg.total_effort, 0.0) AS workload_percent,
          COALESCE(pub_agg.pubs_count, 0) AS pubs_count,
          COALESCE(pat_agg.patents_count, 0) AS patents_count
        FROM researcher AS r
        JOIN department AS d ON d.dept_id = r.dept_id
        LEFT JOIN (
          SELECT
            pi.researcher_id,
            COUNT(DISTINCT pi.project_id) AS active_projects_count,
            SUM(pi.effort_percent) AS total_effort
          FROM project_investigator AS pi
          JOIN project AS p ON p.project_id = pi.project_id
          WHERE p.status IN ('Proposed', 'Active')
          GROUP BY pi.researcher_id
        ) AS proj_agg ON proj_agg.researcher_id = r.researcher_id
        LEFT JOIN (
          SELECT researcher_id, COUNT(DISTINCT publication_id) AS pubs_count
          FROM publication_author
          GROUP BY researcher_id
        ) AS pub_agg ON pub_agg.researcher_id = r.researcher_id
        LEFT JOIN (
          SELECT researcher_id, COUNT(DISTINCT patent_id) AS patents_count
          FROM patent_inventor
          GROUP BY researcher_id
        ) AS pat_agg ON pat_agg.researcher_id = r.researcher_id
        {where_sql}
        ORDER BY {sort_col} {direction}
        LIMIT %s OFFSET %s;
        """
        query_params = list(params) + [page_size, offset]

    items = run_query(data_sql, query_params)
    for it in items:
        it["workload_percent"] = float(it["workload_percent"] or 0.0)

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

def get_investigator_detail(researcher_id: int, role: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves single investigator profile, projects, and outputs."""
    is_pi = (role == "PI")
    pi_proj_ids = list(get_pi_project_ids(user_id)) if is_pi else []

    if is_pi:
        # Check if researcher is associated with any PI project
        chk_sql = f"""
        SELECT 1
        FROM project_investigator
        WHERE researcher_id = %s AND project_id IN ({','.join(['%s']*len(pi_proj_ids))})
        LIMIT 1;
        """
        if not pi_proj_ids or not run_query(chk_sql, [researcher_id] + pi_proj_ids, fetchone=True):
            return None

    # Base profile
    sql_base = """
    SELECT
      r.researcher_id, r.first_name, r.last_name,
      CONCAT(r.first_name, ' ', r.last_name) AS full_name,
      r.email, r.phone, r.orcid_id AS orcid, r.designation, r.is_active,
      d.dept_id, d.dept_name, d.dept_code
    FROM researcher AS r
    JOIN department AS d ON d.dept_id = r.dept_id
    WHERE r.researcher_id = %s;
    """
    res = run_query(sql_base, (researcher_id,), fetchone=True)
    if not res:
        return None

    # Assigned projects
    if is_pi:
        sql_proj = f"""
        SELECT
          p.project_id, p.project_code, p.title, p.status,
          pi.role, pi.effort_percent, pi.assigned_date
        FROM project_investigator AS pi
        JOIN project AS p ON p.project_id = pi.project_id
        WHERE pi.researcher_id = %s AND p.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
        ORDER BY (pi.role = 'PI') DESC, p.start_date DESC;
        """
        projects = run_query(sql_proj, [researcher_id] + pi_proj_ids)
    else:
        sql_proj = """
        SELECT
          p.project_id, p.project_code, p.title, p.status,
          pi.role, pi.effort_percent, pi.assigned_date
        FROM project_investigator AS pi
        JOIN project AS p ON p.project_id = pi.project_id
        WHERE pi.researcher_id = %s
        ORDER BY (p.status IN ('Proposed', 'Active')) DESC, (pi.role = 'PI') DESC, p.start_date DESC;
        """
        projects = run_query(sql_proj, (researcher_id,))

    # Workload percent
    if is_pi:
        workload = sum(float(p["effort_percent"]) for p in projects if p["status"] in ("Proposed", "Active"))
    else:
        sql_wl = """
        SELECT COALESCE(SUM(pi.effort_percent), 0.0) AS workload
        FROM project_investigator AS pi
        JOIN project AS p ON p.project_id = pi.project_id
        WHERE pi.researcher_id = %s AND p.status IN ('Proposed', 'Active');
        """
        wl_row = run_query(sql_wl, (researcher_id,), fetchone=True)
        workload = float(wl_row["workload"] or 0.0) if wl_row else 0.0

    # Linked publications
    if is_pi:
        sql_pubs = f"""
        SELECT DISTINCT
          pub.publication_id, pub.title, pub.pub_type AS publication_type, pub.venue,
          pub.pub_date AS publication_date, pub.doi, pub.indexing, pa.is_corresponding, pa.author_order
        FROM publication_author AS pa
        JOIN publication AS pub ON pub.publication_id = pa.publication_id
        JOIN project_publication AS pp ON pp.publication_id = pub.publication_id
        WHERE pa.researcher_id = %s AND pp.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
        ORDER BY pub.pub_date DESC;
        """
        publications = run_query(sql_pubs, [researcher_id] + pi_proj_ids)
    else:
        sql_pubs = """
        SELECT
          pub.publication_id, pub.title, pub.pub_type AS publication_type, pub.venue,
          pub.pub_date AS publication_date, pub.doi, pub.indexing, pa.is_corresponding, pa.author_order
        FROM publication_author AS pa
        JOIN publication AS pub ON pub.publication_id = pa.publication_id
        WHERE pa.researcher_id = %s
        ORDER BY pub.pub_date DESC;
        """
        publications = run_query(sql_pubs, (researcher_id,))

    # Linked patents
    if is_pi:
        sql_pats = f"""
        SELECT DISTINCT
          pat.patent_id, pat.title, pat.application_number, pat.patent_number,
          pat.jurisdiction, pat.filing_date, pat.grant_date, pat.status
        FROM patent_inventor AS pi_inv
        JOIN patent AS pat ON pat.patent_id = pi_inv.patent_id
        JOIN project_patent AS pp ON pp.patent_id = pat.patent_id
        WHERE pi_inv.researcher_id = %s AND pp.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
        ORDER BY pat.filing_date DESC;
        """
        patents = run_query(sql_pats, [researcher_id] + pi_proj_ids)
    else:
        sql_pats = """
        SELECT
          pat.patent_id, pat.title, pat.application_number, pat.patent_number,
          pat.jurisdiction, pat.filing_date, pat.grant_date, pat.status
        FROM patent_inventor AS pi_inv
        JOIN patent AS pat ON pat.patent_id = pi_inv.patent_id
        WHERE pi_inv.researcher_id = %s
        ORDER BY pat.filing_date DESC;
        """
        patents = run_query(sql_pats, (researcher_id,))

    return {
        "researcher": res,
        "workload_percent": workload,
        "projects": projects,
        "publications": publications,
        "patents": patents
    }

def get_my_workload(user_id: int) -> Dict[str, Any]:
    """Retrieves personal workload breakdown for a PI user across own projects."""
    pi_proj_ids = list(get_pi_project_ids(user_id))
    if not pi_proj_ids:
        return {"total_workload": 0.0, "projects": []}

    sql = f"""
    SELECT
      p.project_id, p.project_code, p.title, p.status,
      pi.role, pi.effort_percent, pi.assigned_date,
      p.start_date, p.end_date
    FROM project_investigator AS pi
    JOIN project AS p ON p.project_id = pi.project_id
    JOIN user_account AS u ON u.researcher_id = pi.researcher_id
    WHERE u.user_id = %s AND p.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
    ORDER BY (p.status = 'Active') DESC, p.start_date DESC;
    """
    params = [user_id] + pi_proj_ids
    projects = run_query(sql, params)
    total_wl = sum(float(p["effort_percent"]) for p in projects if p["status"] in ("Proposed", "Active"))

    return {
        "total_workload": round(total_wl, 1),
        "projects": projects
    }

def get_researcher_workload_api(researcher_id: int) -> Dict[str, Any]:
    """Returns workload percentage and active projects for the assign modal API."""
    sql = """
    SELECT
      p.project_id, p.project_code, p.title, p.status, pi.effort_percent, pi.role
    FROM project_investigator AS pi
    JOIN project AS p ON p.project_id = pi.project_id
    WHERE pi.researcher_id = %s AND p.status IN ('Proposed', 'Active');
    """
    rows = run_query(sql, (researcher_id,))
    total_effort = sum(float(r["effort_percent"]) for r in rows)
    return {
        "current_percent": round(total_effort, 1),
        "projects": rows
    }

def create_researcher(data: Dict[str, Any]) -> int:
    """Inserts a new researcher."""
    sql = """
    INSERT INTO researcher (
      first_name, last_name, email, phone, orcid, designation, dept_id, is_active
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    with run_transaction() as cursor:
        cursor.execute(sql, (
            data["first_name"].strip(),
            data["last_name"].strip(),
            data["email"].strip().lower(),
            data.get("phone", "").strip() or None,
            data.get("orcid", "").strip() or None,
            data["designation"],
            int(data["dept_id"]),
            bool(data.get("is_active", True))
        ))
        cursor.execute("SELECT LAST_INSERT_ID() AS id;")
        row = cursor.fetchone()
        return row["id"]

def update_researcher(researcher_id: int, data: Dict[str, Any]):
    """Updates an existing researcher."""
    sql = """
    UPDATE researcher
    SET first_name = %s,
        last_name = %s,
        email = %s,
        phone = %s,
        orcid = %s,
        designation = %s,
        dept_id = %s,
        is_active = %s
    WHERE researcher_id = %s;
    """
    with run_transaction() as cursor:
        cursor.execute(sql, (
            data["first_name"].strip(),
            data["last_name"].strip(),
            data["email"].strip().lower(),
            data.get("phone", "").strip() or None,
            data.get("orcid", "").strip() or None,
            data["designation"],
            int(data["dept_id"]),
            bool(data.get("is_active", True)),
            researcher_id
        ))
