"""
RPGMS Milestones Service
File: app/services/milestones.py
Author: Antigravity AI

Handles milestone queries, Gantt-lite timeline grouping, status updates,
and procedure calls for completion.
Enforces role-based isolation:
- ADMIN / RESEARCH_OFFICER: Organization-wide access.
- PI: Scoped exclusively to milestones on own projects.
- VIEWER: No operational milestone list access.
"""

from datetime import date
from typing import Any, Dict, List, Optional
from app.db import run_query, call_procedure, run_transaction
from app.auth import get_pi_project_ids

ALLOWED_SORT_COLS = {
    "due_date": "m.due_date",
    "title": "m.title",
    "project": "p.project_code",
    "status": "m.status",
    "days_late": "days_late",
}

def get_milestones_list(
    filters: Dict[str, Any],
    role: str,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    sort_key: str = "due_date",
    sort_dir: str = "asc"
) -> Dict[str, Any]:
    """Retrieves paginated, role-scoped list of milestones."""
    is_pi = (role == "PI")
    pi_proj_ids = list(get_pi_project_ids(user_id)) if is_pi else []

    if is_pi and not pi_proj_ids:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "timeline_projects": []
        }

    where_clauses = []
    params: List[Any] = []

    if is_pi:
        placeholders = ",".join(["%s"] * len(pi_proj_ids))
        where_clauses.append(f"m.project_id IN ({placeholders})")
        params.extend(pi_proj_ids)

    q = filters.get("q", "").strip()
    if q:
        where_clauses.append("(m.title LIKE %s OR m.description LIKE %s OR p.project_code LIKE %s OR p.title LIKE %s)")
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    project_id = filters.get("project_id")
    if project_id:
        try:
            where_clauses.append("m.project_id = %s")
            params.append(int(project_id))
        except ValueError:
            pass

    dept_id = filters.get("dept_id")
    if dept_id:
        try:
            where_clauses.append("p.dept_id = %s")
            params.append(int(dept_id))
        except ValueError:
            pass

    status = filters.get("status")
    if status and status != "All":
        where_clauses.append("m.status = %s")
        params.append(status)

    if filters.get("overdue_only"):
        where_clauses.append("m.status IN ('Pending', 'In Progress', 'Delayed') AND m.due_date < CURDATE()")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Count
    count_sql = f"""
    SELECT COUNT(*) AS total
    FROM milestone AS m
    JOIN project AS p ON p.project_id = m.project_id
    {where_sql};
    """
    count_row = run_query(count_sql, params, fetchone=True)
    total_count = count_row["total"] if count_row else 0
    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

    offset = max(0, (page - 1) * page_size)
    direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
    sort_col = ALLOWED_SORT_COLS.get(sort_key.lower(), "m.due_date")

    data_sql = f"""
    SELECT
      m.milestone_id,
      m.project_id,
      p.project_code,
      p.title AS project_title,
      p.start_date AS project_start,
      p.end_date AS project_end,
      m.title,
      m.description,
      m.due_date,
      m.completed_date,
      m.status,
      DATEDIFF(CURDATE(), m.due_date) AS days_late
    FROM milestone AS m
    JOIN project AS p ON p.project_id = m.project_id
    {where_sql}
    ORDER BY {sort_col} {direction}
    LIMIT %s OFFSET %s;
    """
    query_params = list(params) + [page_size, offset]
    rows = run_query(data_sql, query_params)

    today = date.today()
    items = []
    for r in rows:
        is_done = (r["status"] == "Completed")
        is_overdue = (not is_done and r["due_date"] < today)
        items.append({
            "milestone_id": r["milestone_id"],
            "project_id": r["project_id"],
            "project_code": r["project_code"],
            "project_title": r["project_title"],
            "project_start": r["project_start"],
            "project_end": r["project_end"],
            "title": r["title"],
            "description": r["description"],
            "due_date": r["due_date"],
            "completed_date": r["completed_date"],
            "status": r["status"],
            "is_overdue": is_overdue,
            "days_late": max(0, r["days_late"] or 0)
        })

    # Timeline view data: group all matching projects with their milestones
    timeline_sql = f"""
    SELECT
      p.project_id, p.project_code, p.title AS project_title,
      p.start_date, p.end_date,
      m.milestone_id, m.title AS milestone_title, m.due_date, m.completed_date, m.status
    FROM project AS p
    JOIN milestone AS m ON m.project_id = p.project_id
    {where_sql}
    ORDER BY p.project_code ASC, m.due_date ASC;
    """
    tl_rows = run_query(timeline_sql, params)
    timeline_projects: Dict[int, Dict[str, Any]] = {}
    for r in tl_rows:
        pid = r["project_id"]
        if pid not in timeline_projects:
            timeline_projects[pid] = {
                "project_id": pid,
                "project_code": r["project_code"],
                "project_title": r["project_title"],
                "start_date": r["start_date"],
                "end_date": r["end_date"],
                "milestones": []
            }
        is_done = (r["status"] == "Completed")
        is_overdue = (not is_done and r["due_date"] < today)
        timeline_projects[pid]["milestones"].append({
            "milestone_id": r["milestone_id"],
            "title": r["milestone_title"],
            "due_date": r["due_date"],
            "completed_date": r["completed_date"],
            "status": r["status"],
            "is_overdue": is_overdue
        })

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "timeline_projects": list(timeline_projects.values())
    }

def create_milestone(project_id: int, title: str, description: str, due_date: str, status: str = "Pending") -> int:
    """Inserts a new milestone checking project date limits and closed status."""
    with run_transaction() as cursor:
        cursor.execute("SELECT start_date, end_date, status FROM project WHERE project_id = %s FOR UPDATE;", (project_id,))
        p = cursor.fetchone()
        if not p:
            raise ValueError("Project not found")
        if p["status"] in ("Completed", "Cancelled"):
            raise ValueError("BR-17: This project is closed; cannot add new milestones")

        cursor.execute("""
            INSERT INTO milestone (project_id, title, description, due_date, status)
            VALUES (%s, %s, %s, %s, %s);
        """, (project_id, title.strip(), description.strip() if description else None, due_date, status))
        cursor.execute("SELECT LAST_INSERT_ID() AS id;")
        return cursor.fetchone()["id"]

def update_milestone_status(milestone_id: int, new_status: str):
    """Updates milestone status via procedure sp_update_milestone_status."""
    call_procedure("sp_update_milestone_status", (milestone_id, new_status))

def complete_milestone(milestone_id: int, completed_date: str):
    """Completes milestone via procedure sp_complete_milestone."""
    call_procedure("sp_complete_milestone", (milestone_id, completed_date))

def get_overdue_milestones_count(role: str, user_id: int) -> int:
    """Returns count of overdue milestones for the bell notification badge."""
    is_pi = (role == "PI")
    if is_pi:
        pi_proj_ids = list(get_pi_project_ids(user_id))
        if not pi_proj_ids:
            return 0
        sql = f"""
        SELECT COUNT(*) AS cnt
        FROM milestone
        WHERE status IN ('Pending', 'In Progress', 'Delayed')
          AND due_date < CURDATE()
          AND project_id IN ({','.join(['%s']*len(pi_proj_ids))});
        """
        row = run_query(sql, pi_proj_ids, fetchone=True)
        return row["cnt"] if row else 0
    else:
        sql = """
        SELECT COUNT(*) AS cnt
        FROM milestone
        WHERE status IN ('Pending', 'In Progress', 'Delayed')
          AND due_date < CURDATE();
        """
        row = run_query(sql, fetchone=True)
        return row["cnt"] if row else 0
