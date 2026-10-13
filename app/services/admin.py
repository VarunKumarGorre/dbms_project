"""
RPGMS Administration Service
File: app/services/admin.py
Author: Antigravity AI

Handles user provisioning, role adjustments, account deactivation,
safety rules (protecting the last active ADMIN), and audit log inspection.
Access is strictly restricted to the ADMIN role.
"""

import json
from typing import Any, Dict, List, Optional
import bcrypt
from app.db import run_query, run_transaction

def get_users_list() -> List[Dict[str, Any]]:
    """Retrieves all user accounts with associated researcher and department info."""
    sql = """
    SELECT
      u.user_id,
      u.username,
      u.role,
      u.researcher_id,
      u.is_active,
      u.created_at,
      CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
      d.dept_name,
      d.dept_code
    FROM user_account AS u
    LEFT JOIN researcher AS r ON r.researcher_id = u.researcher_id
    LEFT JOIN department AS d ON d.dept_id = r.dept_id
    ORDER BY u.created_at DESC;
    """
    return run_query(sql)

def create_user(
    username: str,
    password: str,
    role: str,
    researcher_id: Optional[int]
) -> int:
    """
    Provisions a new user account with bcrypt password hashing.
    Enforces that role PI requires a linked researcher.
    """
    uname = username.strip().lower()
    if role == "PI" and not researcher_id:
        raise ValueError("A linked researcher is required when creating a PI user account")

    pwd_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    sql = """
    INSERT INTO user_account (username, password_hash, role, researcher_id, is_active)
    VALUES (%s, %s, %s, %s, TRUE);
    """
    with run_transaction() as cursor:
        cursor.execute(sql, (uname, pwd_hash, role, researcher_id if researcher_id else None))
        cursor.execute("SELECT LAST_INSERT_ID() AS id;")
        return cursor.fetchone()["id"]

def disable_user(user_id: int):
    """
    Deactivates an account (soft delete).
    Rejects disabling the last active ADMIN account.
    """
    with run_transaction() as cursor:
        cursor.execute("SELECT username, role, is_active FROM user_account WHERE user_id = %s FOR UPDATE;", (user_id,))
        u = cursor.fetchone()
        if not u:
            raise ValueError("User not found")

        if u["role"] == "ADMIN" and u["is_active"]:
            cursor.execute("SELECT COUNT(*) AS cnt FROM user_account WHERE role = 'ADMIN' AND is_active = TRUE;")
            admin_cnt = cursor.fetchone()["cnt"]
            if admin_cnt <= 1:
                raise ValueError("Cannot disable the last active ADMIN account")

        cursor.execute("UPDATE user_account SET is_active = FALSE WHERE user_id = %s;", (user_id,))

def update_user_role(user_id: int, new_role: str, researcher_id: Optional[int]):
    """
    Updates role and researcher link.
    Rejects demoting the last active ADMIN account.
    """
    if new_role == "PI" and not researcher_id:
        raise ValueError("A linked researcher is required for PI role")

    with run_transaction() as cursor:
        cursor.execute("SELECT username, role, is_active FROM user_account WHERE user_id = %s FOR UPDATE;", (user_id,))
        u = cursor.fetchone()
        if not u:
            raise ValueError("User not found")

        if u["role"] == "ADMIN" and new_role != "ADMIN" and u["is_active"]:
            cursor.execute("SELECT COUNT(*) AS cnt FROM user_account WHERE role = 'ADMIN' AND is_active = TRUE;")
            admin_cnt = cursor.fetchone()["cnt"]
            if admin_cnt <= 1:
                raise ValueError("Cannot demote the last active ADMIN account")

        cursor.execute("""
            UPDATE user_account
            SET role = %s, researcher_id = %s
            WHERE user_id = %s;
        """, (new_role, researcher_id if researcher_id else None, user_id))

def get_audit_log(
    table_name: Optional[str] = None,
    action: Optional[str] = None,
    record_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 25
) -> Dict[str, Any]:
    """Retrieves paginated audit log entries with change diffs."""
    where = []
    params: List[Any] = []

    if table_name and table_name != "All":
        where.append("table_name = %s")
        params.append(table_name)

    if action and action != "All":
        where.append("action = %s")
        params.append(action)

    if record_id:
        try:
            where.append("record_id = %s")
            params.append(int(record_id))
        except ValueError:
            pass

    if from_date:
        where.append("changed_at >= %s")
        params.append(from_date)

    if to_date:
        where.append("changed_at <= %s")
        params.append(f"{to_date} 23:59:59")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    count_sql = f"SELECT COUNT(*) AS total FROM audit_log {where_sql};"
    count_row = run_query(count_sql, params, fetchone=True)
    total_count = count_row["total"] if count_row else 0
    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

    offset = max(0, (page - 1) * page_size)
    data_sql = f"""
    SELECT
      log_id, table_name, record_id, action,
      old_values AS old_data, new_values AS new_data, changed_by, changed_at
    FROM audit_log
    {where_sql}
    ORDER BY changed_at DESC, log_id DESC
    LIMIT %s OFFSET %s;
    """
    rows = run_query(data_sql, list(params) + [page_size, offset])

    items = []
    for r in rows:
        old_val = r["old_data"]
        new_val = r["new_data"]
        if isinstance(old_val, str):
            try:
                old_val = json.loads(old_val)
            except Exception:
                pass
        if isinstance(new_val, str):
            try:
                new_val = json.loads(new_val)
            except Exception:
                pass

        # Build list of changed field diffs
        diffs = []
        if r["action"] == "UPDATE" and isinstance(old_val, dict) and isinstance(new_val, dict):
            all_keys = set(old_val.keys()).union(set(new_val.keys()))
            for k in sorted(all_keys):
                v_old = old_val.get(k)
                v_new = new_val.get(k)
                if v_old != v_new:
                    diffs.append({"field": k, "old": v_old, "new": v_new})

        items.append({
            "log_id": r["log_id"],
            "table_name": r["table_name"],
            "record_id": r["record_id"],
            "action": r["action"],
            "changed_by": r["changed_by"],
            "changed_at": r["changed_at"],
            "old_data": old_val,
            "new_data": new_val,
            "diffs": diffs
        })

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }
