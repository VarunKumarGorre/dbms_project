-- ============================================================================
-- RPGMS Stored Procedures
-- File: db/03_procedures.sql
-- Description: Transaction-owning stored procedures with explicit row locks,
--              READ COMMITTED isolation, and atomic commit/rollback.
-- ============================================================================

DELIMITER $$

-- ----------------------------------------------------------------------------
-- 1. sp_register_project
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_register_project$$
CREATE PROCEDURE sp_register_project(
  IN  p_code          VARCHAR(20),
  IN  p_title         VARCHAR(200),
  IN  p_abstract      TEXT,
  IN  p_dept_id       INT UNSIGNED,
  IN  p_start         DATE,
  IN  p_end           DATE,
  IN  p_pi_res_id     INT UNSIGNED,
  IN  p_pi_effort     DECIMAL(5,2),
  OUT p_project_id    INT UNSIGNED
)
SQL SECURITY DEFINER
BEGIN
  DECLARE v_is_active BOOLEAN;
  DECLARE v_curr_effort DECIMAL(7,2);

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
  START TRANSACTION;

  -- 1. Validate dates (BR-01)
  IF p_end <= p_start THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-01: End date must be after the start date';
  END IF;

  -- 2. Validate effort bounds
  IF p_pi_effort <= 0 OR p_pi_effort > 100 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Effort percentage must be between 1 and 100';
  END IF;

  -- 3. Lock researcher and validate active (BR-12)
  SELECT is_active INTO v_is_active
    FROM researcher
   WHERE researcher_id = p_pi_res_id
     FOR UPDATE;

  IF v_is_active IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Researcher does not exist';
  END IF;

  IF v_is_active = FALSE THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-12: Inactive researchers cannot be assigned to projects';
  END IF;

  -- 4. Validate combined workload across Proposed/Active projects (BR-11)
  SELECT COALESCE(SUM(pi.effort_percent), 0)
    INTO v_curr_effort
    FROM project_investigator AS pi
    JOIN project AS p ON p.project_id = pi.project_id
   WHERE pi.researcher_id = p_pi_res_id
     AND p.status IN ('Proposed', 'Active');

  IF (v_curr_effort + p_pi_effort) > 100.00 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-11: This assignment would exceed the 100% effort limit across active projects';
  END IF;

  -- 5. Insert project
  INSERT INTO project (project_code, title, abstract, dept_id, start_date, end_date, status)
  VALUES (p_code, p_title, p_abstract, p_dept_id, p_start, p_end, 'Proposed');

  SET p_project_id = LAST_INSERT_ID();

  -- 6. Insert initial PI (BR-10)
  INSERT INTO project_investigator (project_id, researcher_id, role, assigned_date, effort_percent)
  VALUES (p_project_id, p_pi_res_id, 'PI', p_start, p_pi_effort);

  COMMIT;
END$$


-- ----------------------------------------------------------------------------
-- 2. sp_assign_investigator
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_assign_investigator$$
CREATE PROCEDURE sp_assign_investigator(
  IN p_project_id     INT UNSIGNED,
  IN p_researcher_id  INT UNSIGNED,
  IN p_role           VARCHAR(20),
  IN p_effort_percent DECIMAL(5,2)
)
SQL SECURITY DEFINER
BEGIN
  DECLARE v_proj_status VARCHAR(20);
  DECLARE v_is_active BOOLEAN;
  DECLARE v_curr_effort DECIMAL(7,2);

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
  START TRANSACTION;

  -- Reject role PI (use sp_change_project_pi)
  IF p_role = 'PI' THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-10: Cannot assign PI directly. Use Change PI procedure';
  END IF;

  IF p_effort_percent <= 0 OR p_effort_percent > 100 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Effort percentage must be between 1 and 100';
  END IF;

  -- 1. Lock project row
  SELECT status INTO v_proj_status
    FROM project
   WHERE project_id = p_project_id
     FOR UPDATE;

  IF v_proj_status IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Project not found';
  END IF;

  IF v_proj_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: Cannot assign researchers to a completed or cancelled project';
  END IF;

  -- 2. Lock researcher row
  SELECT is_active INTO v_is_active
    FROM researcher
   WHERE researcher_id = p_researcher_id
     FOR UPDATE;

  IF v_is_active IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Researcher not found';
  END IF;

  IF v_is_active = FALSE THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-12: Inactive researchers cannot be assigned to projects';
  END IF;

  -- 3. Calculate workload on Proposed/Active projects (BR-11)
  IF v_proj_status IN ('Proposed', 'Active') THEN
    SELECT COALESCE(SUM(pi.effort_percent), 0)
      INTO v_curr_effort
      FROM project_investigator AS pi
      JOIN project AS p ON p.project_id = pi.project_id
     WHERE pi.researcher_id = p_researcher_id
       AND p.status IN ('Proposed', 'Active');

    IF (v_curr_effort + p_effort_percent) > 100.00 THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'BR-11: This assignment would exceed the 100% effort limit across active projects';
    END IF;
  END IF;

  -- 4. Insert assignment
  INSERT INTO project_investigator (project_id, researcher_id, role, assigned_date, effort_percent)
  VALUES (p_project_id, p_researcher_id, p_role, CURDATE(), p_effort_percent);

  COMMIT;
END$$


-- ----------------------------------------------------------------------------
-- 3. sp_remove_investigator
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_remove_investigator$$
CREATE PROCEDURE sp_remove_investigator(
  IN p_project_id    INT UNSIGNED,
  IN p_researcher_id INT UNSIGNED
)
SQL SECURITY DEFINER
BEGIN
  DECLARE v_proj_status VARCHAR(20);
  DECLARE v_role VARCHAR(20);

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
  START TRANSACTION;

  -- 1. Lock project
  SELECT status INTO v_proj_status
    FROM project
   WHERE project_id = p_project_id
     FOR UPDATE;

  IF v_proj_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: Cannot modify team of a closed project';
  END IF;

  -- 2. Lock assignment
  SELECT role INTO v_role
    FROM project_investigator
   WHERE project_id = p_project_id
     AND researcher_id = p_researcher_id
     FOR UPDATE;

  IF v_role IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Team assignment not found';
  END IF;

  IF v_role = 'PI' THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-10: Cannot remove the Principal Investigator. Use Change PI to transfer leadership';
  END IF;

  DELETE FROM project_investigator
   WHERE project_id = p_project_id
     AND researcher_id = p_researcher_id;

  COMMIT;
END$$


-- ----------------------------------------------------------------------------
-- 4. sp_add_grant_with_budget
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_add_grant_with_budget$$
CREATE PROCEDURE sp_add_grant_with_budget(
  IN  p_grant_number      VARCHAR(40),
  IN  p_project_id        INT UNSIGNED,
  IN  p_agency_id         INT UNSIGNED,
  IN  p_amount            DECIMAL(14,2),
  IN  p_sanction          DATE,
  IN  p_gstart            DATE,
  IN  p_gend              DATE,
  IN  p_allocations_json  JSON,
  OUT p_grant_id          INT UNSIGNED
)
SQL SECURITY DEFINER
BEGIN
  DECLARE v_p_start DATE;
  DECLARE v_p_end DATE;
  DECLARE v_p_status VARCHAR(20);
  DECLARE v_alloc_count INT;
  DECLARE v_i INT DEFAULT 0;
  DECLARE v_head_id INT UNSIGNED;
  DECLARE v_head_amount DECIMAL(14,2);
  DECLARE v_total_allocated DECIMAL(14,2) DEFAULT 0.00;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
  START TRANSACTION;

  -- 1. Lock and validate project
  SELECT start_date, end_date, status
    INTO v_p_start, v_p_end, v_p_status
    FROM project
   WHERE project_id = p_project_id
     FOR UPDATE;

  IF v_p_status IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Project not found';
  END IF;

  IF v_p_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: Cannot add a grant to a completed or cancelled project';
  END IF;

  -- 2. Validate dates (BR-02, BR-03)
  IF p_gend <= p_gstart OR p_gstart < p_sanction THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-02: Grant end date must be after start date, and start date on or after sanction date';
  END IF;

  IF p_gstart < v_p_start OR p_gend > v_p_end THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-03: The grant period must fall inside the project dates';
  END IF;

  IF p_amount <= 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-05: Grant amount must be greater than zero';
  END IF;

  -- 3. Validate JSON allocations array
  SET v_alloc_count = JSON_LENGTH(p_allocations_json);
  IF v_alloc_count IS NULL OR v_alloc_count = 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Budget allocations array cannot be empty';
  END IF;

  -- Verify allocations sum (BR-09) and positive amounts (BR-05)
  WHILE v_i < v_alloc_count DO
    SET v_head_id = JSON_UNQUOTE(JSON_EXTRACT(p_allocations_json, CONCAT('$[', v_i, '].head_id')));
    SET v_head_amount = CAST(JSON_UNQUOTE(JSON_EXTRACT(p_allocations_json, CONCAT('$[', v_i, '].amount'))) AS DECIMAL(14,2));

    IF v_head_amount IS NULL OR v_head_amount <= 0 THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'BR-05: Each budget allocation must be greater than zero';
    END IF;

    SET v_total_allocated = v_total_allocated + v_head_amount;
    SET v_i = v_i + 1;
  END WHILE;

  IF v_total_allocated > p_amount THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-09: Total budget allocations cannot exceed the grant amount';
  END IF;

  -- 4. Insert grant_award
  INSERT INTO grant_award (grant_number, project_id, agency_id, grant_amount, sanction_date, grant_start, grant_end, status)
  VALUES (p_grant_number, p_project_id, p_agency_id, p_amount, p_sanction, p_gstart, p_gend, 'Sanctioned');

  SET p_grant_id = LAST_INSERT_ID();

  -- 5. Insert budget allocations
  SET v_i = 0;
  WHILE v_i < v_alloc_count DO
    SET v_head_id = JSON_UNQUOTE(JSON_EXTRACT(p_allocations_json, CONCAT('$[', v_i, '].head_id')));
    SET v_head_amount = CAST(JSON_UNQUOTE(JSON_EXTRACT(p_allocations_json, CONCAT('$[', v_i, '].amount'))) AS DECIMAL(14,2));

    INSERT INTO grant_budget_allocation (grant_id, head_id, allocated_amount)
    VALUES (p_grant_id, v_head_id, v_head_amount);

    SET v_i = v_i + 1;
  END WHILE;

  COMMIT;
END$$


-- ----------------------------------------------------------------------------
-- 5. sp_record_expenditure
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_record_expenditure$$
CREATE PROCEDURE sp_record_expenditure(
  IN  p_grant_id          INT UNSIGNED,
  IN  p_head_id           INT UNSIGNED,
  IN  p_expense_date      DATE,
  IN  p_amount            DECIMAL(14,2),
  IN  p_description       VARCHAR(250),
  IN  p_voucher_no        VARCHAR(30),
  IN  p_user_id           INT UNSIGNED,
  OUT p_expenditure_id    INT UNSIGNED,
  OUT p_head_remaining    DECIMAL(14,2),
  OUT p_grant_remaining   DECIMAL(14,2)
)
SQL SECURITY DEFINER
BEGIN
  DECLARE v_grant_amount DECIMAL(14,2);
  DECLARE v_grant_start DATE;
  DECLARE v_grant_end DATE;
  DECLARE v_grant_status VARCHAR(20);
  DECLARE v_proj_status VARCHAR(20);
  DECLARE v_allocated_amount DECIMAL(14,2);
  DECLARE v_head_spent DECIMAL(14,2);
  DECLARE v_grant_spent DECIMAL(14,2);

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
  START TRANSACTION;

  -- 1. Validate positive amount (BR-05)
  IF p_amount <= 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-05: Expenditure amount must be greater than zero';
  END IF;

  -- 2. Lock grant_award row first (serializes spend on this grant)
  SELECT g.grant_amount, g.grant_start, g.grant_end, g.status, p.status
    INTO v_grant_amount, v_grant_start, v_grant_end, v_grant_status, v_proj_status
    FROM grant_award AS g
    JOIN project AS p ON p.project_id = g.project_id
   WHERE g.grant_id = p_grant_id
     FOR UPDATE;

  IF v_grant_amount IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Grant not found';
  END IF;

  IF v_proj_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: This project is closed, so new expenses or milestones cannot be added';
  END IF;

  IF v_grant_status IN ('Closed', 'Terminated') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: This grant is closed or terminated; no new expenditure allowed';
  END IF;

  IF p_expense_date < v_grant_start OR p_expense_date > v_grant_end THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-07: The expense date must be within the grant period';
  END IF;

  -- 3. Lock allocation row
  SELECT allocated_amount
    INTO v_allocated_amount
    FROM grant_budget_allocation
   WHERE grant_id = p_grant_id
     AND head_id = p_head_id
     FOR UPDATE;

  IF v_allocated_amount IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-15: Select a budget head that is allocated to this grant';
  END IF;

  -- 4. Re-read spent totals under lock at READ COMMITTED
  SELECT COALESCE(SUM(amount), 0)
    INTO v_head_spent
    FROM expenditure
   WHERE grant_id = p_grant_id
     AND head_id = p_head_id;

  SELECT COALESCE(SUM(amount), 0)
    INTO v_grant_spent
    FROM expenditure
   WHERE grant_id = p_grant_id;

  -- 5. Enforce budget limits (BR-06)
  IF (v_head_spent + p_amount) > v_allocated_amount THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-06: Expenditure exceeds the allocation for this budget head';
  END IF;

  IF (v_grant_spent + p_amount) > v_grant_amount THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-06: Expenditure exceeds total grant amount';
  END IF;

  -- 6. Insert expenditure
  INSERT INTO expenditure (grant_id, head_id, expense_date, amount, description, voucher_no, recorded_by)
  VALUES (p_grant_id, p_head_id, p_expense_date, p_amount, p_description, p_voucher_no, p_user_id);

  SET p_expenditure_id = LAST_INSERT_ID();
  SET p_head_remaining = v_allocated_amount - (v_head_spent + p_amount);
  SET p_grant_remaining = v_grant_amount - (v_grant_spent + p_amount);

  -- If grant was Sanctioned, transition to Active
  IF v_grant_status = 'Sanctioned' THEN
    UPDATE grant_award SET status = 'Active' WHERE grant_id = p_grant_id;
  END IF;

  COMMIT;
END$$


-- ----------------------------------------------------------------------------
-- 6. sp_update_milestone_status
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_update_milestone_status$$
CREATE PROCEDURE sp_update_milestone_status(
  IN p_milestone_id INT UNSIGNED,
  IN p_new_status   VARCHAR(20)
)
SQL SECURITY DEFINER
BEGIN
  DECLARE v_project_id INT UNSIGNED;
  DECLARE v_proj_status VARCHAR(20);
  DECLARE v_p_start DATE;
  DECLARE v_p_end DATE;
  DECLARE v_due_date DATE;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
  START TRANSACTION;

  -- Verify status value
  IF p_new_status NOT IN ('Pending', 'In Progress', 'Delayed') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'sp_update_milestone_status only accepts Pending, In Progress, or Delayed. Use sp_complete_milestone for Completed';
  END IF;

  -- 1. Read project_id without lock
  SELECT project_id INTO v_project_id FROM milestone WHERE milestone_id = p_milestone_id;
  IF v_project_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Milestone not found';
  END IF;

  -- 2. Lock project first (matches project closure lock order)
  SELECT status, start_date, end_date
    INTO v_proj_status, v_p_start, v_p_end
    FROM project
   WHERE project_id = v_project_id
     FOR UPDATE;

  IF v_proj_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: This project is closed, so new expenses or milestones cannot be added';
  END IF;

  -- 3. Lock milestone row
  SELECT due_date INTO v_due_date
    FROM milestone
   WHERE milestone_id = p_milestone_id
     FOR UPDATE;

  IF v_due_date < v_p_start OR v_due_date > v_p_end THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-04: The milestone due date must fall inside the project dates';
  END IF;

  -- Update status and ensure completed_date is NULL (BR-13)
  UPDATE milestone
     SET status = p_new_status,
         completed_date = NULL
   WHERE milestone_id = p_milestone_id;

  COMMIT;
END$$


-- ----------------------------------------------------------------------------
-- 7. sp_complete_milestone
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_complete_milestone$$
CREATE PROCEDURE sp_complete_milestone(
  IN p_milestone_id    INT UNSIGNED,
  IN p_completed_date  DATE
)
SQL SECURITY DEFINER
BEGIN
  DECLARE v_project_id INT UNSIGNED;
  DECLARE v_proj_status VARCHAR(20);
  DECLARE v_p_start DATE;
  DECLARE v_p_end DATE;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
  START TRANSACTION;

  IF p_completed_date IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-13: A completed milestone needs a completion date';
  END IF;

  -- 1. Read project_id without lock
  SELECT project_id INTO v_project_id FROM milestone WHERE milestone_id = p_milestone_id;
  IF v_project_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Milestone not found';
  END IF;

  -- 2. Lock project first
  SELECT status, start_date, end_date
    INTO v_proj_status, v_p_start, v_p_end
    FROM project
   WHERE project_id = v_project_id
     FOR UPDATE;

  IF v_proj_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: This project is closed, so new expenses or milestones cannot be added';
  END IF;

  IF p_completed_date < v_p_start OR p_completed_date > v_p_end THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-04: The milestone completion date must fall inside the project dates';
  END IF;

  -- 3. Lock milestone row
  SELECT project_id FROM milestone WHERE milestone_id = p_milestone_id FOR UPDATE;

  UPDATE milestone
     SET status = 'Completed',
         completed_date = p_completed_date
   WHERE milestone_id = p_milestone_id;

  COMMIT;
END$$


-- ----------------------------------------------------------------------------
-- 8. sp_update_project_status
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_update_project_status$$
CREATE PROCEDURE sp_update_project_status(
  IN p_project_id INT UNSIGNED,
  IN p_new_status VARCHAR(20)
)
SQL SECURITY DEFINER
BEGIN
  DECLARE v_curr_status VARCHAR(20);
  DECLARE done INT DEFAULT FALSE;
  DECLARE v_res_id INT UNSIGNED;
  DECLARE v_effort DECIMAL(7,2);

  DECLARE cur_researchers CURSOR FOR
    SELECT DISTINCT pi.researcher_id
      FROM project_investigator AS pi
     WHERE pi.project_id = p_project_id
     ORDER BY pi.researcher_id ASC;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
  START TRANSACTION;

  IF p_new_status NOT IN ('Proposed', 'Active', 'On Hold') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'sp_update_project_status only accepts Proposed, Active, or On Hold. Use sp_close_project for Completed or Cancelled';
  END IF;

  SELECT status INTO v_curr_status
    FROM project
   WHERE project_id = p_project_id
     FOR UPDATE;

  IF v_curr_status IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Project not found';
  END IF;

  IF v_curr_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Cannot modify status of a completed or cancelled project';
  END IF;

  -- When switching into Proposed or Active, lock researchers in ascending order and verify effort (BR-11)
  IF p_new_status IN ('Proposed', 'Active') AND v_curr_status NOT IN ('Proposed', 'Active') THEN
    OPEN cur_researchers;
    read_loop: LOOP
      FETCH cur_researchers INTO v_res_id;
      IF done THEN
        LEAVE read_loop;
      END IF;

      -- Lock researcher
      SELECT researcher_id FROM researcher WHERE researcher_id = v_res_id FOR UPDATE;

      -- Check workload including this project
      SELECT COALESCE(SUM(pi.effort_percent), 0)
        INTO v_effort
        FROM project_investigator AS pi
        JOIN project AS p ON p.project_id = pi.project_id
       WHERE pi.researcher_id = v_res_id
         AND (p.status IN ('Proposed', 'Active') OR p.project_id = p_project_id);

      IF v_effort > 100.00 THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'BR-11: Transitioning project to Proposed/Active exceeds 100% effort limit for assigned team member';
      END IF;
    END LOOP;
    CLOSE cur_researchers;
  END IF;

  UPDATE project SET status = p_new_status WHERE project_id = p_project_id;

  COMMIT;
END$$


-- ----------------------------------------------------------------------------
-- 9. sp_close_project
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_close_project$$
CREATE PROCEDURE sp_close_project(
  IN p_project_id INT UNSIGNED,
  IN p_new_status VARCHAR(20)
)
SQL SECURITY DEFINER
BEGIN
  DECLARE v_curr_status VARCHAR(20);
  DECLARE v_unfinished_count INT;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
  START TRANSACTION;

  IF p_new_status NOT IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'sp_close_project only accepts Completed or Cancelled';
  END IF;

  SELECT status INTO v_curr_status
    FROM project
   WHERE project_id = p_project_id
     FOR UPDATE;

  IF v_curr_status IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Project not found';
  END IF;

  IF v_curr_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Project is already closed';
  END IF;

  -- For Completed, verify no unfinished milestones remain
  IF p_new_status = 'Completed' THEN
    SELECT COUNT(*)
      INTO v_unfinished_count
      FROM milestone
     WHERE project_id = p_project_id
       AND status IN ('Pending', 'In Progress', 'Delayed');

    IF v_unfinished_count > 0 THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Cannot complete project while unfinished milestones remain';
    END IF;
  END IF;

  -- Update project status
  UPDATE project SET status = p_new_status WHERE project_id = p_project_id;

  -- Close or Terminate active/sanctioned grants
  IF p_new_status = 'Completed' THEN
    UPDATE grant_award
       SET status = 'Closed'
     WHERE project_id = p_project_id
       AND status IN ('Sanctioned', 'Active');
  ELSE
    UPDATE grant_award
       SET status = 'Terminated'
     WHERE project_id = p_project_id
       AND status IN ('Sanctioned', 'Active');
  END IF;

  COMMIT;
END$$


-- ----------------------------------------------------------------------------
-- 10. sp_change_project_pi
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_change_project_pi$$
CREATE PROCEDURE sp_change_project_pi(
  IN p_project_id        INT UNSIGNED,
  IN p_new_res_id        INT UNSIGNED,
  IN p_new_effort        DECIMAL(5,2)
)
SQL SECURITY DEFINER
BEGIN
  DECLARE v_old_res_id INT UNSIGNED;
  DECLARE v_proj_status VARCHAR(20);
  DECLARE v_is_active BOOLEAN;
  DECLARE v_lock_first INT UNSIGNED;
  DECLARE v_lock_second INT UNSIGNED;
  DECLARE v_curr_effort DECIMAL(7,2);
  DECLARE v_already_assigned INT;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    SET @rpgms_pi_transfer = NULL;
    ROLLBACK;
    RESIGNAL;
  END;

  SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
  START TRANSACTION;

  IF p_new_effort <= 0 OR p_new_effort > 100 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Effort percentage must be between 1 and 100';
  END IF;

  -- 1. Lock project
  SELECT status INTO v_proj_status
    FROM project
   WHERE project_id = p_project_id
     FOR UPDATE;

  IF v_proj_status IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Project not found';
  END IF;

  IF v_proj_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: Cannot change PI on a closed project';
  END IF;

  -- 2. Find current PI
  SELECT researcher_id INTO v_old_res_id
    FROM project_investigator
   WHERE project_id = p_project_id
     AND role = 'PI';

  IF v_old_res_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Project currently has no PI assigned';
  END IF;

  IF v_old_res_id = p_new_res_id THEN
    -- Same researcher: just update effort
    UPDATE project_investigator
       SET effort_percent = p_new_effort
     WHERE project_id = p_project_id AND researcher_id = p_new_res_id;
    COMMIT;
  ELSE
    -- 3. Lock old and new researchers in ascending ID order to prevent deadlocks
    IF v_old_res_id < p_new_res_id THEN
      SET v_lock_first = v_old_res_id;
      SET v_lock_second = p_new_res_id;
    ELSE
      SET v_lock_first = p_new_res_id;
      SET v_lock_second = v_old_res_id;
    END IF;

    SELECT researcher_id FROM researcher WHERE researcher_id = v_lock_first FOR UPDATE;
    SELECT researcher_id FROM researcher WHERE researcher_id = v_lock_second FOR UPDATE;

    -- Validate new researcher is active (BR-12)
    SELECT is_active INTO v_is_active FROM researcher WHERE researcher_id = p_new_res_id;
    IF v_is_active IS NULL OR v_is_active = FALSE THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'BR-12: Inactive researchers cannot be assigned to projects';
    END IF;

    -- 4. Validate workload for new PI on Proposed/Active projects (BR-11)
    SELECT COALESCE(SUM(pi.effort_percent), 0)
      INTO v_curr_effort
      FROM project_investigator AS pi
      JOIN project AS p ON p.project_id = pi.project_id
     WHERE pi.researcher_id = p_new_res_id
       AND p.project_id <> p_project_id
       AND p.status IN ('Proposed', 'Active');

    IF (v_curr_effort + p_new_effort) > 100.00 THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'BR-11: This assignment would exceed the 100% effort limit across active projects';
    END IF;

    -- 5. Atomic PI transfer with controlled session flag
    SET @rpgms_pi_transfer = 1;

    -- Demote old PI to Co-PI
    UPDATE project_investigator
       SET role = 'Co-PI'
     WHERE project_id = p_project_id
       AND researcher_id = v_old_res_id;

    -- Check if new researcher is already on project team
    SELECT COUNT(*) INTO v_already_assigned
      FROM project_investigator
     WHERE project_id = p_project_id
       AND researcher_id = p_new_res_id;

    IF v_already_assigned > 0 THEN
      UPDATE project_investigator
         SET role = 'PI',
             effort_percent = p_new_effort
       WHERE project_id = p_project_id
         AND researcher_id = p_new_res_id;
    ELSE
      INSERT INTO project_investigator (project_id, researcher_id, role, assigned_date, effort_percent)
      VALUES (p_project_id, p_new_res_id, 'PI', CURDATE(), p_new_effort);
    END IF;

    SET @rpgms_pi_transfer = NULL;

    COMMIT;
  END IF;
END$$

DELIMITER ;
