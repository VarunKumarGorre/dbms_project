"""
RPGMS Transaction Atomicity & Concurrency Test Suite
File: tests/test_transactions.py
Author: Antigravity AI

Verifies:
1. Atomicity & Rollback: Failing procedures roll back completely with zero partial writes.
2. Concurrent Double-Spend Race Condition: Two concurrent worker threads attempting
   to overspend a budget head with FOR UPDATE row locks ensure exactly ONE succeeds
   and ONE fails with BR-06.
"""

import os
import json
import threading
from decimal import Decimal
import pytest
import mysql.connector

def test_procedure_atomicity_and_rollback(test_db):
    """Verify that stored procedures roll back all intermediate writes upon error."""
    cursor = test_db.cursor(dictionary=True)

    # Initial counts
    cursor.execute("SELECT COUNT(*) AS cnt FROM grant_award;")
    initial_grants = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) AS cnt FROM grant_budget_allocation;")
    initial_allocs = cursor.fetchone()["cnt"]

    # Call sp_add_grant_with_budget with allocations exceeding grant amount
    # (allocations total 2,000,000 > grant_amount 1,000,000)
    invalid_allocs = json.dumps([
        {"head_id": 1, "amount": 1000000.00},
        {"head_id": 2, "amount": 1000000.00}
    ])

    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.callproc("sp_add_grant_with_budget", [
            "GA-ATOMIC-FAIL", 1, 1, 1000000.00, "2024-01-01", "2024-01-01", "2025-01-01", invalid_allocs, 0
        ])
    assert "BR-09" in str(exc_info.value)

    # Confirm complete rollback: no new grant, no new allocations
    cursor.execute("SELECT COUNT(*) AS cnt FROM grant_award;")
    final_grants = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) AS cnt FROM grant_budget_allocation;")
    final_allocs = cursor.fetchone()["cnt"]

    assert final_grants == initial_grants, "Atomicity violation: grant_award row was committed despite failure!"
    assert final_allocs == initial_allocs, "Atomicity violation: allocation row was committed despite failure!"

def test_concurrent_expenditure_race_condition():
    """
    Simulates two simultaneous user sessions attempting to spend ₹ 40,000 each
    against a budget head that only has ₹ 50,000 remaining.
    FOR UPDATE row locking in sp_record_expenditure ensures serialization:
    exactly one succeeds, one fails with BR-06, and no double-spend occurs.
    """
    # 1. Setup fixture data on rpgms_test
    setup_conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        database="rpgms_test",
        user=os.getenv("DB_TEST_USER", "rpgms_test_user"),
        password=os.getenv("DB_TEST_PASSWORD", "rpgms_test_pass"),
        autocommit=True
    )
    cursor = setup_conn.cursor(dictionary=True)

    # Create test grant with ₹ 100,000
    cursor.execute("""
        INSERT INTO grant_award (grant_number, project_id, agency_id, grant_amount, sanction_date, grant_start, grant_end, status)
        VALUES ('GA-RACE-CONC', 1, 1, 100000.00, '2024-01-01', '2024-01-01', '2025-12-31', 'Active');
    """)
    grant_id = cursor.lastrowid

    # Allocate ₹ 100,000 to head 1
    cursor.execute("""
        INSERT INTO grant_budget_allocation (grant_id, head_id, allocated_amount)
        VALUES (%s, 1, 100000.00);
    """, (grant_id,))

    # Initial spend ₹ 50,000 (leaves exactly ₹ 50,000)
    cursor.execute("""
        INSERT INTO expenditure (grant_id, head_id, expense_date, amount, description, voucher_no)
        VALUES (%s, 1, '2024-03-01', 50000.00, 'Baseline Spend', 'V-RACE-BASE');
    """, (grant_id,))
    setup_conn.close()

    # 2. Worker threads competing to spend ₹ 40,000
    results = []
    barrier = threading.Barrier(2)

    def worker(worker_id):
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", 3306)),
            database="rpgms_test",
            user=os.getenv("DB_USER", "rpgms_app"),
            password=os.getenv("DB_PASSWORD", "rpgms_app_pass"),
            autocommit=True
        )
        cur = conn.cursor()
        voucher_no = f"V-RACE-TH-{worker_id}"

        # Synchronize thread start at the barrier
        barrier.wait()

        try:
            cur.callproc("sp_record_expenditure", [
                grant_id,
                1,
                "2024-06-01",
                40000.00,
                f"Concurrent Spend Worker {worker_id}",
                voucher_no,
                1,
                0, 0, 0
            ])
            results.append({"worker": worker_id, "success": True, "error": None})
        except mysql.connector.Error as err:
            results.append({"worker": worker_id, "success": False, "error": str(err)})
        finally:
            conn.close()

    t1 = threading.Thread(target=worker, args=(1,))
    t2 = threading.Thread(target=worker, args=(2,))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # 3. Assertions
    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    assert len(successes) == 1, f"Expected exactly 1 successful spend, got {len(successes)}: {results}"
    assert len(failures) == 1, f"Expected exactly 1 failed spend, got {len(failures)}: {results}"
    assert "BR-06" in failures[0]["error"], f"Failure reason did not mention BR-06: {failures[0]['error']}"

    # Verify database final state
    verify_conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        database="rpgms_test",
        user=os.getenv("DB_TEST_USER", "rpgms_test_user"),
        password=os.getenv("DB_TEST_PASSWORD", "rpgms_test_pass"),
        autocommit=True
    )
    v_cur = verify_conn.cursor(dictionary=True)
    v_cur.execute("SELECT SUM(amount) AS total_spent FROM expenditure WHERE grant_id = %s;", (grant_id,))
    total_spent = v_cur.fetchone()["total_spent"]
    verify_conn.close()

    assert Decimal(str(total_spent)) == Decimal("90000.00"), f"Expected ₹ 90,000 spent (50k + 40k), found {total_spent}"
