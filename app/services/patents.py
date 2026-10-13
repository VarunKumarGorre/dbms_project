"""
RPGMS Patents Service
File: app/services/patents.py
Author: Antigravity AI

Handles patent directory, inventors repeater, project linkages,
status lifecycle transitions, and atomic patent creation.
Enforces role-based isolation:
- ADMIN / RESEARCH_OFFICER: Organization-wide access and write privileges.
- PI: Catalog view with unrelated project links redacted;
      can link existing patents only to own projects.
- VIEWER: No operational patent list access.
"""

from typing import Any, Dict, List, Optional
from app.db import run_query, run_transaction
from app.auth import get_pi_project_ids

ALLOWED_SORT_COLS = {
    "filing_date": "pat.filing_date",
    "title": "pat.title",
    "status": "pat.status",
    "app_num": "pat.application_number",
}

def get_patents_list(
    filters: Dict[str, Any],
    role: str,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    sort_key: str = "filing_date",
    sort_dir: str = "desc"
) -> Dict[str, Any]:
    """Retrieves paginated, role-scoped patent catalog."""
    is_pi = (role == "PI")
    pi_proj_ids = list(get_pi_project_ids(user_id)) if is_pi else []

    where_clauses = []
    params: List[Any] = []

    q = filters.get("q", "").strip()
    if q:
        where_clauses.append("(pat.title LIKE %s OR pat.application_number LIKE %s OR pat.patent_number LIKE %s)")
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard, wildcard])

    status = filters.get("status")
    if status and status != "All":
        where_clauses.append("pat.status = %s")
        params.append(status)

    jurisdiction = filters.get("jurisdiction")
    if jurisdiction and jurisdiction != "All":
        where_clauses.append("pat.jurisdiction = %s")
        params.append(jurisdiction)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Count
    count_sql = f"SELECT COUNT(*) AS total FROM patent AS pat {where_sql};"
    count_row = run_query(count_sql, params, fetchone=True)
    total_count = count_row["total"] if count_row else 0
    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

    offset = max(0, (page - 1) * page_size)
    direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
    sort_col = ALLOWED_SORT_COLS.get(sort_key.lower(), "pat.filing_date")

    data_sql = f"""
    SELECT
      pat.patent_id,
      pat.application_number,
      pat.patent_number,
      pat.title,
      pat.jurisdiction,
      pat.filing_date,
      pat.grant_date,
      pat.status
    FROM patent AS pat
    {where_sql}
    ORDER BY {sort_col} {direction}, pat.patent_id DESC
    LIMIT %s OFFSET %s;
    """
    query_params = list(params) + [page_size, offset]
    rows = run_query(data_sql, query_params)

    items = []
    for r in rows:
        pid = r["patent_id"]

        # Inventors
        sql_invs = """
        SELECT
          pi_inv.researcher_id,
          CONCAT(r.first_name, ' ', r.last_name) AS name,
          r.designation
        FROM patent_inventor AS pi_inv
        JOIN researcher AS r ON r.researcher_id = pi_inv.researcher_id
        WHERE pi_inv.patent_id = %s;
        """
        inventors = run_query(sql_invs, (pid,))

        # Scoped projects
        if is_pi:
            if pi_proj_ids:
                sql_proj = f"""
                SELECT p.project_id, p.project_code, p.title
                FROM project_patent AS pp
                JOIN project AS p ON p.project_id = pp.project_id
                WHERE pp.patent_id = %s AND p.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
                ORDER BY p.project_code ASC;
                """
                linked_projects = run_query(sql_proj, [pid] + pi_proj_ids)
            else:
                linked_projects = []
        else:
            sql_proj = """
            SELECT p.project_id, p.project_code, p.title
            FROM project_patent AS pp
            JOIN project AS p ON p.project_id = pp.project_id
            WHERE pp.patent_id = %s
            ORDER BY p.project_code ASC;
            """
            linked_projects = run_query(sql_proj, (pid,))

        items.append({
            "patent_id": pid,
            "application_number": r["application_number"],
            "patent_number": r["patent_number"],
            "title": r["title"],
            "jurisdiction": r["jurisdiction"],
            "filing_date": r["filing_date"],
            "grant_date": r["grant_date"],
            "status": r["status"],
            "inventors": inventors,
            "linked_projects": linked_projects
        })

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

def get_patent_detail(patent_id: int, role: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves single patent metadata, inventors, and scoped project links."""
    is_pi = (role == "PI")
    pi_proj_ids = list(get_pi_project_ids(user_id)) if is_pi else []

    sql = """
    SELECT
      patent_id, application_number, patent_number, title,
      jurisdiction, filing_date, grant_date, status
    FROM patent
    WHERE patent_id = %s;
    """
    pat = run_query(sql, (patent_id,), fetchone=True)
    if not pat:
        return None

    # Inventors
    sql_invs = """
    SELECT
      pi_inv.researcher_id,
      CONCAT(r.first_name, ' ', r.last_name) AS name,
      r.email, r.orcid_id AS orcid,
      d.dept_name, r.designation
    FROM patent_inventor AS pi_inv
    JOIN researcher AS r ON r.researcher_id = pi_inv.researcher_id
    JOIN department AS d ON d.dept_id = r.dept_id
    WHERE pi_inv.patent_id = %s;
    """
    inventors = run_query(sql_invs, (patent_id,))

    # Scoped projects
    if is_pi:
        if pi_proj_ids:
            sql_proj = f"""
            SELECT p.project_id, p.project_code, p.title, p.status
            FROM project_patent AS pp
            JOIN project AS p ON p.project_id = pp.project_id
            WHERE pp.patent_id = %s AND p.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
            ORDER BY p.project_code ASC;
            """
            projects = run_query(sql_proj, [patent_id] + pi_proj_ids)
        else:
            projects = []
    else:
        sql_proj = """
        SELECT p.project_id, p.project_code, p.title, p.status
        FROM project_patent AS pp
        JOIN project AS p ON p.project_id = pp.project_id
        WHERE pp.patent_id = %s
        ORDER BY p.project_code ASC;
        """
        projects = run_query(sql_proj, (patent_id,))

    return {
        "patent": pat,
        "inventors": inventors,
        "linked_projects": projects
    }

def create_patent(
    app_number: str,
    title: str,
    jurisdiction: str,
    filing_date: str,
    status: str,
    patent_number: Optional[str],
    grant_date: Optional[str],
    inventor_ids: List[int],
    linked_project_ids: List[int]
) -> int:
    """
    Atomically creates patent, inventor entries, and project linkages.
    Enforces BR-14 (chk_pat_dates, chk_pat_status).
    """
    if status == "Granted":
        if not patent_number or not grant_date:
            raise ValueError("BR-14: A granted patent needs a valid patent number and grant date")
    else:
        patent_number = None
        grant_date = None

    with run_transaction() as cursor:
        cursor.execute("""
            INSERT INTO patent (
              application_number, patent_number, title, jurisdiction,
              filing_date, grant_date, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (
            app_number.strip(),
            patent_number.strip() if patent_number else None,
            title.strip(),
            jurisdiction.strip() if jurisdiction else "India",
            filing_date,
            grant_date,
            status
        ))
        cursor.execute("SELECT LAST_INSERT_ID() AS id;")
        pat_id = cursor.fetchone()["id"]

        for res_id in set(inventor_ids):
            cursor.execute("""
                INSERT INTO patent_inventor (patent_id, researcher_id)
                VALUES (%s, %s);
            """, (pat_id, int(res_id)))

        for proj_id in set(linked_project_ids):
            cursor.execute("""
                INSERT INTO project_patent (project_id, patent_id)
                VALUES (%s, %s);
            """, (int(proj_id), pat_id))

        return pat_id

def update_patent_status(
    patent_id: int,
    new_status: str,
    patent_number: Optional[str] = None,
    grant_date: Optional[str] = None
):
    """Updates patent status and validates grant credentials under BR-14."""
    if new_status == "Granted":
        if not patent_number or not grant_date:
            raise ValueError("BR-14: A granted patent needs a valid patent number and grant date")
    else:
        patent_number = None
        grant_date = None

    with run_transaction() as cursor:
        cursor.execute("""
            UPDATE patent
            SET status = %s,
                patent_number = %s,
                grant_date = %s
            WHERE patent_id = %s;
        """, (new_status, patent_number, grant_date, patent_id))

def search_patents_for_linking(
    query: str,
    target_project_id: int,
    role: str,
    user_id: int
) -> List[Dict[str, Any]]:
    """
    Search patents catalogue to link to target project.
    Strictly redacts unrelated project links.
    """
    sql = """
    SELECT
      pat.patent_id,
      pat.title,
      pat.application_number,
      pat.patent_number,
      pat.filing_date,
      pat.status,
      (EXISTS (
        SELECT 1 FROM project_patent AS pp
        WHERE pp.patent_id = pat.patent_id AND pp.project_id = %s
      )) AS already_linked
    FROM patent AS pat
    WHERE pat.title LIKE %s OR pat.application_number LIKE %s
    ORDER BY pat.filing_date DESC
    LIMIT 10;
    """
    wildcard = f"%{query.strip()}%"
    rows = run_query(sql, (target_project_id, wildcard, wildcard))
    results = []
    for r in rows:
        results.append({
            "id": r["patent_id"],
            "title": r["title"],
            "app_num": r["application_number"],
            "patent_number": r["patent_number"],
            "date": r["filing_date"].isoformat() if hasattr(r["filing_date"], "isoformat") else str(r["filing_date"]),
            "status": r["status"],
            "already_linked_to_target": bool(r["already_linked"])
        })
    return results
