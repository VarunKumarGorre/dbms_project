"""
RPGMS Route & Blueprint Integration Test Suite
File: tests/test_routes.py
Author: Antigravity AI

Verifies GET/POST route lifecycles across all 12 application blueprints:
auth, dashboard, projects, investigators, grants, milestones, expenditure,
publications, patents, reports, admin, and api.
"""

import json
import uuid
import random
import pytest

# 1. Authentication Routes
def test_auth_login_get_and_post(client):
    """Test login form GET, invalid POST, and valid POST."""
    resp_get = client.get("/login")
    assert resp_get.status_code == 200
    assert "Sign In" in resp_get.get_data(as_text=True)

    # Invalid login
    resp_bad = client.post("/login", data={"username": "admin", "password": "wrongpassword"})
    assert resp_bad.status_code == 200
    assert "Incorrect username or password" in resp_bad.get_data(as_text=True)

    # Valid login
    resp_ok = client.post("/login", data={"username": "admin", "password": "password123"}, follow_redirects=False)
    assert resp_ok.status_code == 302
    assert "/dashboard" in resp_ok.headers["Location"]

def test_auth_logout(admin_client):
    """Test user logout."""
    resp = admin_client.post("/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

# 2. Dashboard Routes
def test_dashboard_views(admin_client, pi_client, viewer_client):
    """Test dashboard loading for different roles."""
    assert admin_client.get("/dashboard").status_code == 200
    assert pi_client.get("/dashboard").status_code == 200
    assert viewer_client.get("/dashboard").status_code == 200

# 3. Project Workflow Routes
def test_projects_crud_workflow(admin_client):
    """Test project list, registration GET & POST, and detail views."""
    # List
    resp_list = admin_client.get("/projects")
    assert resp_list.status_code == 200
    assert "Projects" in resp_list.get_data(as_text=True)

    # Register Form GET
    resp_new_get = admin_client.get("/projects/new")
    assert resp_new_get.status_code == 200

    # Register Project POST (using sp_register_project)
    p_code = f"RP-2025-{random.randint(600, 999)}"
    post_data = {
        "project_code": p_code,
        "title": "Quantum Key Distribution Integration",
        "dept_id": "1",
        "pi_res_id": "1",
        "pi_effort": "25.0",
        "start_date": "2025-01-01",
        "end_date": "2027-12-31",
        "abstract": "Testing end-to-end route creation of quantum projects."
    }
    resp_create = admin_client.post("/projects/new", data=post_data, follow_redirects=False)
    assert resp_create.status_code == 302

    # View created project details
    detail_url = resp_create.headers["Location"]
    resp_detail = admin_client.get(detail_url)
    assert resp_detail.status_code == 200
    assert "Quantum Key Distribution Integration" in resp_detail.get_data(as_text=True)

def test_project_assign_investigator(admin_client):
    """Test adding team member to a project via modal POST."""
    resp = admin_client.post("/projects/1/investigators", data={
        "researcher_id": "4",
        "role": "Co-PI",
        "effort_percent": "15.00"
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert "/projects/1" in resp.headers["Location"]

# 4. Grants Workflow Routes
def test_grants_workflow(admin_client):
    """Test grants list, creation wizard GET & POST, and detail."""
    resp_list = admin_client.get("/grants")
    assert resp_list.status_code == 200

    resp_new_get = admin_client.get("/grants/new?project_id=1")
    assert resp_new_get.status_code == 200

    # Wizard POST with individual head allocations
    g_num = f"GA-ROUTE-{uuid.uuid4().hex[:6].upper()}"
    post_data = {
        "grant_number": g_num,
        "project_id": "1",
        "agency_id": "1",
        "amount": "500000.00",
        "sanction_date": "2024-01-01",
        "grant_start": "2024-01-01",
        "grant_end": "2025-12-31",
        "alloc_head_1": "300000.00",
        "alloc_head_2": "200000.00"
    }
    resp_create = admin_client.post("/grants/new", data=post_data, follow_redirects=False)
    assert resp_create.status_code == 302

    # Detail
    assert admin_client.get("/grants/1").status_code == 200

# 5. Expenditure Routes
def test_expenditure_workflow(admin_client):
    """Test expenditure list, expense entry, and statement."""
    resp_list = admin_client.get("/expenditure")
    assert resp_list.status_code == 200

    resp_form_get = admin_client.get("/expenditure/new?grant_id=1")
    assert resp_form_get.status_code == 200

    # Record expense POST (calling sp_record_expenditure)
    v_num = f"V-RT-{uuid.uuid4().hex[:6].upper()}"
    post_data = {
        "grant_id": "1",
        "head_id": "2",
        "expense_date": "2024-05-10",
        "amount": "1500.00",
        "description": "High-purity reagents for chemical vapor deposition",
        "voucher_no": v_num
    }
    resp_entry = admin_client.post("/expenditure/new", data=post_data, follow_redirects=False)
    assert resp_entry.status_code == 302

    # Financial statement
    resp_stmt = admin_client.get("/expenditure/statement/1")
    assert resp_stmt.status_code == 200
    assert "Statement of Expenditure" in resp_stmt.get_data(as_text=True)

# 6. Milestones Routes
def test_milestones_workflow(admin_client):
    """Test milestones list and status update POST."""
    resp_list = admin_client.get("/milestones")
    assert resp_list.status_code == 200

    # Update milestone status
    resp_upd = admin_client.post("/milestones/1/status", data={
        "status": "In Progress"
    }, follow_redirects=False)
    assert resp_upd.status_code == 302

# 7. Publications Workflow
def test_publications_workflow(admin_client):
    """Test publications list, creation form, and detail view."""
    assert admin_client.get("/publications").status_code == 200
    assert admin_client.get("/publications/new").status_code == 200

    # Create publication POST with author linkages
    doi_val = f"10.1109/JIOT.2025.{uuid.uuid4().hex[:6]}"
    post_data = {
        "title": "Novel Edge ML Frameworks for Real-Time ECG",
        "publication_type": "Journal",
        "venue": "IEEE Internet of Things Journal",
        "doi": doi_val,
        "publication_date": "2025-02-01",
        "indexing": "SCIE",
        "author_ids[]": ["1"],
        "is_corresponding[]": ["1"],
        "linked_project_ids[]": ["1"]
    }
    resp_create = admin_client.post("/publications/new", data=post_data, follow_redirects=False)
    assert resp_create.status_code == 302

    # Detail
    assert admin_client.get("/publications/1").status_code == 200

# 8. Patents Workflow
def test_patents_workflow(admin_client):
    """Test patents list, creation form, and detail view."""
    assert admin_client.get("/patents").status_code == 200
    assert admin_client.get("/patents/new").status_code == 200

    # Create patent POST
    app_num = f"202511{uuid.uuid4().hex[:6]}"
    post_data = {
        "title": "Quantum Photonic Modulator Architecture",
        "application_number": app_num,
        "filing_date": "2025-01-15",
        "jurisdiction": "India",
        "status": "Filed",
        "inventor_ids[]": ["1"],
        "linked_project_ids[]": ["1"]
    }
    resp_create = admin_client.post("/patents/new", data=post_data, follow_redirects=False)
    assert resp_create.status_code == 302

    # Detail
    assert admin_client.get("/patents/1").status_code == 200

# 9. Reports Hub & Analytics
def test_reports_hub_and_detail(admin_client):
    """Test reports directory hub and individual reports."""
    resp_hub = admin_client.get("/reports")
    assert resp_hub.status_code == 200
    assert "Analytical Reports" in resp_hub.get_data(as_text=True)

    resp_r1 = admin_client.get("/reports/r1")
    assert resp_r1.status_code == 200

    resp_r2 = admin_client.get("/reports/r2")
    assert resp_r2.status_code == 200

# 10. Admin Users & Audit
def test_admin_users_and_audit(admin_client):
    """Test user management and audit log pages."""
    resp_users = admin_client.get("/admin/users")
    assert resp_users.status_code == 200
    assert "User Accounts" in resp_users.get_data(as_text=True)

    resp_audit = admin_client.get("/admin/audit")
    assert resp_audit.status_code == 200
    assert "Audit Log" in resp_audit.get_data(as_text=True)

# 11. API Typeahead Endpoints
def test_api_search_endpoints(admin_client):
    """Test autocomplete typeahead APIs."""
    resp_search = admin_client.get("/api/search?q=sensor")
    assert resp_search.status_code == 200
    data = resp_search.get_json()
    assert "projects" in data
    assert "researchers" in data

    resp_heads = admin_client.get("/api/grants/1/heads")
    assert resp_heads.status_code == 200
    heads = resp_heads.get_json()
    assert len(heads) > 0

# 12. Error Handlers
def test_404_error_handler(admin_client):
    """Test that a non-existent route returns 404 with custom error page."""
    resp = admin_client.get("/non-existent-page-xyz-123")
    assert resp.status_code == 404
    assert "404" in resp.get_data(as_text=True)
    assert "Page Not Found" in resp.get_data(as_text=True)
