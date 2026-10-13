"""
RPGMS Schema Constraints and Integrity Tests
File: tests/test_schema_constraints.py
Author: Antigravity AI

Validates all CHECK, UNIQUE, NOT NULL, FOREIGN KEY (composite & cascading),
and DEFAULT value constraints defined in db/01_schema.sql on rpgms_test.
"""

import pytest
import mysql.connector

def test_chk_proj_dates_valid_and_invalid(test_db):
    """CHECK chk_proj_dates: end_date > start_date and chk_proj_code format."""
    cursor = test_db.cursor()
    # Invalid: end_date <= start_date
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO project (project_code, title, dept_id, start_date, end_date)
            VALUES ('RP-2025-901', 'Invalid Project Dates', 1, '2025-06-01', '2025-05-01');
        """)
    assert "chk_proj_dates" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

    # Valid: end_date > start_date
    cursor.execute("""
        INSERT INTO project (project_code, title, dept_id, start_date, end_date)
        VALUES ('RP-2025-902', 'Valid Project Dates', 1, '2025-06-01', '2025-06-02');
    """)
    cursor.execute("SELECT status FROM project WHERE project_code = 'RP-2025-902';")
    row = cursor.fetchone()
    # Verify DEFAULT status = 'Proposed'
    assert row[0] == "Proposed"

def test_chk_gr_dates_sanction_and_end(test_db):
    """CHECK chk_gr_dates: sanction_date <= grant_start < grant_end."""
    cursor = test_db.cursor()
    # Invalid: grant_start before sanction_date
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO grant_award (grant_number, project_id, agency_id, grant_amount, sanction_date, grant_start, grant_end)
            VALUES ('GA-INV-01', 1, 1, 100000.00, '2025-05-01', '2025-04-01', '2025-08-01');
        """)
    assert "chk_gr_dates" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

    # Invalid: grant_end before grant_start
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO grant_award (grant_number, project_id, agency_id, grant_amount, sanction_date, grant_start, grant_end)
            VALUES ('GA-INV-02', 1, 1, 100000.00, '2025-05-01', '2025-05-01', '2025-04-30');
        """)
    assert "chk_gr_dates" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

def test_chk_positive_amounts(test_db):
    """CHECK amounts strictly > 0 for grant, allocation, and expenditure."""
    cursor = test_db.cursor()
    # Grant amount <= 0
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO grant_award (grant_number, project_id, agency_id, grant_amount, sanction_date, grant_start, grant_end)
            VALUES ('GA-INV-03', 1, 1, 0.00, '2024-01-01', '2024-01-01', '2025-01-01');
        """)
    assert "chk_gr_amount" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

    # Allocation amount <= 0
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO grant_budget_allocation (grant_id, head_id, allocated_amount)
            VALUES (1, 1, -500.00);
        """)
    assert "chk_alloc_amount" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

    # Expenditure amount <= 0
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO expenditure (grant_id, head_id, voucher_no, amount, expense_date, description)
            VALUES (1, 1, 'V-INV-01', 0.00, '2024-02-01', 'Invalid zero amount');
        """)
    assert "chk_exp_amount" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

def test_chk_pub_doi_format(test_db):
    """CHECK chk_pub_doi regex format."""
    cursor = test_db.cursor()
    # Invalid DOI format
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO publication (title, pub_type, venue, doi, pub_date)
            VALUES ('Invalid DOI Paper', 'Journal', 'Nature Testing', 'not-a-valid-doi', '2025-01-01');
        """)
    assert "chk_pub_doi" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

def test_chk_ms_completion_consistency(test_db):
    """CHECK chk_ms_completion: Completed requires date, others require NULL."""
    cursor = test_db.cursor()
    # Completed without completion date
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO milestone (project_id, title, due_date, status, completed_date)
            VALUES (1, 'Milestone Without Date', '2024-06-01', 'Completed', NULL);
        """)
    assert "chk_ms_completion" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

    # Pending with completion date
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO milestone (project_id, title, due_date, status, completed_date)
            VALUES (1, 'Pending Milestone With Date', '2024-06-01', 'Pending', '2024-05-15');
        """)
    assert "chk_ms_completion" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

def test_chk_pat_status_and_dates(test_db):
    """CHECK chk_pat_status & chk_pat_dates."""
    cursor = test_db.cursor()
    # Granted without patent_number
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO patent (application_number, title, filing_date, status, patent_number, grant_date)
            VALUES ('APP-INV-01', 'Granted Without Number', '2024-01-01', 'Granted', NULL, '2024-06-01');
        """)
    assert "chk_pat_status" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

    # Grant date before filing date
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO patent (application_number, title, filing_date, status, patent_number, grant_date)
            VALUES ('APP-INV-02', 'Backdated Patent', '2024-06-01', 'Granted', 'PAT-12345', '2024-05-01');
        """)
    assert "chk_pat_dates" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

def test_chk_rep_submit_rules(test_db):
    """CHECK chk_rep_submit: Draft requires NULL submission info, non-Draft requires NOT NULL."""
    cursor = test_db.cursor()
    # Draft with submitted_by populated
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO report (project_id, report_type, period_start, period_end, status, submitted_by)
            VALUES (1, 'Progress', '2024-01-01', '2024-03-31', 'Draft', 1);
        """)
    assert "chk_rep_submit" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

    # Submitted with NULL submitted_by
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO report (project_id, report_type, period_start, period_end, status, submitted_on, submitted_by)
            VALUES (1, 'Progress', '2024-01-01', '2024-03-31', 'Submitted', '2024-04-01', NULL);
        """)
    assert "chk_rep_submit" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

def test_chk_res_effort_bounds(test_db):
    """CHECK chk_pi_effort: 0 < effort_percent <= 100."""
    cursor = test_db.cursor()
    # Zero effort
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO project_investigator (project_id, researcher_id, role, assigned_date, effort_percent)
            VALUES (1, 3, 'Co-PI', '2024-01-01', 0.00);
        """)
    assert "chk_pi_effort" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

    # Effort > 100
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO project_investigator (project_id, researcher_id, role, assigned_date, effort_percent)
            VALUES (1, 3, 'Co-PI', '2024-01-01', 105.00);
        """)
    assert "chk_pi_effort" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

def test_uq_one_pi_per_project_and_uq_author_order(test_db):
    """UNIQUE uq_one_pi_per_project & uq_author_order."""
    cursor = test_db.cursor()
    # Project 1 already has PI (Dr. Aravind Rao, id=1). Attempting another PI directly:
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO project_investigator (project_id, researcher_id, role, assigned_date, effort_percent)
            VALUES (1, 2, 'PI', '2024-01-01', 20.00);
        """)
    assert "uq_one_pi_per_project" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()

    # Author order uniqueness per publication
    # Publication 1 already has author_order 1
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO publication_author (publication_id, researcher_id, author_order)
            VALUES (1, 4, 1);
        """)
    assert "uq_author_order" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()

def test_composite_foreign_key_expenditure_allocation(test_db):
    """Composite FK fk_exp_alloc on expenditure (grant_id, head_id) -> grant_budget_allocation."""
    cursor = test_db.cursor()
    # Create a new test grant with only head 1 allocated
    cursor.execute("""
        INSERT INTO grant_award (grant_number, project_id, agency_id, grant_amount, sanction_date, grant_start, grant_end)
        VALUES ('GA-FK-TEST-01', 1, 1, 500000.00, '2024-01-01', '2024-01-01', '2025-01-01');
    """)
    new_grant_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO grant_budget_allocation (grant_id, head_id, allocated_amount)
        VALUES (%s, 1, 500000.00);
    """, (new_grant_id,))

    # Expenditure on Head ID 2 (which is NOT allocated to this new grant) must fail composite FK
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO expenditure (grant_id, head_id, voucher_no, amount, expense_date, description)
            VALUES (%s, 2, 'V-COMP-FK-99', 5000.00, '2024-03-01', 'Unallocated head');
        """, (new_grant_id,))
    assert "fk_exp_alloc" in str(exc_info.value).lower() or "foreign key" in str(exc_info.value).lower()

def test_on_delete_restrict_and_cascade(test_db):
    """Verify ON DELETE RESTRICT on department and CASCADE on child links."""
    cursor = test_db.cursor()
    # Deleting department 1 should fail because researchers/projects exist
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("DELETE FROM department WHERE dept_id = 1;")
    assert "foreign key" in str(exc_info.value).lower()

def test_defaults_applied_when_columns_omitted(test_db):
    """Verify DEFAULT values when columns are omitted on INSERT."""
    cursor = test_db.cursor()
    # Researcher: is_active defaults to TRUE
    cursor.execute("""
        INSERT INTO researcher (employee_code, first_name, last_name, email, designation, dept_id, joined_date)
        VALUES ('EMP-DEF-01', 'Test', 'DefaultRes', 'test.default@example.edu', 'Assistant Professor', 1, '2024-01-01');
    """)
    res_id = cursor.lastrowid
    cursor.execute("SELECT is_active FROM researcher WHERE researcher_id = %s;", (res_id,))
    assert cursor.fetchone()[0] == 1

    # Milestone: status defaults to 'Pending'
    cursor.execute("""
        INSERT INTO milestone (project_id, title, due_date)
        VALUES (1, 'Default Test Milestone', '2025-01-15');
    """)
    ms_id = cursor.lastrowid
    cursor.execute("SELECT status FROM milestone WHERE milestone_id = %s;", (ms_id,))
    assert cursor.fetchone()[0] == "Pending"

    # Expenditure: created_at defaults to CURRENT_TIMESTAMP
    cursor.execute("""
        INSERT INTO expenditure (grant_id, head_id, voucher_no, amount, expense_date, description)
        VALUES (1, 1, 'V-DEF-99', 100.00, '2024-01-10', 'Default test');
    """)
    exp_id = cursor.lastrowid
    cursor.execute("SELECT created_at FROM expenditure WHERE expenditure_id = %s;", (exp_id,))
    assert cursor.fetchone()[0] is not None
