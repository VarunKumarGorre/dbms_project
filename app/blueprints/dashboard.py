"""
RPGMS Dashboard Blueprint
File: app/blueprints/dashboard.py
Author: Antigravity AI
"""

from flask import Blueprint, render_template, session
from app.auth import require_login
from app.services.dashboard import get_dashboard_data

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
@require_login
def index():
    role = session.get("role")
    user_id = session.get("user_id")
    researcher_id = session.get("researcher_id")

    dash_data = get_dashboard_data(role, user_id, researcher_id)
    return render_template("dashboard/index.html", data=dash_data, role=role)
