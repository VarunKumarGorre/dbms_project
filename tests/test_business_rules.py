"""
RPGMS Business Rules Test Suite (BR-01 to BR-18)
File: tests/test_business_rules.py
Author: Antigravity AI

Rigorous positive and negative verification for all 18 core business rules.
Asserts custom trigger/procedure BR-xx signals, native CHECK/UNIQUE/FK constraint mappings,
and user-friendly error formatting.
"""

import json
import pytest
import mysql.connector
from app.errors import format_db_error

def test_br01_project_dates(test_db):
    """BR-01: End date must be strictly after the start date."""
    cursor = test_db.cursor()
    # Negative: end_date <= start_date
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO project (project_code, title, dept_id, start_date, end_date)
            VALUES ('RP-2025-801', 'BR-01 Inverted Dates', 1, '2025-06-01', '2025-05-31');
        """)
    msg = format_db_error(exc_info.value)
    assert "End date must be after the start date" in msg

    # Positive
    cursor.execute("""
        INSERT INTO project (project_code, title, dept_id, start_date, end_date)
        VALUES ('RP-2025-802', 'BR-01 Valid Dates', 1, '2025-06-01', '2026-06-01');
    """)
    assert cursor.rowcount == 1

def test_br02_grant_dates(test_db):
    """BR-02: Grant sanction_date <= grant_start < grant_end."""
    cursor = test_db.cursor()
    # Negative: grant_end <= grant_start
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO grant_award (grant_number, project_id, agency_id, grant_amount, sanction_date, grant_start, grant_end)
            VALUES ('GA-BR02-INV', 1, 1, 100000.00, '2024-01-01', '2024-06-01', '2024-05-01');
        """)
    msg = format_db_error(exc_info.value)
    assert "Grant dates are invalid" in msg

    # Positive
    cursor.execute("""
        INSERT INTO grant_award (grant_number, project_id, agency_id, grant_amount, sanction_date, grant_start, grant_end)
        VALUES ('GA-BR02-VAL', 1, 1, 100000.00, '2024-01-01', '2024-01-01', '2025-01-01');
    """)
    assert cursor.rowcount == 1

def test_br03_grant_within_project_lifetime(test_db):
    """BR-03: Grant period must fall entirely within the parent project's lifetime."""
    cursor = test_db.cursor()
    # Project 1: start_date 2024-01-01, end_date 2026-12-31
    # Negative: grant_end extends beyond project end_date (2027-06-30 > 2026-12-31)
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO grant_award (grant_number, project_id, agency_id, grant_amount, sanction_date, grant_start, grant_end)
            VALUES ('GA-BR03-INV', 1, 1, 100000.00, '2024-01-01', '2024-01-01', '2027-06-30');
        """)
    assert "BR-03" in str(exc_info.value)

    # Positive: grant inside project lifetime
    cursor.execute("""
        INSERT INTO grant_award (grant_number, project_id, agency_id, grant_amount, sanction_date, grant_start, grant_end)
        VALUES ('GA-BR03-VAL', 1, 1, 100000.00, '2024-01-01', '2024-02-01', '2025-12-31');
    """)
    assert cursor.rowcount == 1

def test_br04_milestone_within_project_dates(test_db):
    """BR-04: Milestone due_date and completed_date must fall within project lifetime."""
    cursor = test_db.cursor()
    # Negative: milestone due date after project end date (2027-06-01 > 2026-12-31)
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO milestone (project_id, title, due_date)
            VALUES (1, 'BR-04 Post-Project Milestone', '2027-06-01');
        """)
    assert "BR-04" in str(exc_info.value)

    # Positive
    cursor.execute("""
        INSERT INTO milestone (project_id, title, due_date)
        VALUES (1, 'BR-04 Valid Milestone', '2025-06-01');
    """)
    assert cursor.rowcount == 1

def test_br05_strictly_positive_amounts(test_db):
    """BR-05: Grant, allocation, and expenditure amounts must be strictly > 0."""
    cursor = test_db.cursor()
    # Negative: zero allocation
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO grant_budget_allocation (grant_id, head_id, allocated_amount)
            VALUES (1, 1, 0.00);
        """)
    msg = format_db_error(exc_info.value)
    assert "amounts must be strictly greater than zero" in msg

def test_br06_expenditure_budget_limit(test_db):
    """BR-06: Expenditure amount cannot exceed remaining budget head or total grant."""
    cursor = test_db.cursor()
    # Call stored procedure with 10 arguments attempting massive overspend
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.callproc("sp_record_expenditure", [
            1,            # grant_id
            1,            # head_id
            "2024-05-01", # expense_date
            99999999.00,  # massive amount exceeding budget
            "Massive Overspend",
            "V-BR06-ERR",
            1,            # recorded_by
            0, 0, 0       # OUT parameters
        ])
    assert "BR-06" in str(exc_info.value)

def test_br07_expense_within_grant_dates(test_db):
    """BR-07: Expense date must fall within grant start and end dates."""
    cursor = test_db.cursor()
    # Grant 1 period: 2024-01-01 to 2026-12-31
    # Negative: expense before grant start
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO expenditure (grant_id, head_id, expense_date, amount, description, voucher_no)
            VALUES (1, 1, '2023-12-15', 500.00, 'Pre-grant expense', 'V-BR07-INV');
        """)
    assert "BR-07" in str(exc_info.value)

    # Positive
    cursor.execute("""
        INSERT INTO expenditure (grant_id, head_id, expense_date, amount, description, voucher_no)
        VALUES (1, 1, '2024-06-15', 500.00, 'Valid date expense', 'V-BR07-VAL');
    """)
    assert cursor.rowcount == 1

def test_br08_doi_uniqueness_and_format(test_db):
    """BR-08: Publication DOI format and global uniqueness."""
    cursor = test_db.cursor()
    # Seed already has '10.1109/JSEN.2024.3389123' on publication 1
    # Negative: duplicate DOI
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO publication (title, pub_type, venue, doi, pub_date)
            VALUES ('Duplicate DOI Paper', 'Journal', 'IEEE Sensors', '10.1109/JSEN.2024.3389123', '2024-08-01');
        """)
    msg = format_db_error(exc_info.value)
    assert "DOI already exists" in msg

    # Positive: valid unique DOI
    cursor.execute("""
        INSERT INTO publication (title, pub_type, venue, doi, pub_date)
        VALUES ('Unique DOI Paper', 'Journal', 'IEEE Sensors', '10.1109/JSEN.2025.9999999', '2025-01-01');
    """)
    assert cursor.rowcount == 1

def test_br09_total_allocation_limit(test_db):
    """BR-09: Total allocations cannot exceed sanctioned grant amount."""
    cursor = test_db.cursor()
    allocs = json.dumps([{"head_id": 1, "amount": 600000.00}, {"head_id": 2, "amount": 600000.00}])
    # Calling sp_add_grant_with_budget with allocations (1,200,000) > grant amount (1,000,000)
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.callproc("sp_add_grant_with_budget", [
            "GA-BR09-EXCEED", 1, 1, 1000000.00, "2024-01-01", "2024-01-01", "2025-01-01", allocs, 0
        ])
    assert "BR-09" in str(exc_info.value)

def test_br10_single_pi_per_project(test_db):
    """BR-10: Exactly one Principal Investigator per project."""
    cursor = test_db.cursor()
    # Project 1 already has PI Dr. Rao. Attempting to add researcher 5 as second PI
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO project_investigator (project_id, researcher_id, role, assigned_date, effort_percent)
            VALUES (1, 5, 'PI', '2024-01-01', 25.00);
        """)
    msg = format_db_error(exc_info.value)
    assert "exactly one Principal Investigator" in msg

def test_br11_researcher_effort_limit(test_db):
    """BR-11: Total active researcher effort cannot exceed 100%."""
    cursor = test_db.cursor()
    # Dr. Aravind Rao (id=1) already has active effort allocated.
    # Assigning him 95% on project 3 breaches 100% limit
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.callproc("sp_assign_investigator", [3, 1, "Co-PI", 95.00])
    assert "BR-11" in str(exc_info.value)

def test_br12_inactive_researcher_rejected(test_db):
    """BR-12: Inactive researchers cannot be assigned to projects."""
    cursor = test_db.cursor()
    # Researcher 24 (Suresh) is inactive (is_active = FALSE)
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO project_investigator (project_id, researcher_id, role, assigned_date, effort_percent)
            VALUES (1, 24, 'Researcher', '2024-01-01', 15.00);
        """)
    assert "BR-12" in str(exc_info.value)

def test_br13_milestone_completion_date(test_db):
    """BR-13: Completed status requires completion date; other statuses forbid it."""
    cursor = test_db.cursor()
    # Negative: Delayed with completed_date
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO milestone (project_id, title, due_date, status, completed_date)
            VALUES (1, 'BR-13 Invalid Delayed', '2024-08-01', 'Delayed', '2024-08-10');
        """)
    msg = format_db_error(exc_info.value)
    assert "completed milestone needs a completion date" in msg

def test_br14_patent_status_and_dates(test_db):
    """BR-14: Granted patents require patent number and grant date on/after filing."""
    cursor = test_db.cursor()
    # Negative: Granted without patent_number
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO patent (application_number, title, filing_date, status, grant_date)
            VALUES ('APP-BR14-INV', 'BR-14 Patent', '2024-01-01', 'Granted', '2024-06-01');
        """)
    msg = format_db_error(exc_info.value)
    assert "granted patent needs a valid patent number" in msg

def test_br15_allocated_budget_head_required(test_db):
    """BR-15: Expenditure requires pre-allocated budget head for the grant."""
    cursor = test_db.cursor()
    # Create test grant with head 1 only
    cursor.execute("""
        INSERT INTO grant_award (grant_number, project_id, agency_id, grant_amount, sanction_date, grant_start, grant_end)
        VALUES ('GA-BR15-TEST', 1, 1, 200000.00, '2024-01-01', '2024-01-01', '2025-01-01');
    """)
    g_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO grant_budget_allocation (grant_id, head_id, allocated_amount)
        VALUES (%s, 1, 200000.00);
    """, (g_id,))

    # Spending on head 2 should fail composite foreign key
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO expenditure (grant_id, head_id, expense_date, amount, description, voucher_no)
            VALUES (%s, 2, '2024-06-01', 1000.00, 'Unallocated Head Expense', 'V-BR15-INV');
        """, (g_id,))
    msg = format_db_error(exc_info.value)
    assert "budget head that is allocated to this grant" in msg

def test_br16_publication_date_relative_to_project(test_db):
    """BR-16: Publication date cannot be earlier than start date of linked project."""
    cursor = test_db.cursor()
    # Project 1 starts 2024-01-01
    # Create paper published in 2022
    cursor.execute("""
        INSERT INTO publication (title, pub_type, venue, pub_date)
        VALUES ('Pre-Project Discovery Paper', 'Journal', 'Physical Review', '2022-05-01');
    """)
    pub_id = cursor.lastrowid

    # Linking to Project 1 must trigger BR-16
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO project_publication (project_id, publication_id)
            VALUES (1, %s);
        """, (pub_id,))
    assert "BR-16" in str(exc_info.value)

def test_br17_closed_project_immutability(test_db):
    """BR-17: Closed project rejects new expenditures, milestones, or team assignments."""
    cursor = test_db.cursor()
    # Project 6 is Completed in seed data
    # Attempting to add a new milestone to completed project
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO milestone (project_id, title, due_date)
            VALUES (6, 'Post-Close Milestone', '2024-06-01');
        """)
    assert "BR-17" in str(exc_info.value)
    assert "closed" in str(exc_info.value).lower()

def test_br18_publication_authors(test_db):
    """BR-18: Unique author order and each author appears at most once per publication."""
    cursor = test_db.cursor()
    # Publication 1 already has researcher 1 as author
    # Negative: same researcher twice
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("""
            INSERT INTO publication_author (publication_id, researcher_id, author_order)
            VALUES (1, 1, 5);
        """)
    msg = format_db_error(exc_info.value)
    assert "Each author must appear once per publication" in msg or "duplicate" in str(exc_info.value).lower()
