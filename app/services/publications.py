"""
RPGMS Publications Service
File: app/services/publications.py
Author: Antigravity AI

Handles publication catalog searches, author associations, project linkages,
and atomic publication creation.
Enforces role-based isolation:
- ADMIN / RESEARCH_OFFICER: Organization-wide access and write privileges.
- PI: Catalog view with unrelated project links redacted;
      can link existing publications only to own projects.
- VIEWER: No operational publication list access.
"""

from typing import Any, Dict, List, Optional
from app.db import run_query, run_transaction
from app.auth import get_pi_project_ids

ALLOWED_SORT_COLS = {
    "date": "p.pub_date",
    "title": "p.title",
    "year": "YEAR(p.pub_date)",
    "type": "p.pub_type",
}

def get_publications_list(
    filters: Dict[str, Any],
    role: str,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    sort_key: str = "date",
    sort_dir: str = "desc"
) -> Dict[str, Any]:
    """Retrieves paginated, role-scoped publication catalog."""
    is_pi = (role == "PI")
    pi_proj_ids = list(get_pi_project_ids(user_id)) if is_pi else []

    where_clauses = []
    params: List[Any] = []

    q = filters.get("q", "").strip()
    if q:
        where_clauses.append("(p.title LIKE %s OR p.doi LIKE %s OR p.venue LIKE %s)")
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard, wildcard])

    year = filters.get("year")
    if year:
        try:
            where_clauses.append("YEAR(p.pub_date) = %s")
            params.append(int(year))
        except ValueError:
            pass

    pub_type = filters.get("type")
    if pub_type and pub_type != "All":
        where_clauses.append("p.pub_type = %s")
        params.append(pub_type)

    indexing = filters.get("indexing")
    if indexing and indexing != "All":
        where_clauses.append("p.indexing = %s")
        params.append(indexing)

    dept_id = filters.get("dept_id")
    if dept_id:
        try:
            where_clauses.append("""
                p.publication_id IN (
                    SELECT pa.publication_id
                    FROM publication_author AS pa
                    JOIN researcher AS r ON r.researcher_id = pa.researcher_id
                    WHERE r.dept_id = %s
                )
            """)
            params.append(int(dept_id))
        except ValueError:
            pass

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Count
    count_sql = f"SELECT COUNT(*) AS total FROM publication AS p {where_sql};"
    count_row = run_query(count_sql, params, fetchone=True)
    total_count = count_row["total"] if count_row else 0
    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

    offset = max(0, (page - 1) * page_size)
    direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
    sort_col = ALLOWED_SORT_COLS.get(sort_key.lower(), "p.pub_date")

    data_sql = f"""
    SELECT
      p.publication_id,
      p.title,
      p.pub_type AS publication_type,
      p.venue,
      p.pub_date AS publication_date,
      p.doi,
      p.indexing,
      p.issn_isbn
    FROM publication AS p
    {where_sql}
    ORDER BY {sort_col} {direction}, p.publication_id DESC
    LIMIT %s OFFSET %s;
    """
    query_params = list(params) + [page_size, offset]
    rows = run_query(data_sql, query_params)

    items = []
    for r in rows:
        pid = r["publication_id"]

        # Authors
        sql_authors = """
        SELECT
          pa.researcher_id,
          CONCAT(r.first_name, ' ', r.last_name) AS name,
          pa.is_corresponding,
          pa.author_order
        FROM publication_author AS pa
        JOIN researcher AS r ON r.researcher_id = pa.researcher_id
        WHERE pa.publication_id = %s
        ORDER BY pa.author_order ASC;
        """
        authors = run_query(sql_authors, (pid,))

        # Linked projects (scoped: PI only sees own-project affiliations)
        if is_pi:
            if pi_proj_ids:
                sql_proj = f"""
                SELECT p.project_id, p.project_code, p.title
                FROM project_publication AS pp
                JOIN project AS p ON p.project_id = pp.project_id
                WHERE pp.publication_id = %s AND p.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
                ORDER BY p.project_code ASC;
                """
                linked_projects = run_query(sql_proj, [pid] + pi_proj_ids)
            else:
                linked_projects = []
        else:
            sql_proj = """
            SELECT p.project_id, p.project_code, p.title
            FROM project_publication AS pp
            JOIN project AS p ON p.project_id = pp.project_id
            WHERE pp.publication_id = %s
            ORDER BY p.project_code ASC;
            """
            linked_projects = run_query(sql_proj, (pid,))

        items.append({
            "publication_id": pid,
            "title": r["title"],
            "publication_type": r["publication_type"],
            "venue": r["venue"],
            "publication_date": r["publication_date"],
            "doi": r["doi"],
            "indexing": r["indexing"],
            "issn_isbn": r["issn_isbn"],
            "authors": authors,
            "linked_projects": linked_projects
        })

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

def get_publication_detail(publication_id: int, role: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves single publication metadata, authors, and authorized project affiliations."""
    is_pi = (role == "PI")
    pi_proj_ids = list(get_pi_project_ids(user_id)) if is_pi else []

    sql = """
    SELECT
      publication_id, title, pub_type AS publication_type, venue,
      pub_date AS publication_date, doi, indexing, issn_isbn
    FROM publication
    WHERE publication_id = %s;
    """
    pub = run_query(sql, (publication_id,), fetchone=True)
    if not pub:
        return None

    # Authors
    sql_authors = """
    SELECT
      pa.researcher_id,
      CONCAT(r.first_name, ' ', r.last_name) AS name,
      r.email, r.orcid_id AS orcid,
      d.dept_name,
      pa.is_corresponding,
      pa.author_order
    FROM publication_author AS pa
    JOIN researcher AS r ON r.researcher_id = pa.researcher_id
    JOIN department AS d ON d.dept_id = r.dept_id
    WHERE pa.publication_id = %s
    ORDER BY pa.author_order ASC;
    """
    authors = run_query(sql_authors, (publication_id,))

    # Scoped projects
    if is_pi:
        if pi_proj_ids:
            sql_proj = f"""
            SELECT p.project_id, p.project_code, p.title, p.status
            FROM project_publication AS pp
            JOIN project AS p ON p.project_id = pp.project_id
            WHERE pp.publication_id = %s AND p.project_id IN ({','.join(['%s']*len(pi_proj_ids))})
            ORDER BY p.project_code ASC;
            """
            projects = run_query(sql_proj, [publication_id] + pi_proj_ids)
        else:
            projects = []
    else:
        sql_proj = """
        SELECT p.project_id, p.project_code, p.title, p.status
        FROM project_publication AS pp
        JOIN project AS p ON p.project_id = pp.project_id
        WHERE pp.publication_id = %s
        ORDER BY p.project_code ASC;
        """
        projects = run_query(sql_proj, (publication_id,))

    return {
        "publication": pub,
        "authors": authors,
        "linked_projects": projects
    }

def create_publication(
    title: str,
    pub_type: str,
    venue: str,
    pub_date: str,
    doi: Optional[str],
    indexing: str,
    issn_isbn: Optional[str],
    authors: List[Dict[str, Any]],
    linked_project_ids: List[int]
) -> int:
    """
    Atomically creates publication record, author order entries, and project linkages.
    Enforces BR-08 (DOI format/uniqueness), BR-16 (date bounds), and BR-18 (unique author order).
    """
    with run_transaction() as cursor:
        # 1. Insert publication
        cursor.execute("""
            INSERT INTO publication (
              title, pub_type, venue, pub_date, doi, indexing, issn_isbn
            ) VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (
            title.strip(),
            pub_type,
            venue.strip(),
            pub_date,
            doi.strip() if doi else None,
            indexing,
            issn_isbn.strip() if issn_isbn else None
        ))
        cursor.execute("SELECT LAST_INSERT_ID() AS id;")
        pub_id = cursor.fetchone()["id"]

        # 2. Insert authors
        seen_res = set()
        for idx, author in enumerate(authors, start=1):
            res_id = int(author["researcher_id"])
            if res_id in seen_res:
                raise ValueError("BR-18: Each author must appear only once per publication")
            seen_res.add(res_id)

            cursor.execute("""
                INSERT INTO publication_author (publication_id, researcher_id, author_order, is_corresponding)
                VALUES (%s, %s, %s, %s);
            """, (pub_id, res_id, idx, bool(author.get("is_corresponding", False))))

        # 3. Link projects (BR-16 verified by trigger trg_chk_proj_pub_date_ins)
        for proj_id in linked_project_ids:
            cursor.execute("""
                INSERT INTO project_publication (project_id, publication_id)
                VALUES (%s, %s);
            """, (int(proj_id), pub_id))

        return pub_id

def search_publications_for_linking(
    query: str,
    target_project_id: int,
    role: str,
    user_id: int
) -> List[Dict[str, Any]]:
    """
    Search publications catalogue to link to target project.
    Strictly redacts unrelated project links.
    """
    sql = """
    SELECT
      p.publication_id,
      p.title,
      p.venue,
      p.pub_date AS publication_date,
      p.doi,
      p.pub_type AS publication_type,
      (EXISTS (
        SELECT 1 FROM project_publication AS pp
        WHERE pp.publication_id = p.publication_id AND pp.project_id = %s
      )) AS already_linked
    FROM publication AS p
    WHERE p.title LIKE %s OR p.doi LIKE %s
    ORDER BY p.pub_date DESC
    LIMIT 10;
    """
    wildcard = f"%{query.strip()}%"
    rows = run_query(sql, (target_project_id, wildcard, wildcard))
    results = []
    for r in rows:
        results.append({
            "id": r["publication_id"],
            "title": r["title"],
            "venue": r["venue"],
            "date": r["publication_date"].isoformat() if hasattr(r["publication_date"], "isoformat") else str(r["publication_date"]),
            "doi": r["doi"],
            "type": r["publication_type"],
            "already_linked_to_target": bool(r["already_linked"])
        })
    return results
