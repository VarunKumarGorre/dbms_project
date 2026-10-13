"""
RPGMS Role-Based Access Control & Redaction Test Suite
File: tests/test_auth_roles.py
Author: Antigravity AI

Verifies:
1. VIEWER cannot access operational routes or search (strictly 403).
2. VIEWER accesses reports & dashboard safely: no row-level codes, names, vouchers, DOIs.
3. PI is strictly scoped to own projects; accessing another PI's project returns 403.
4. Protection against disabling or demoting the last active ADMIN.
"""

import pytest
from app.services.admin import disable_user, update_user_role
from app.services.reports import generate_report, export_report_csv, REPORTS_META

OPERATIONAL_ROUTES = [
    "/projects",
    "/projects/new",
    "/projects/1",
    "/investigators",
    "/grants",
    "/grants/new",
    "/expenditure",
    "/expenditure/new",
    "/milestones",
    "/publications",
    "/patents",
    "/api/search?q=test"
]

@pytest.mark.parametrize("route", OPERATIONAL_ROUTES)
def test_viewer_operational_routes_forbidden(viewer_client, route):
    """Verify that VIEWER role is strictly rejected with 403 from operational pages."""
    resp = viewer_client.get(route)
    assert resp.status_code == 403, f"Expected 403 Forbidden for route {route}, got {resp.status_code}"

def test_viewer_allowed_dashboard_and_reports(viewer_client):
    """Verify that VIEWER can access Dashboard and Reports hub."""
    resp_dash = viewer_client.get("/dashboard")
    assert resp_dash.status_code == 200

    resp_rep = viewer_client.get("/reports")
    assert resp_rep.status_code == 200

@pytest.mark.parametrize("report_code", list(REPORTS_META.keys()))
def test_viewer_redaction_in_reports_and_csv(viewer_client, app, report_code):
    """
    Verify that VIEWER reports and CSV exports contain ONLY aggregate metrics
    and omit row-level project codes (RP-xxxx), researcher names, vouchers, and DOIs.
    """
    # 1. HTML route
    resp = viewer_client.get(f"/reports/{report_code.lower()}")
    assert resp.status_code == 200

    # 2. CSV route
    csv_resp = viewer_client.get(f"/reports/{report_code.lower()}?format=csv")
    assert csv_resp.status_code == 200
    csv_content = csv_resp.get_data(as_text=True)

    # Prohibited operational row identifiers
    assert "RP-2024-001" not in csv_content, f"Report {report_code} CSV leaked project code"
    assert "Aravind Rao" not in csv_content, f"Report {report_code} CSV leaked researcher name"
    assert "V-2024-001" not in csv_content, f"Report {report_code} CSV leaked voucher number"
    assert "10.1109/" not in csv_content, f"Report {report_code} CSV leaked publication DOI"

def test_pi_access_scoping(pi_client):
    """
    Verify that PI (Dr. Aravind Rao) can view Project 1 (his own),
    but is strictly rejected with 403 when attempting to view Project 2 (Dr. Menon).
    """
    # Own project: allowed
    resp_own = pi_client.get("/projects/1")
    assert resp_own.status_code == 200

    # Other PI's project: rejected
    resp_other = pi_client.get("/projects/2")
    assert resp_other.status_code == 403

def test_last_active_admin_protection(app):
    """Verify that disabling or demoting the last active ADMIN is forbidden."""
    with app.app_context():
        # User 1 is the only active ADMIN in test seed
        with pytest.raises(ValueError) as exc_disable:
            disable_user(1)
        assert "Cannot disable the last active ADMIN account" in str(exc_disable.value)

        with pytest.raises(ValueError) as exc_demote:
            update_user_role(1, "VIEWER", None)
        assert "Cannot demote the last active ADMIN account" in str(exc_demote.value)

def test_officer_full_operational_access(officer_client):
    """Verify that RESEARCH_OFFICER has access to all operational modules."""
    for path in ["/projects", "/grants", "/expenditure", "/milestones", "/reports"]:
        resp = officer_client.get(path)
        assert resp.status_code == 200, f"Officer failed to access {path}: {resp.status_code}"
