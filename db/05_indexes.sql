-- ============================================================================
-- RPGMS Optimization Indexes
-- File: db/05_indexes.sql
-- Description: Composite, selective, and FULLTEXT indexes for frequently queried columns.
-- Note: Does NOT duplicate existing foreign-key support indexes.
-- ============================================================================

CREATE INDEX idx_proj_status_dept   ON project(status, dept_id);
CREATE INDEX idx_proj_dates         ON project(start_date, end_date);
CREATE INDEX idx_res_name           ON researcher(last_name, first_name);
CREATE INDEX idx_grant_agency       ON grant_award(agency_id, status);
CREATE INDEX idx_exp_grant_date     ON expenditure(grant_id, expense_date);
CREATE INDEX idx_ms_proj_status_due ON milestone(project_id, status, due_date);
CREATE INDEX idx_pub_date           ON publication(pub_date);
CREATE FULLTEXT INDEX ft_project_text ON project(title, abstract);
CREATE FULLTEXT INDEX ft_pub_title    ON publication(title);
