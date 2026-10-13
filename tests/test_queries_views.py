"""
RPGMS Queries, Views, and Fan-Out Verification Tests
File: tests/test_queries_views.py
Author: Antigravity AI

Verifies:
1. All 9 analytical views exist, return records, and satisfy arithmetic invariants.
2. Join fan-out absence: aggregate views match independent table sums.
3. All 40 numbered SQL queries (Q01-Q40) execute cleanly on rpgms_test.
4. All 10 analytical report engines (R1-R10) execute without error across roles.
"""

from decimal import Decimal
from pathlib import Path
import re
import pytest
from app.services.reports import generate_report, REPORTS_META

VIEWS = [
    "vw_project_overview",
    "vw_project_progress",
    "vw_budget_utilization",
    "vw_budget_head_utilization",
    "vw_milestone_tracker",
    "vw_researcher_output",
    "vw_agency_portfolio",
    "vw_project_publications",
    "vw_department_summary"
]

@pytest.mark.parametrize("view_name", VIEWS)
def test_all_views_return_rows(test_db, view_name):
    """Verify that every view returns rows in seeded database."""
    cursor = test_db.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM {view_name} LIMIT 10;")
    rows = cursor.fetchall()
    assert len(rows) > 0, f"View {view_name} returned 0 rows"

def test_view_arithmetic_consistency(test_db):
    """Verify arithmetic invariants: total_spent + balance == grant_amount."""
    cursor = test_db.cursor(dictionary=True)
    # Check vw_budget_utilization
    cursor.execute("SELECT grant_number, grant_amount, total_spent, balance FROM vw_budget_utilization;")
    for r in cursor.fetchall():
        spent = Decimal(str(r["total_spent"]))
        bal = Decimal(str(r["balance"]))
        amt = Decimal(str(r["grant_amount"]))
        assert spent + bal == amt, f"Arithmetic mismatch in grant {r['grant_number']}: {spent} + {bal} != {amt}"

    # Check vw_project_overview
    cursor.execute("SELECT project_code, total_grant_amount, total_spent, balance FROM vw_project_overview;")
    for r in cursor.fetchall():
        spent = Decimal(str(r["total_spent"]))
        bal = Decimal(str(r["balance"]))
        amt = Decimal(str(r["total_grant_amount"]))
        assert spent + bal == amt, f"Arithmetic mismatch in project {r['project_code']}: {spent} + {bal} != {amt}"

def test_join_fan_out_absence(test_db):
    """Detect join fan-out inflation: check view totals against direct table sums."""
    cursor = test_db.cursor(dictionary=True)

    # 1. Total grants sum in vw_agency_portfolio vs grant_award table
    cursor.execute("SELECT SUM(total_sanctioned_amount) AS view_tot FROM vw_agency_portfolio;")
    view_grant_total = cursor.fetchone()["view_tot"]
    cursor.execute("SELECT SUM(grant_amount) AS tbl_tot FROM grant_award;")
    tbl_grant_total = cursor.fetchone()["tbl_tot"]
    assert view_grant_total == tbl_grant_total, f"Fan-out detected: agency view total {view_grant_total} != table total {tbl_grant_total}"

    # 2. Total expenditure sum in vw_budget_utilization vs expenditure table
    cursor.execute("SELECT SUM(total_spent) AS view_tot FROM vw_budget_utilization;")
    view_exp_total = cursor.fetchone()["view_tot"]
    cursor.execute("SELECT SUM(amount) AS tbl_tot FROM expenditure;")
    tbl_exp_total = cursor.fetchone()["tbl_tot"]
    assert view_exp_total == tbl_exp_total, f"Fan-out detected: budget view total {view_exp_total} != expenditure table total {tbl_exp_total}"

def test_all_40_sql_queries_execute(test_db):
    """Execute all 40 queries from db/07_queries.sql to confirm syntax & semantics."""
    sql_path = Path(__file__).resolve().parent.parent / "db" / "07_queries.sql"
    sql_text = sql_path.read_text(encoding="utf-8")

    cursor = test_db.cursor()

    # Split into statements while skipping comments
    statements = []
    current = []
    for line in sql_text.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("--") or not trimmed:
            continue
        current.append(line)
        if trimmed.endswith(";"):
            statements.append("\n".join(current))
            current = []

    assert len(statements) >= 40, f"Expected at least 40 statements, found {len(statements)}"

    for idx, stmt in enumerate(statements, start=1):
        try:
            cursor.execute(stmt)
            # Consume result if it's a SELECT
            if cursor.with_rows:
                cursor.fetchall()
        except Exception as err:
            pytest.fail(f"Query #{idx} failed execution:\n{stmt}\nError: {err}")

@pytest.mark.parametrize("report_code", list(REPORTS_META.keys()))
def test_all_10_reports_execute(app, report_code):
    """Verify all 10 reports execute cleanly for both ADMIN and VIEWER roles."""
    with app.app_context():
        # Test as ADMIN
        admin_data = generate_report(report_code, {}, role="ADMIN", user_id=1)
        assert admin_data is not None, f"Report {report_code} failed for ADMIN"
        assert "columns" in admin_data
        assert "rows" in admin_data
        assert "tiles" in admin_data

        # Test as VIEWER (sanitized aggregates)
        viewer_data = generate_report(report_code, {}, role="VIEWER", user_id=6)
        assert viewer_data is not None, f"Report {report_code} failed for VIEWER"
        assert "columns" in viewer_data
        assert "rows" in viewer_data
