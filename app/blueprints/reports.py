"""
RPGMS Reports Blueprint
File: app/blueprints/reports.py
Author: Antigravity AI
"""

from flask import Blueprint, render_template, request, Response, session, abort
from app.auth import require_role
from app.services.reports import (
    get_reports_hub_data, generate_report, export_report_csv, REPORTS_META
)
from app.db import run_query

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("/reports")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI", "VIEWER"])
def hub():
    reports_list = get_reports_hub_data()
    role = session.get("role")
    return render_template("reports/hub.html", reports=reports_list, role=role)

@reports_bp.route("/reports/<string:code>")
@require_role(["ADMIN", "RESEARCH_OFFICER", "PI", "VIEWER"])
def show_report(code: str):
    rep_code = code.upper()
    if rep_code not in REPORTS_META:
        abort(404)

    role = session.get("role")
    user_id = session.get("user_id")

    filters = {
        "status": request.args.get("status", "All"),
        "dept_id": request.args.get("dept_id", ""),
        "agency_id": request.args.get("agency_id", ""),
        "health": request.args.get("health", "All"),
        "year": request.args.get("year", ""),
        "indexing": request.args.get("indexing", "All"),
        "grant_id": request.args.get("grant_id", ""),
        "jurisdiction": request.args.get("jurisdiction", "All")
    }

    if request.args.get("format") == "csv":
        csv_data = export_report_csv(rep_code, filters, role, user_id)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=report_{rep_code.lower()}_export.csv"}
        )

    data = generate_report(rep_code, filters, role, user_id)
    if not data:
        abort(404)

    # Filter dropdown options if needed
    departments = run_query("SELECT dept_id, dept_name, dept_code FROM department ORDER BY dept_name ASC;")
    agencies = run_query("SELECT agency_id, agency_name FROM funding_agency ORDER BY agency_name ASC;")

    return render_template(
        "reports/report.html",
        report=data,
        filters=filters,
        departments=departments,
        agencies=agencies,
        role=role
    )
