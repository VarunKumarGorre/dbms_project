-- ============================================================================
-- RPGMS Analytical & Operational Views
-- File: db/04_views.sql
-- Description: 9 authoritative views computing dynamic metrics without violating 3NF.
--              Employs subqueries/derived tables to prevent join fan-out inflation.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. vw_project_overview
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_project_overview AS
SELECT
  p.project_id,
  p.project_code,
  p.title,
  p.status,
  p.start_date,
  p.end_date,
  d.dept_id,
  d.dept_code,
  d.dept_name,
  pi.researcher_id AS pi_id,
  CONCAT(r.first_name, ' ', r.last_name) AS pi_name,
  r.email AS pi_email,
  COALESCE(g.total_grant_amount, 0.00) AS total_grant_amount,
  COALESCE(e.total_spent, 0.00) AS total_spent,
  (COALESCE(g.total_grant_amount, 0.00) - COALESCE(e.total_spent, 0.00)) AS balance,
  CASE
    WHEN COALESCE(g.total_grant_amount, 0.00) > 0
    THEN ROUND((COALESCE(e.total_spent, 0.00) / g.total_grant_amount) * 100, 2)
    ELSE 0.00
  END AS utilization_pct
FROM project AS p
JOIN department AS d ON d.dept_id = p.dept_id
LEFT JOIN project_investigator AS pi ON pi.project_id = p.project_id AND pi.role = 'PI'
LEFT JOIN researcher AS r ON r.researcher_id = pi.researcher_id
LEFT JOIN (
  SELECT project_id, SUM(grant_amount) AS total_grant_amount
  FROM grant_award
  GROUP BY project_id
) AS g ON g.project_id = p.project_id
LEFT JOIN (
  SELECT ga.project_id, SUM(exp.amount) AS total_spent
  FROM grant_award AS ga
  JOIN expenditure AS exp ON exp.grant_id = ga.grant_id
  GROUP BY ga.project_id
) AS e ON e.project_id = p.project_id;


-- ----------------------------------------------------------------------------
-- 2. vw_project_progress
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_project_progress AS
SELECT
  p.project_id,
  p.project_code,
  p.title,
  p.status,
  p.start_date,
  p.end_date,
  DATEDIFF(p.end_date, CURDATE()) AS days_remaining,
  -- Time elapsed clamped between 0 and 100%
  CASE
    WHEN CURDATE() <= p.start_date THEN 0.00
    WHEN CURDATE() >= p.end_date THEN 100.00
    ELSE ROUND((DATEDIFF(CURDATE(), p.start_date) / DATEDIFF(p.end_date, p.start_date)) * 100, 2)
  END AS time_elapsed_pct,
  COALESCE(m.total_milestones, 0) AS total_milestones,
  COALESCE(m.completed_milestones, 0) AS completed_milestones,
  COALESCE(m.overdue_milestones, 0) AS overdue_milestones,
  CASE
    WHEN COALESCE(m.total_milestones, 0) > 0
    THEN ROUND((m.completed_milestones / m.total_milestones) * 100, 2)
    ELSE NULL
  END AS milestone_completion_pct,
  -- RAG status determination rule
  CASE
    WHEN p.status IN ('Completed', 'Cancelled') THEN 'Closed'
    WHEN p.status = 'Proposed' OR CURDATE() < p.start_date THEN 'Not started'
    WHEN COALESCE(m.total_milestones, 0) = 0 THEN 'Not rated'
    WHEN m.overdue_milestones > 0
         AND (ROUND((DATEDIFF(CURDATE(), p.start_date) / DATEDIFF(p.end_date, p.start_date)) * 100, 2)
              - ROUND((m.completed_milestones / m.total_milestones) * 100, 2)) >= 15.00
      THEN 'Red'
    WHEN m.overdue_milestones > 0
         OR (ROUND((DATEDIFF(CURDATE(), p.start_date) / DATEDIFF(p.end_date, p.start_date)) * 100, 2)
             > ROUND((m.completed_milestones / m.total_milestones) * 100, 2))
      THEN 'Amber'
    ELSE 'Green'
  END AS rag_status
FROM project AS p
LEFT JOIN (
  SELECT
    project_id,
    COUNT(*) AS total_milestones,
    SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_milestones,
    SUM(CASE WHEN status <> 'Completed' AND due_date < CURDATE() THEN 1 ELSE 0 END) AS overdue_milestones
  FROM milestone
  GROUP BY project_id
) AS m ON m.project_id = p.project_id;


-- ----------------------------------------------------------------------------
-- 3. vw_budget_utilization
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_budget_utilization AS
SELECT
  g.grant_id,
  g.grant_number,
  g.project_id,
  p.project_code,
  p.title AS project_title,
  p.dept_id,
  a.agency_id,
  a.agency_name,
  g.grant_amount,
  g.status AS grant_status,
  COALESCE(e.total_spent, 0.00) AS total_spent,
  (g.grant_amount - COALESCE(e.total_spent, 0.00)) AS balance,
  ROUND((COALESCE(e.total_spent, 0.00) / g.grant_amount) * 100, 2) AS utilization_pct,
  CASE
    WHEN (g.grant_amount - COALESCE(e.total_spent, 0.00)) <= 0.00 THEN 'Exhausted'
    WHEN ROUND((COALESCE(e.total_spent, 0.00) / g.grant_amount) * 100, 2) >= 90.00 THEN 'Near Limit'
    WHEN ROUND((COALESCE(e.total_spent, 0.00) / g.grant_amount) * 100, 2) >= 50.00 THEN 'On Track'
    ELSE 'Under 50%'
  END AS health_status
FROM grant_award AS g
JOIN project AS p ON p.project_id = g.project_id
JOIN funding_agency AS a ON a.agency_id = g.agency_id
LEFT JOIN (
  SELECT grant_id, SUM(amount) AS total_spent
  FROM expenditure
  GROUP BY grant_id
) AS e ON e.grant_id = g.grant_id;


-- ----------------------------------------------------------------------------
-- 4. vw_budget_head_utilization
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_budget_head_utilization AS
SELECT
  gba.grant_id,
  ga.grant_number,
  ga.project_id,
  p.project_code,
  gba.head_id,
  bh.head_name,
  gba.allocated_amount,
  COALESCE(exp.spent_amount, 0.00) AS spent_amount,
  (gba.allocated_amount - COALESCE(exp.spent_amount, 0.00)) AS remaining_amount,
  ROUND((COALESCE(exp.spent_amount, 0.00) / gba.allocated_amount) * 100, 2) AS utilization_pct
FROM grant_budget_allocation AS gba
JOIN grant_award AS ga ON ga.grant_id = gba.grant_id
JOIN project AS p ON p.project_id = ga.project_id
JOIN budget_head AS bh ON bh.head_id = gba.head_id
LEFT JOIN (
  SELECT grant_id, head_id, SUM(amount) AS spent_amount
  FROM expenditure
  GROUP BY grant_id, head_id
) AS exp ON exp.grant_id = gba.grant_id AND exp.head_id = gba.head_id;


-- ----------------------------------------------------------------------------
-- 5. vw_milestone_tracker
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_milestone_tracker AS
SELECT
  m.milestone_id,
  m.project_id,
  p.project_code,
  p.title AS project_title,
  p.dept_id,
  d.dept_name,
  m.title AS milestone_title,
  m.description,
  m.due_date,
  m.completed_date,
  m.status,
  CASE
    WHEN m.status <> 'Completed' AND m.due_date < CURDATE()
    THEN DATEDIFF(CURDATE(), m.due_date)
    ELSE 0
  END AS days_overdue,
  CASE
    WHEN m.status <> 'Completed' AND m.due_date < CURDATE()
    THEN TRUE
    ELSE FALSE
  END AS is_overdue
FROM milestone AS m
JOIN project AS p ON p.project_id = m.project_id
JOIN department AS d ON d.dept_id = p.dept_id;


-- ----------------------------------------------------------------------------
-- 6. vw_researcher_output
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_researcher_output AS
SELECT
  r.researcher_id,
  r.employee_code,
  CONCAT(r.first_name, ' ', r.last_name) AS full_name,
  r.designation,
  r.dept_id,
  d.dept_code,
  d.dept_name,
  r.is_active,
  COALESCE(proj.total_projects, 0) AS total_projects,
  COALESCE(pi_proj.pi_projects, 0) AS pi_projects,
  COALESCE(pub.total_publications, 0) AS total_publications,
  COALESCE(pub.indexed_publications, 0) AS indexed_publications,
  COALESCE(pat.total_patents, 0) AS total_patents,
  COALESCE(pi_grants.total_grant_value_led, 0.00) AS total_grant_value_led
FROM researcher AS r
JOIN department AS d ON d.dept_id = r.dept_id
LEFT JOIN (
  SELECT researcher_id, COUNT(DISTINCT project_id) AS total_projects
  FROM project_investigator
  GROUP BY researcher_id
) AS proj ON proj.researcher_id = r.researcher_id
LEFT JOIN (
  SELECT researcher_id, COUNT(DISTINCT project_id) AS pi_projects
  FROM project_investigator
  WHERE role = 'PI'
  GROUP BY researcher_id
) AS pi_proj ON pi_proj.researcher_id = r.researcher_id
LEFT JOIN (
  SELECT
    pa.researcher_id,
    COUNT(DISTINCT p.publication_id) AS total_publications,
    SUM(CASE WHEN p.indexing IN ('Scopus', 'SCI', 'SCIE', 'WoS') THEN 1 ELSE 0 END) AS indexed_publications
  FROM publication_author AS pa
  JOIN publication AS p ON p.publication_id = pa.publication_id
  GROUP BY pa.researcher_id
) AS pub ON pub.researcher_id = r.researcher_id
LEFT JOIN (
  SELECT researcher_id, COUNT(DISTINCT patent_id) AS total_patents
  FROM patent_inventor
  GROUP BY researcher_id
) AS pat ON pat.researcher_id = r.researcher_id
LEFT JOIN (
  SELECT pi.researcher_id, SUM(ga.grant_amount) AS total_grant_value_led
  FROM project_investigator AS pi
  JOIN grant_award AS ga ON ga.project_id = pi.project_id
  WHERE pi.role = 'PI'
  GROUP BY pi.researcher_id
) AS pi_grants ON pi_grants.researcher_id = r.researcher_id;


-- ----------------------------------------------------------------------------
-- 7. vw_agency_portfolio
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_agency_portfolio AS
SELECT
  a.agency_id,
  a.agency_name,
  a.agency_type,
  a.country,
  COUNT(DISTINCT g.grant_id) AS total_grants,
  COUNT(DISTINCT g.project_id) AS total_projects_funded,
  COALESCE(SUM(g.grant_amount), 0.00) AS total_sanctioned_amount,
  COALESCE(e.total_spent, 0.00) AS total_spent_amount,
  CASE
    WHEN COUNT(DISTINCT g.grant_id) > 0
    THEN ROUND(COALESCE(SUM(g.grant_amount), 0.00) / COUNT(DISTINCT g.grant_id), 2)
    ELSE 0.00
  END AS avg_grant_size
FROM funding_agency AS a
LEFT JOIN grant_award AS g ON g.agency_id = a.agency_id
LEFT JOIN (
  SELECT ga.agency_id, SUM(exp.amount) AS total_spent
  FROM grant_award AS ga
  JOIN expenditure AS exp ON exp.grant_id = ga.grant_id
  GROUP BY ga.agency_id
) AS e ON e.agency_id = a.agency_id
GROUP BY a.agency_id, a.agency_name, a.agency_type, a.country;


-- ----------------------------------------------------------------------------
-- 8. vw_project_publications
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_project_publications AS
SELECT
  pp.project_id,
  p.project_code,
  p.title AS project_title,
  pub.publication_id,
  pub.title AS publication_title,
  pub.pub_type,
  pub.venue,
  YEAR(pub.pub_date) AS pub_year,
  pub.pub_date,
  pub.doi,
  pub.indexing,
  pub.citation_count,
  COALESCE(authors.author_list, '') AS author_list
FROM project_publication AS pp
JOIN project AS p ON p.project_id = pp.project_id
JOIN publication AS pub ON pub.publication_id = pp.publication_id
LEFT JOIN (
  SELECT
    pa.publication_id,
    GROUP_CONCAT(
      CONCAT(r.first_name, ' ', r.last_name, IF(pa.is_corresponding, ' (*)', ''))
      ORDER BY pa.author_order ASC
      SEPARATOR ', '
    ) AS author_list
  FROM publication_author AS pa
  JOIN researcher AS r ON r.researcher_id = pa.researcher_id
  GROUP BY pa.publication_id
) AS authors ON authors.publication_id = pub.publication_id;


-- ----------------------------------------------------------------------------
-- 9. vw_department_summary
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_department_summary AS
SELECT
  d.dept_id,
  d.dept_code,
  d.dept_name,
  COALESCE(res.total_researchers, 0) AS total_researchers,
  COALESCE(proj.total_projects, 0) AS total_projects,
  COALESCE(proj.active_projects, 0) AS active_projects,
  COALESCE(gr.total_funding, 0.00) AS total_funding,
  COALESCE(pub.total_publications, 0) AS total_publications
FROM department AS d
LEFT JOIN (
  SELECT dept_id, COUNT(*) AS total_researchers
  FROM researcher
  GROUP BY dept_id
) AS res ON res.dept_id = d.dept_id
LEFT JOIN (
  SELECT
    dept_id,
    COUNT(*) AS total_projects,
    SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) AS active_projects
  FROM project
  GROUP BY dept_id
) AS proj ON proj.dept_id = d.dept_id
LEFT JOIN (
  SELECT p.dept_id, SUM(ga.grant_amount) AS total_funding
  FROM project AS p
  JOIN grant_award AS ga ON ga.project_id = p.project_id
  GROUP BY p.dept_id
) AS gr ON gr.dept_id = d.dept_id
LEFT JOIN (
  SELECT r.dept_id, COUNT(DISTINCT pa.publication_id) AS total_publications
  FROM researcher AS r
  JOIN publication_author AS pa ON pa.researcher_id = r.researcher_id
  GROUP BY r.dept_id
) AS pub ON pub.dept_id = d.dept_id;
