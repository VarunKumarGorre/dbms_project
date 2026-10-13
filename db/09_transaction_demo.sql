-- ============================================================================
-- RPGMS Transaction Demonstration Script
-- File: db/09_transaction_demo.sql
-- Description: Interactive demonstrations of ACID properties against rpgms_test:
--              1. Atomicity (failed procedure rollback)
--              2. Explicit COMMIT vs ROLLBACK
--              3. Partial rollback using SAVEPOINT
--              4. Concurrency isolation under READ COMMITTED with row locking
-- ============================================================================

-- USE rpgms_test;

-- ----------------------------------------------------------------------------
-- DEMO 1: ATOMICITY (sp_register_project failure)
-- Attempt to register a project with an invalid/inactive researcher.
-- Proves that if the PI assignment fails, the project row is rolled back.
-- ----------------------------------------------------------------------------
SELECT COUNT(*) AS project_count_before FROM project WHERE project_code = 'RP-2026-999';

-- Attempt registration with non-existent researcher_id = 9999
-- Expected: Error 1644 (Researcher does not exist)
CALL sp_register_project(
  'RP-2026-999',
  'Disposable Atomic Test Project',
  'This project should never exist.',
  1,
  '2026-01-01',
  '2028-12-31',
  9999,
  20.00,
  @new_proj_id
);

-- Prove atomicity: No orphan project row was committed!
SELECT COUNT(*) AS project_count_after FROM project WHERE project_code = 'RP-2026-999';


-- ----------------------------------------------------------------------------
-- DEMO 2: EXPLICIT COMMIT VS ROLLBACK
-- Inserting a disposable funding agency inside a transaction, verifying it,
-- then issuing ROLLBACK to prove complete disappearance.
-- ----------------------------------------------------------------------------
START TRANSACTION;

INSERT INTO funding_agency (agency_name, agency_type, country)
VALUES ('Disposable Test Agency', 'Private', 'India');

-- Visible within current transaction:
SELECT agency_name, agency_type FROM funding_agency WHERE agency_name = 'Disposable Test Agency';

ROLLBACK;

-- Verified vanished after rollback:
SELECT COUNT(*) AS agency_count_after_rollback
FROM funding_agency
WHERE agency_name = 'Disposable Test Agency';


-- ----------------------------------------------------------------------------
-- DEMO 3: SAVEPOINT & PARTIAL ROLLBACK
-- Demonstrate rolling back part of a transaction without losing prior operations.
-- ----------------------------------------------------------------------------
START TRANSACTION;

-- Step A: Insert test department
INSERT INTO department (dept_code, dept_name, building)
VALUES ('TESTD', 'Disposable Testing Department', 'Test Lab');

SAVEPOINT sp_after_dept;

-- Step B: Insert second test department
INSERT INTO department (dept_code, dept_name, building)
VALUES ('TEMP2', 'Second Disposable Department', 'Temp Lab');

-- Roll back only to the savepoint
ROLLBACK TO SAVEPOINT sp_after_dept;

-- Commit the transaction
COMMIT;

-- Verify: 'TESTD' exists, but 'TEMP2' was rolled back!
SELECT dept_code, dept_name FROM department WHERE dept_code IN ('TESTD', 'TEMP2');

-- Clean up test department:
DELETE FROM department WHERE dept_code = 'TESTD';
