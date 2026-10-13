-- ============================================================================
-- RPGMS Business Rule & Audit Triggers
-- File: db/02_triggers.sql
-- Description: Triggers enforcing business rules BR-02, BR-03, BR-04, BR-07,
--              BR-09, BR-10, BR-12, BR-16, BR-17, and comprehensive audit logs.
-- Note: Does NOT calculate BR-06 or BR-11 aggregates (handled in procedures).
-- ============================================================================

DELIMITER $$

-- ----------------------------------------------------------------------------
-- 1. EXPENDITURE TRIGGERS (BR-07, BR-17)
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_expenditure_bi$$
CREATE TRIGGER trg_expenditure_bi BEFORE INSERT ON expenditure
FOR EACH ROW
BEGIN
  DECLARE v_start DATE;
  DECLARE v_end DATE;
  DECLARE v_project_status VARCHAR(20);

  SELECT g.grant_start, g.grant_end, p.status
    INTO v_start, v_end, v_project_status
    FROM grant_award AS g
    JOIN project AS p ON p.project_id = g.project_id
   WHERE g.grant_id = NEW.grant_id;

  IF v_project_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: This project is closed, so new expenses or milestones cannot be added';
  END IF;

  IF NEW.expense_date < v_start OR NEW.expense_date > v_end THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-07: The expense date must be within the grant period';
  END IF;
END$$

DROP TRIGGER IF EXISTS trg_expenditure_bu$$
CREATE TRIGGER trg_expenditure_bu BEFORE UPDATE ON expenditure
FOR EACH ROW
BEGIN
  DECLARE v_start DATE;
  DECLARE v_end DATE;
  DECLARE v_project_status VARCHAR(20);

  SELECT g.grant_start, g.grant_end, p.status
    INTO v_start, v_end, v_project_status
    FROM grant_award AS g
    JOIN project AS p ON p.project_id = g.project_id
   WHERE g.grant_id = NEW.grant_id;

  IF v_project_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: This project is closed, so new expenses or milestones cannot be added';
  END IF;

  IF NEW.expense_date < v_start OR NEW.expense_date > v_end THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-07: The expense date must be within the grant period';
  END IF;
END$$


-- ----------------------------------------------------------------------------
-- 2. GRANT AWARD TRIGGERS (BR-02, BR-03, BR-07, BR-09, BR-17)
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_grant_award_bi$$
CREATE TRIGGER trg_grant_award_bi BEFORE INSERT ON grant_award
FOR EACH ROW
BEGIN
  DECLARE v_p_start DATE;
  DECLARE v_p_end DATE;
  DECLARE v_p_status VARCHAR(20);

  SELECT start_date, end_date, status
    INTO v_p_start, v_p_end, v_p_status
    FROM project
   WHERE project_id = NEW.project_id;

  IF v_p_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: Cannot add a grant to a completed or cancelled project';
  END IF;

  IF NEW.grant_start < v_p_start OR NEW.grant_end > v_p_end THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-03: The grant period must fall inside the project dates';
  END IF;
END$$

DROP TRIGGER IF EXISTS trg_grant_award_bu$$
CREATE TRIGGER trg_grant_award_bu BEFORE UPDATE ON grant_award
FOR EACH ROW
BEGIN
  DECLARE v_p_start DATE;
  DECLARE v_p_end DATE;
  DECLARE v_min_exp DATE;
  DECLARE v_max_exp DATE;
  DECLARE v_total_allocated DECIMAL(14,2);
  DECLARE v_total_spent DECIMAL(14,2);

  SELECT start_date, end_date
    INTO v_p_start, v_p_end
    FROM project
   WHERE project_id = NEW.project_id;

  IF NEW.grant_start < v_p_start OR NEW.grant_end > v_p_end THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-03: The grant period must fall inside the project dates';
  END IF;

  -- BR-02 / BR-07: Verify changing dates does not strand existing expenditures
  SELECT MIN(expense_date), MAX(expense_date)
    INTO v_min_exp, v_max_exp
    FROM expenditure
   WHERE grant_id = NEW.grant_id;

  IF v_min_exp IS NOT NULL AND (v_min_exp < NEW.grant_start OR v_max_exp > NEW.grant_end) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-02: Changing grant dates would strand existing expenditures outside the new period';
  END IF;

  -- BR-09: Grant amount cannot be reduced below existing allocations or spending
  SELECT COALESCE(SUM(allocated_amount), 0)
    INTO v_total_allocated
    FROM grant_budget_allocation
   WHERE grant_id = NEW.grant_id;

  SELECT COALESCE(SUM(amount), 0)
    INTO v_total_spent
    FROM expenditure
   WHERE grant_id = NEW.grant_id;

  IF NEW.grant_amount < v_total_allocated THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-09: Grant amount cannot be reduced below existing allocations';
  END IF;

  IF NEW.grant_amount < v_total_spent THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-09: Grant amount cannot be reduced below existing spending';
  END IF;
END$$


-- ----------------------------------------------------------------------------
-- 3. PROJECT TRIGGERS (BR-03, BR-04, BR-16)
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_project_bu$$
CREATE TRIGGER trg_project_bu BEFORE UPDATE ON project
FOR EACH ROW
BEGIN
  DECLARE v_invalid_grants INT;
  DECLARE v_invalid_milestones INT;
  DECLARE v_invalid_pubs INT;

  -- BR-03: Check existing grants stay within new project dates
  SELECT COUNT(*)
    INTO v_invalid_grants
    FROM grant_award
   WHERE project_id = NEW.project_id
     AND (grant_start < NEW.start_date OR grant_end > NEW.end_date);

  IF v_invalid_grants > 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-03: Changing project dates would strand existing grants outside the project lifetime';
  END IF;

  -- BR-04: Check existing milestones stay within new project dates
  SELECT COUNT(*)
    INTO v_invalid_milestones
    FROM milestone
   WHERE project_id = NEW.project_id
     AND (due_date < NEW.start_date OR due_date > NEW.end_date
          OR (completed_date IS NOT NULL AND (completed_date < NEW.start_date OR completed_date > NEW.end_date)));

  IF v_invalid_milestones > 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-04: Changing project dates would strand existing milestones outside the project lifetime';
  END IF;

  -- BR-16: Check linked publications do not predate new project start_date
  IF NEW.start_date <> OLD.start_date THEN
    SELECT COUNT(*)
      INTO v_invalid_pubs
      FROM project_publication AS pp
      JOIN publication AS pub ON pub.publication_id = pp.publication_id
     WHERE pp.project_id = NEW.project_id
       AND pub.pub_date < NEW.start_date;

    IF v_invalid_pubs > 0 THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'BR-16: Changing project start date would predate existing linked publications';
    END IF;
  END IF;
END$$


-- ----------------------------------------------------------------------------
-- 4. MILESTONE TRIGGERS (BR-04, BR-17)
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_milestone_bi$$
CREATE TRIGGER trg_milestone_bi BEFORE INSERT ON milestone
FOR EACH ROW
BEGIN
  DECLARE v_p_start DATE;
  DECLARE v_p_end DATE;
  DECLARE v_p_status VARCHAR(20);

  SELECT start_date, end_date, status
    INTO v_p_start, v_p_end, v_p_status
    FROM project
   WHERE project_id = NEW.project_id;

  IF v_p_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: This project is closed, so new expenses or milestones cannot be added';
  END IF;

  IF NEW.due_date < v_p_start OR NEW.due_date > v_p_end THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-04: The milestone due date must fall inside the project dates';
  END IF;

  IF NEW.completed_date IS NOT NULL AND (NEW.completed_date < v_p_start OR NEW.completed_date > v_p_end) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-04: The milestone completion date must fall inside the project dates';
  END IF;
END$$

DROP TRIGGER IF EXISTS trg_milestone_bu$$
CREATE TRIGGER trg_milestone_bu BEFORE UPDATE ON milestone
FOR EACH ROW
BEGIN
  DECLARE v_p_start DATE;
  DECLARE v_p_end DATE;
  DECLARE v_p_status VARCHAR(20);

  SELECT start_date, end_date, status
    INTO v_p_start, v_p_end, v_p_status
    FROM project
   WHERE project_id = NEW.project_id;

  IF v_p_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: This project is closed, so new expenses or milestones cannot be added';
  END IF;

  IF NEW.due_date < v_p_start OR NEW.due_date > v_p_end THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-04: The milestone due date must fall inside the project dates';
  END IF;

  IF NEW.completed_date IS NOT NULL AND (NEW.completed_date < v_p_start OR NEW.completed_date > v_p_end) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-04: The milestone completion date must fall inside the project dates';
  END IF;
END$$


-- ----------------------------------------------------------------------------
-- 5. PROJECT INVESTIGATOR TRIGGERS (BR-10, BR-12, BR-17)
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_project_investigator_bi$$
CREATE TRIGGER trg_project_investigator_bi BEFORE INSERT ON project_investigator
FOR EACH ROW
BEGIN
  DECLARE v_res_active BOOLEAN;
  DECLARE v_proj_status VARCHAR(20);

  SELECT is_active INTO v_res_active FROM researcher WHERE researcher_id = NEW.researcher_id;
  IF v_res_active IS NULL OR v_res_active = FALSE THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-12: Inactive researchers cannot be assigned to projects';
  END IF;

  SELECT status INTO v_proj_status FROM project WHERE project_id = NEW.project_id;
  IF v_proj_status IN ('Completed', 'Cancelled') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-17: Cannot assign researchers to a completed or cancelled project';
  END IF;
END$$

DROP TRIGGER IF EXISTS trg_project_investigator_bu$$
CREATE TRIGGER trg_project_investigator_bu BEFORE UPDATE ON project_investigator
FOR EACH ROW
BEGIN
  DECLARE v_res_active BOOLEAN;

  SELECT is_active INTO v_res_active FROM researcher WHERE researcher_id = NEW.researcher_id;
  IF v_res_active IS NULL OR v_res_active = FALSE THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-12: Inactive researchers cannot be assigned to projects';
  END IF;

  -- BR-10: Guard PI from accidental role demotion without controlled procedure
  IF OLD.role = 'PI' AND NEW.role <> 'PI' AND @rpgms_pi_transfer IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-10: Cannot demote PI without transfer procedure';
  END IF;
END$$

DROP TRIGGER IF EXISTS trg_project_investigator_bd$$
CREATE TRIGGER trg_project_investigator_bd BEFORE DELETE ON project_investigator
FOR EACH ROW
BEGIN
  -- BR-10: Guard PI from removal without controlled transfer procedure
  IF OLD.role = 'PI' AND @rpgms_pi_transfer IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-10: This project must have exactly one Principal Investigator. Use Change PI to transfer responsibility';
  END IF;
END$$


-- ----------------------------------------------------------------------------
-- 6. PUBLICATION & PROJECT PUBLICATION TRIGGERS (BR-16)
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_project_publication_bi$$
CREATE TRIGGER trg_project_publication_bi BEFORE INSERT ON project_publication
FOR EACH ROW
BEGIN
  DECLARE v_p_start DATE;
  DECLARE v_pub_date DATE;

  SELECT start_date INTO v_p_start FROM project WHERE project_id = NEW.project_id;
  SELECT pub_date INTO v_pub_date FROM publication WHERE publication_id = NEW.publication_id;

  IF v_pub_date < v_p_start THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-16: The publication date cannot be earlier than the start date of a linked project';
  END IF;
END$$

DROP TRIGGER IF EXISTS trg_project_publication_bu$$
CREATE TRIGGER trg_project_publication_bu BEFORE UPDATE ON project_publication
FOR EACH ROW
BEGIN
  DECLARE v_p_start DATE;
  DECLARE v_pub_date DATE;

  SELECT start_date INTO v_p_start FROM project WHERE project_id = NEW.project_id;
  SELECT pub_date INTO v_pub_date FROM publication WHERE publication_id = NEW.publication_id;

  IF v_pub_date < v_p_start THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'BR-16: The publication date cannot be earlier than the start date of a linked project';
  END IF;
END$$

DROP TRIGGER IF EXISTS trg_publication_bu$$
CREATE TRIGGER trg_publication_bu BEFORE UPDATE ON publication
FOR EACH ROW
BEGIN
  DECLARE v_invalid_count INT;

  IF NEW.pub_date <> OLD.pub_date THEN
    SELECT COUNT(*)
      INTO v_invalid_count
      FROM project_publication AS pp
      JOIN project AS p ON p.project_id = pp.project_id
     WHERE pp.publication_id = NEW.publication_id
       AND NEW.pub_date < p.start_date;

    IF v_invalid_count > 0 THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'BR-16: The publication date cannot be earlier than the start date of a linked project';
    END IF;
  END IF;
END$$


-- ----------------------------------------------------------------------------
-- 7. AUDIT LOG TRIGGERS (AFTER INSERT / UPDATE / DELETE)
-- ----------------------------------------------------------------------------

-- Helper pattern: writes JSON_OBJECT into audit_log with actor identity

-- 7.1 department
DROP TRIGGER IF EXISTS trg_audit_department_ai$$
CREATE TRIGGER trg_audit_department_ai AFTER INSERT ON department FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('department', CAST(NEW.dept_id AS CHAR), 'INSERT', NULL,
          JSON_OBJECT('dept_id', NEW.dept_id, 'dept_code', NEW.dept_code, 'dept_name', NEW.dept_name),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_department_au$$
CREATE TRIGGER trg_audit_department_au AFTER UPDATE ON department FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('department', CAST(NEW.dept_id AS CHAR), 'UPDATE',
          JSON_OBJECT('dept_id', OLD.dept_id, 'dept_code', OLD.dept_code, 'dept_name', OLD.dept_name),
          JSON_OBJECT('dept_id', NEW.dept_id, 'dept_code', NEW.dept_code, 'dept_name', NEW.dept_name),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_department_ad$$
CREATE TRIGGER trg_audit_department_ad AFTER DELETE ON department FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('department', CAST(OLD.dept_id AS CHAR), 'DELETE',
          JSON_OBJECT('dept_id', OLD.dept_id, 'dept_code', OLD.dept_code, 'dept_name', OLD.dept_name), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.2 researcher
DROP TRIGGER IF EXISTS trg_audit_researcher_ai$$
CREATE TRIGGER trg_audit_researcher_ai AFTER INSERT ON researcher FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('researcher', CAST(NEW.researcher_id AS CHAR), 'INSERT', NULL,
          JSON_OBJECT('researcher_id', NEW.researcher_id, 'name', CONCAT(NEW.first_name, ' ', NEW.last_name), 'email', NEW.email, 'dept_id', NEW.dept_id, 'is_active', NEW.is_active),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_researcher_au$$
CREATE TRIGGER trg_audit_researcher_au AFTER UPDATE ON researcher FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('researcher', CAST(NEW.researcher_id AS CHAR), 'UPDATE',
          JSON_OBJECT('researcher_id', OLD.researcher_id, 'name', CONCAT(OLD.first_name, ' ', OLD.last_name), 'email', OLD.email, 'dept_id', OLD.dept_id, 'is_active', OLD.is_active),
          JSON_OBJECT('researcher_id', NEW.researcher_id, 'name', CONCAT(NEW.first_name, ' ', NEW.last_name), 'email', NEW.email, 'dept_id', NEW.dept_id, 'is_active', NEW.is_active),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_researcher_ad$$
CREATE TRIGGER trg_audit_researcher_ad AFTER DELETE ON researcher FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('researcher', CAST(OLD.researcher_id AS CHAR), 'DELETE',
          JSON_OBJECT('researcher_id', OLD.researcher_id, 'name', CONCAT(OLD.first_name, ' ', OLD.last_name), 'email', OLD.email), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.3 user_account (IMPORTANT: never log password_hash)
DROP TRIGGER IF EXISTS trg_audit_user_account_ai$$
CREATE TRIGGER trg_audit_user_account_ai AFTER INSERT ON user_account FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('user_account', CAST(NEW.user_id AS CHAR), 'INSERT', NULL,
          JSON_OBJECT('user_id', NEW.user_id, 'username', NEW.username, 'role', NEW.role, 'researcher_id', NEW.researcher_id, 'is_active', NEW.is_active),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_user_account_au$$
CREATE TRIGGER trg_audit_user_account_au AFTER UPDATE ON user_account FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('user_account', CAST(NEW.user_id AS CHAR), 'UPDATE',
          JSON_OBJECT('user_id', OLD.user_id, 'username', OLD.username, 'role', OLD.role, 'researcher_id', OLD.researcher_id, 'is_active', OLD.is_active),
          JSON_OBJECT('user_id', NEW.user_id, 'username', NEW.username, 'role', NEW.role, 'researcher_id', NEW.researcher_id, 'is_active', NEW.is_active),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_user_account_ad$$
CREATE TRIGGER trg_audit_user_account_ad AFTER DELETE ON user_account FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('user_account', CAST(OLD.user_id AS CHAR), 'DELETE',
          JSON_OBJECT('user_id', OLD.user_id, 'username', OLD.username, 'role', OLD.role), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.4 project
DROP TRIGGER IF EXISTS trg_audit_project_ai$$
CREATE TRIGGER trg_audit_project_ai AFTER INSERT ON project FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('project', CAST(NEW.project_id AS CHAR), 'INSERT', NULL,
          JSON_OBJECT('project_id', NEW.project_id, 'code', NEW.project_code, 'title', NEW.title, 'dept_id', NEW.dept_id, 'status', NEW.status),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_project_au$$
CREATE TRIGGER trg_audit_project_au AFTER UPDATE ON project FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('project', CAST(NEW.project_id AS CHAR), 'UPDATE',
          JSON_OBJECT('project_id', OLD.project_id, 'code', OLD.project_code, 'title', OLD.title, 'status', OLD.status),
          JSON_OBJECT('project_id', NEW.project_id, 'code', NEW.project_code, 'title', NEW.title, 'status', NEW.status),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_project_ad$$
CREATE TRIGGER trg_audit_project_ad AFTER DELETE ON project FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('project', CAST(OLD.project_id AS CHAR), 'DELETE',
          JSON_OBJECT('project_id', OLD.project_id, 'code', OLD.project_code, 'title', OLD.title), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.5 project_investigator
DROP TRIGGER IF EXISTS trg_audit_project_investigator_ai$$
CREATE TRIGGER trg_audit_project_investigator_ai AFTER INSERT ON project_investigator FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('project_investigator', CONCAT(NEW.project_id, ':', NEW.researcher_id), 'INSERT', NULL,
          JSON_OBJECT('project_id', NEW.project_id, 'researcher_id', NEW.researcher_id, 'role', NEW.role, 'effort_percent', NEW.effort_percent),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_project_investigator_au$$
CREATE TRIGGER trg_audit_project_investigator_au AFTER UPDATE ON project_investigator FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('project_investigator', CONCAT(NEW.project_id, ':', NEW.researcher_id), 'UPDATE',
          JSON_OBJECT('role', OLD.role, 'effort_percent', OLD.effort_percent),
          JSON_OBJECT('role', NEW.role, 'effort_percent', NEW.effort_percent),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_project_investigator_ad$$
CREATE TRIGGER trg_audit_project_investigator_ad AFTER DELETE ON project_investigator FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('project_investigator', CONCAT(OLD.project_id, ':', OLD.researcher_id), 'DELETE',
          JSON_OBJECT('project_id', OLD.project_id, 'researcher_id', OLD.researcher_id, 'role', OLD.role), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.6 grant_award
DROP TRIGGER IF EXISTS trg_audit_grant_award_ai$$
CREATE TRIGGER trg_audit_grant_award_ai AFTER INSERT ON grant_award FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('grant_award', CAST(NEW.grant_id AS CHAR), 'INSERT', NULL,
          JSON_OBJECT('grant_id', NEW.grant_id, 'grant_number', NEW.grant_number, 'amount', NEW.grant_amount, 'status', NEW.status),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_grant_award_au$$
CREATE TRIGGER trg_audit_grant_award_au AFTER UPDATE ON grant_award FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('grant_award', CAST(NEW.grant_id AS CHAR), 'UPDATE',
          JSON_OBJECT('grant_number', OLD.grant_number, 'amount', OLD.grant_amount, 'status', OLD.status),
          JSON_OBJECT('grant_number', NEW.grant_number, 'amount', NEW.grant_amount, 'status', NEW.status),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_grant_award_ad$$
CREATE TRIGGER trg_audit_grant_award_ad AFTER DELETE ON grant_award FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('grant_award', CAST(OLD.grant_id AS CHAR), 'DELETE',
          JSON_OBJECT('grant_id', OLD.grant_id, 'grant_number', OLD.grant_number), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.7 grant_budget_allocation
DROP TRIGGER IF EXISTS trg_audit_grant_budget_allocation_ai$$
CREATE TRIGGER trg_audit_grant_budget_allocation_ai AFTER INSERT ON grant_budget_allocation FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('grant_budget_allocation', CONCAT(NEW.grant_id, ':', NEW.head_id), 'INSERT', NULL,
          JSON_OBJECT('grant_id', NEW.grant_id, 'head_id', NEW.head_id, 'allocated_amount', NEW.allocated_amount),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_grant_budget_allocation_au$$
CREATE TRIGGER trg_audit_grant_budget_allocation_au AFTER UPDATE ON grant_budget_allocation FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('grant_budget_allocation', CONCAT(NEW.grant_id, ':', NEW.head_id), 'UPDATE',
          JSON_OBJECT('allocated_amount', OLD.allocated_amount),
          JSON_OBJECT('allocated_amount', NEW.allocated_amount),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_grant_budget_allocation_ad$$
CREATE TRIGGER trg_audit_grant_budget_allocation_ad AFTER DELETE ON grant_budget_allocation FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('grant_budget_allocation', CONCAT(OLD.grant_id, ':', OLD.head_id), 'DELETE',
          JSON_OBJECT('grant_id', OLD.grant_id, 'head_id', OLD.head_id, 'allocated_amount', OLD.allocated_amount), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.8 expenditure
DROP TRIGGER IF EXISTS trg_audit_expenditure_ai$$
CREATE TRIGGER trg_audit_expenditure_ai AFTER INSERT ON expenditure FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('expenditure', CAST(NEW.expenditure_id AS CHAR), 'INSERT', NULL,
          JSON_OBJECT('expenditure_id', NEW.expenditure_id, 'grant_id', NEW.grant_id, 'head_id', NEW.head_id, 'amount', NEW.amount, 'voucher_no', NEW.voucher_no),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_expenditure_au$$
CREATE TRIGGER trg_audit_expenditure_au AFTER UPDATE ON expenditure FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('expenditure', CAST(NEW.expenditure_id AS CHAR), 'UPDATE',
          JSON_OBJECT('expenditure_id', OLD.expenditure_id, 'amount', OLD.amount, 'voucher_no', OLD.voucher_no),
          JSON_OBJECT('expenditure_id', NEW.expenditure_id, 'amount', NEW.amount, 'voucher_no', NEW.voucher_no),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_expenditure_ad$$
CREATE TRIGGER trg_audit_expenditure_ad AFTER DELETE ON expenditure FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('expenditure', CAST(OLD.expenditure_id AS CHAR), 'DELETE',
          JSON_OBJECT('expenditure_id', OLD.expenditure_id, 'voucher_no', OLD.voucher_no, 'amount', OLD.amount), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.9 milestone
DROP TRIGGER IF EXISTS trg_audit_milestone_ai$$
CREATE TRIGGER trg_audit_milestone_ai AFTER INSERT ON milestone FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('milestone', CAST(NEW.milestone_id AS CHAR), 'INSERT', NULL,
          JSON_OBJECT('milestone_id', NEW.milestone_id, 'project_id', NEW.project_id, 'title', NEW.title, 'status', NEW.status, 'due_date', NEW.due_date),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_milestone_au$$
CREATE TRIGGER trg_audit_milestone_au AFTER UPDATE ON milestone FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('milestone', CAST(NEW.milestone_id AS CHAR), 'UPDATE',
          JSON_OBJECT('status', OLD.status, 'completed_date', OLD.completed_date),
          JSON_OBJECT('status', NEW.status, 'completed_date', NEW.completed_date),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_milestone_ad$$
CREATE TRIGGER trg_audit_milestone_ad AFTER DELETE ON milestone FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('milestone', CAST(OLD.milestone_id AS CHAR), 'DELETE',
          JSON_OBJECT('milestone_id', OLD.milestone_id, 'title', OLD.title), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.10 publication
DROP TRIGGER IF EXISTS trg_audit_publication_ai$$
CREATE TRIGGER trg_audit_publication_ai AFTER INSERT ON publication FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('publication', CAST(NEW.publication_id AS CHAR), 'INSERT', NULL,
          JSON_OBJECT('publication_id', NEW.publication_id, 'title', NEW.title, 'doi', NEW.doi, 'pub_type', NEW.pub_type),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_publication_au$$
CREATE TRIGGER trg_audit_publication_au AFTER UPDATE ON publication FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('publication', CAST(NEW.publication_id AS CHAR), 'UPDATE',
          JSON_OBJECT('title', OLD.title, 'doi', OLD.doi),
          JSON_OBJECT('title', NEW.title, 'doi', NEW.doi),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_publication_ad$$
CREATE TRIGGER trg_audit_publication_ad AFTER DELETE ON publication FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('publication', CAST(OLD.publication_id AS CHAR), 'DELETE',
          JSON_OBJECT('publication_id', OLD.publication_id, 'title', OLD.title), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.11 publication_author
DROP TRIGGER IF EXISTS trg_audit_publication_author_ai$$
CREATE TRIGGER trg_audit_publication_author_ai AFTER INSERT ON publication_author FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('publication_author', CONCAT(NEW.publication_id, ':', NEW.researcher_id), 'INSERT', NULL,
          JSON_OBJECT('publication_id', NEW.publication_id, 'researcher_id', NEW.researcher_id, 'author_order', NEW.author_order),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_publication_author_au$$
CREATE TRIGGER trg_audit_publication_author_au AFTER UPDATE ON publication_author FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('publication_author', CONCAT(NEW.publication_id, ':', NEW.researcher_id), 'UPDATE',
          JSON_OBJECT('author_order', OLD.author_order, 'is_corresponding', OLD.is_corresponding),
          JSON_OBJECT('author_order', NEW.author_order, 'is_corresponding', NEW.is_corresponding),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_publication_author_ad$$
CREATE TRIGGER trg_audit_publication_author_ad AFTER DELETE ON publication_author FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('publication_author', CONCAT(OLD.publication_id, ':', OLD.researcher_id), 'DELETE',
          JSON_OBJECT('publication_id', OLD.publication_id, 'researcher_id', OLD.researcher_id), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.12 project_publication
DROP TRIGGER IF EXISTS trg_audit_project_publication_ai$$
CREATE TRIGGER trg_audit_project_publication_ai AFTER INSERT ON project_publication FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('project_publication', CONCAT(NEW.project_id, ':', NEW.publication_id), 'INSERT', NULL,
          JSON_OBJECT('project_id', NEW.project_id, 'publication_id', NEW.publication_id),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_project_publication_ad$$
CREATE TRIGGER trg_audit_project_publication_ad AFTER DELETE ON project_publication FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('project_publication', CONCAT(OLD.project_id, ':', OLD.publication_id), 'DELETE',
          JSON_OBJECT('project_id', OLD.project_id, 'publication_id', OLD.publication_id), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.13 patent
DROP TRIGGER IF EXISTS trg_audit_patent_ai$$
CREATE TRIGGER trg_audit_patent_ai AFTER INSERT ON patent FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('patent', CAST(NEW.patent_id AS CHAR), 'INSERT', NULL,
          JSON_OBJECT('patent_id', NEW.patent_id, 'title', NEW.title, 'app_no', NEW.application_number, 'status', NEW.status),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_patent_au$$
CREATE TRIGGER trg_audit_patent_au AFTER UPDATE ON patent FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('patent', CAST(NEW.patent_id AS CHAR), 'UPDATE',
          JSON_OBJECT('status', OLD.status, 'patent_number', OLD.patent_number),
          JSON_OBJECT('status', NEW.status, 'patent_number', NEW.patent_number),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_patent_ad$$
CREATE TRIGGER trg_audit_patent_ad AFTER DELETE ON patent FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('patent', CAST(OLD.patent_id AS CHAR), 'DELETE',
          JSON_OBJECT('patent_id', OLD.patent_id, 'title', OLD.title), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.14 patent_inventor
DROP TRIGGER IF EXISTS trg_audit_patent_inventor_ai$$
CREATE TRIGGER trg_audit_patent_inventor_ai AFTER INSERT ON patent_inventor FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('patent_inventor', CONCAT(NEW.patent_id, ':', NEW.researcher_id), 'INSERT', NULL,
          JSON_OBJECT('patent_id', NEW.patent_id, 'researcher_id', NEW.researcher_id),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_patent_inventor_ad$$
CREATE TRIGGER trg_audit_patent_inventor_ad AFTER DELETE ON patent_inventor FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('patent_inventor', CONCAT(OLD.patent_id, ':', OLD.researcher_id), 'DELETE',
          JSON_OBJECT('patent_id', OLD.patent_id, 'researcher_id', OLD.researcher_id), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.15 project_patent
DROP TRIGGER IF EXISTS trg_audit_project_patent_ai$$
CREATE TRIGGER trg_audit_project_patent_ai AFTER INSERT ON project_patent FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('project_patent', CONCAT(NEW.project_id, ':', NEW.patent_id), 'INSERT', NULL,
          JSON_OBJECT('project_id', NEW.project_id, 'patent_id', NEW.patent_id),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_project_patent_ad$$
CREATE TRIGGER trg_audit_project_patent_ad AFTER DELETE ON project_patent FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('project_patent', CONCAT(OLD.project_id, ':', OLD.patent_id), 'DELETE',
          JSON_OBJECT('project_id', OLD.project_id, 'patent_id', OLD.patent_id), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

-- 7.16 report
DROP TRIGGER IF EXISTS trg_audit_report_ai$$
CREATE TRIGGER trg_audit_report_ai AFTER INSERT ON report FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('report', CAST(NEW.report_id AS CHAR), 'INSERT', NULL,
          JSON_OBJECT('report_id', NEW.report_id, 'project_id', NEW.project_id, 'type', NEW.report_type, 'status', NEW.status),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_report_au$$
CREATE TRIGGER trg_audit_report_au AFTER UPDATE ON report FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('report', CAST(NEW.report_id AS CHAR), 'UPDATE',
          JSON_OBJECT('status', OLD.status, 'submitted_on', OLD.submitted_on),
          JSON_OBJECT('status', NEW.status, 'submitted_on', NEW.submitted_on),
          COALESCE(@rpgms_actor, USER()));
END$$

DROP TRIGGER IF EXISTS trg_audit_report_ad$$
CREATE TRIGGER trg_audit_report_ad AFTER DELETE ON report FOR EACH ROW
BEGIN
  INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
  VALUES ('report', CAST(OLD.report_id AS CHAR), 'DELETE',
          JSON_OBJECT('report_id', OLD.report_id, 'project_id', OLD.project_id, 'type', OLD.report_type), NULL,
          COALESCE(@rpgms_actor, USER()));
END$$

DELIMITER ;
