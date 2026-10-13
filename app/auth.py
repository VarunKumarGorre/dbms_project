"""
RPGMS Authentication & Role-Based Authorization
File: app/auth.py
Author: Antigravity AI

Handles:
- Bcrypt password verification and session rotation.
- Role-based decorators: require_login, require_role.
- Principal Investigator (PI) data scoping helpers.
"""

from functools import wraps
from typing import Any, Callable, List, Optional, Set
import bcrypt
from flask import abort, g, redirect, request, session, url_for, has_request_context
from app.db import run_query

ROLES = ("ADMIN", "RESEARCH_OFFICER", "PI", "VIEWER")

def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticates username and password against user_account table."""
    if not username or not password:
        return None

    sql = """
    SELECT u.user_id, u.username, u.password_hash, u.role, u.researcher_id, u.is_active,
           CONCAT(r.first_name, ' ', r.last_name) AS researcher_name
    FROM user_account AS u
    LEFT JOIN researcher AS r ON r.researcher_id = u.researcher_id
    WHERE u.username = %s;
    """
    row = run_query(sql, (username.strip(),), fetchone=True)
    if not row:
        return None

    if not row["is_active"]:
        return None

    stored_hash = row["password_hash"].encode("utf-8")
    provided_password = password.encode("utf-8")

    try:
        if bcrypt.checkpw(provided_password, stored_hash):
            return {
                "user_id": row["user_id"],
                "username": row["username"],
                "role": row["role"],
                "researcher_id": row["researcher_id"],
                "display_name": row["researcher_name"] or row["username"]
            }
    except Exception:
        return None

    return None

def login_user(user_data: dict):
    """Establishes authenticated session and rotates session identifier."""
    session.clear()
    session["user_id"] = user_data["user_id"]
    session["username"] = user_data["username"]
    session["role"] = user_data["role"]
    session["researcher_id"] = user_data["researcher_id"]
    session["display_name"] = user_data["display_name"]

def logout_user():
    """Clears authenticated session."""
    session.clear()

def get_current_user() -> Optional[dict]:
    """Returns current user details from session if authenticated."""
    if "user_id" in session:
        return {
            "user_id": session["user_id"],
            "username": session["username"],
            "role": session["role"],
            "researcher_id": session.get("researcher_id"),
            "display_name": session.get("display_name", session["username"])
        }
    return None

def require_login(f: Callable) -> Callable:
    """Decorator requiring an active authenticated session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login", return_to=request.full_path if request.full_path != "/?" else request.path))
        return f(*args, **kwargs)
    return decorated_function

def require_role(allowed_roles: List[str]) -> Callable:
    """Decorator restricting route access to specific roles."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("auth.login", return_to=request.full_path if request.full_path != "/?" else request.path))
            current_role = session.get("role")
            if current_role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_pi_project_ids(user_id: Optional[int] = None) -> Set[int]:
    """Returns the set of project IDs where the current user is Principal Investigator (PI)."""
    if user_id is None:
        user_id = session.get("user_id")
    researcher_id = session.get("researcher_id")

    if not researcher_id:
        return set()

    sql = """
    SELECT project_id
    FROM project_investigator
    WHERE researcher_id = %s AND role = 'PI';
    """
    rows = run_query(sql, (researcher_id,))
    return {r["project_id"] for r in rows}

def can_access_project(project_id: int, role: Optional[str] = None, user_id: Optional[int] = None) -> bool:
    """Verifies whether the user is authorized to view or manage a specific project."""
    if role is None:
        role = session.get("role") if has_request_context() else None
    if role in ("ADMIN", "RESEARCH_OFFICER"):
        return True
    if role == "PI":
        allowed_ids = get_pi_project_ids(user_id=user_id)
        return project_id in allowed_ids
    return False

def can_access_grant(grant_id: int, role: Optional[str] = None, user_id: Optional[int] = None) -> bool:
    """Verifies whether the user is authorized to view or manage a specific grant."""
    if role is None:
        role = session.get("role") if has_request_context() else None
    if role in ("ADMIN", "RESEARCH_OFFICER"):
        return True
    if role == "PI":
        sql = "SELECT project_id FROM grant_award WHERE grant_id = %s;"
        row = run_query(sql, (grant_id,), fetchone=True)
        if not row:
            return False
        return can_access_project(row["project_id"], role=role, user_id=user_id)
    return False
