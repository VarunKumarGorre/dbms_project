-- ============================================================================
-- RPGMS 10 Analytical & Operational Reports (R1 - R10)
-- File: db/08_reports.sql
-- Description: Standard operational queries and corresponding VIEWER-safe
--              aggregate queries for all 10 reports.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- REPORT R1: PROJECT PROGRESS
-- ----------------------------------------------------------------------------
-- R1 Operational: Detailed project progress, completion %, elapsed %, RAG status
SELECT
  p.project_id,
  p.project_code,
  p.title,
  d.dept_code,
  d.dept_name,
  p.status,
  p.start_date,
  p.end_date,
  DATEDIFF(p.end_date, CURDATE()) AS days_remaining,
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
JOIN department AS d ON d.dept_id = p.dept_id
LEFT JOIN (
  SELECT project_id,
         COUNT(*) AS total_milestones,
         SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_milestones,
         SUM(CASE WHEN status <> 'Completed' AND due_date < CURDATE() THEN 1 ELSE 0 END) AS overdue_milestones
  FROM milestone
  GROUP BY project_id
) AS m ON m.project_id = p.project_id
ORDER BY p.project_code ASC;

-- R1 Viewer-safe: Aggregated by department and status, completely omitting project codes & titles
SELECT
  d.dept_code,
  d.dept_name,
  p.status AS project_status,
  COUNT(p.project_id) AS total_projects,
  SUM(COALESCE(m.total_milestones, 0)) AS total_milestones,
  SUM(COALESCE(m.completed_milestones, 0)) AS completed_milestones,
  SUM(COALESCE(m.overdue_milestones, 0)) AS overdue_milestones,
  ROUND(AVG(
    CASE
      WHEN CURDATE() <= p.start_date THEN 0.00
      WHEN CURDATE() >= p.end_date THEN 100.00
      ELSE ROUND((DATEDIFF(CURDATE(), p.start_date) / DATEDIFF(p.end_date, p.start_date)) * 100, 2)
    END
  ), 2) AS avg_time_elapsed_pct
FROM project AS p
JOIN department AS d ON d.dept_id = p.dept_id
LEFT JOIN (
  SELECT project_id,
         COUNT(*) AS total_milestones,
         SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_milestones,
         SUM(CASE WHEN status <> 'Completed' AND due_date < CURDATE() THEN 1 ELSE 0 END) AS overdue_milestones
  FROM milestone
  GROUP BY project_id
) AS m ON m.project_id = p.project_id
GROUP BY d.dept_id, d.dept_code, d.dept_name, p.status
ORDER BY d.dept_code, p.status;


-- ----------------------------------------------------------------------------
-- REPORT R2: BUDGET UTILIZATION
-- ----------------------------------------------------------------------------
-- R2 Operational: Per-grant financial position with health badge
SELECT
  ga.grant_id,
  ga.grant_number,
  p.project_code,
  p.title AS project_title,
  fa.agency_name,
  ga.grant_amount,
  COALESCE(e.total_spent, 0.00) AS total_spent,
  (ga.grant_amount - COALESCE(e.total_spent, 0.00)) AS balance,
  ROUND((COALESCE(e.total_spent, 0.00) / ga.grant_amount) * 100, 2) AS utilization_pct,
  CASE
    WHEN (ga.grant_amount - COALESCE(e.total_spent, 0.00)) <= 0.00 THEN 'Exhausted'
    WHEN ROUND((COALESCE(e.total_spent, 0.00) / ga.grant_amount) * 100, 2) >= 90.00 THEN 'Near Limit'
    WHEN ROUND((COALESCE(e.total_spent, 0.00) / ga.grant_amount) * 100, 2) >= 50.00 THEN 'On Track'
    ELSE 'Under 50%'
  END AS health_status
FROM grant_award AS ga
JOIN project AS p ON p.project_id = ga.project_id
JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
LEFT JOIN (
  SELECT grant_id, SUM(amount) AS total_spent
  FROM expenditure
  GROUP BY grant_id
) AS e ON e.grant_id = ga.grant_id
ORDER BY utilization_pct DESC;

-- R2 Viewer-safe: Summary grouped by health category (grant counts and financial totals)
SELECT
  health_group.health_status,
  COUNT(*) AS grant_count,
  SUM(health_group.grant_amount) AS total_sanctioned,
  SUM(health_group.total_spent) AS total_expenditure,
  SUM(health_group.balance) AS total_balance,
  ROUND((SUM(health_group.total_spent) / SUM(health_group.grant_amount)) * 100, 2) AS group_utilization_pct
FROM (
  SELECT
    ga.grant_amount,
    COALESCE(e.total_spent, 0.00) AS total_spent,
    (ga.grant_amount - COALESCE(e.total_spent, 0.00)) AS balance,
    CASE
      WHEN (ga.grant_amount - COALESCE(e.total_spent, 0.00)) <= 0.00 THEN 'Exhausted'
      WHEN ROUND((COALESCE(e.total_spent, 0.00) / ga.grant_amount) * 100, 2) >= 90.00 THEN 'Near Limit'
      WHEN ROUND((COALESCE(e.total_spent, 0.00) / ga.grant_amount) * 100, 2) >= 50.00 THEN 'On Track'
      ELSE 'Under 50%'
    END AS health_status
  FROM grant_award AS ga
  LEFT JOIN (
    SELECT grant_id, SUM(amount) AS total_spent
    FROM expenditure
    GROUP BY grant_id
  ) AS e ON e.grant_id = ga.grant_id
) AS health_group
GROUP BY health_group.health_status
ORDER BY total_sanctioned DESC;


-- ----------------------------------------------------------------------------
-- REPORT R3: MILESTONE TRACKER
-- ----------------------------------------------------------------------------
-- R3 Operational: Detailed milestone records with days overdue
SELECT
  m.milestone_id,
  m.project_id,
  p.project_code,
  p.title AS project_title,
  d.dept_code,
  m.title AS milestone_title,
  m.due_date,
  m.completed_date,
  m.status,
  CASE
    WHEN m.status <> 'Completed' AND m.due_date < CURDATE()
    THEN DATEDIFF(CURDATE(), m.due_date)
    ELSE 0
  END AS days_overdue
FROM milestone AS m
JOIN project AS p ON p.project_id = m.project_id
JOIN department AS d ON d.dept_id = p.dept_id
ORDER BY days_overdue DESC, m.due_date ASC;

-- R3 Viewer-safe: Milestone distribution by month and status
SELECT
  DATE_FORMAT(due_date, '%Y-%m') AS due_month,
  status AS milestone_status,
  COUNT(*) AS milestone_count,
  SUM(CASE WHEN status <> 'Completed' AND due_date < CURDATE() THEN 1 ELSE 0 END) AS overdue_count
FROM milestone
GROUP BY DATE_FORMAT(due_date, '%Y-%m'), status
ORDER BY due_month ASC, milestone_status;


-- ----------------------------------------------------------------------------
-- REPORT R4: RESEARCHER OUTPUT
-- ----------------------------------------------------------------------------
-- R4 Operational: Output per researcher
SELECT
  r.researcher_id,
  r.employee_code,
  CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
  d.dept_code,
  r.designation,
  COALESCE(proj.total_projects, 0) AS total_projects,
  COALESCE(pub.total_pubs, 0) AS total_publications,
  COALESCE(pub.indexed_pubs, 0) AS indexed_publications,
  COALESCE(pat.total_patents, 0) AS total_patents,
  COALESCE(pi_grants.total_funding_led, 0.00) AS total_funding_led
FROM researcher AS r
JOIN department AS d ON d.dept_id = r.dept_id
LEFT JOIN (
  SELECT researcher_id, COUNT(DISTINCT project_id) AS total_projects
  FROM project_investigator
  GROUP BY researcher_id
) AS proj ON proj.researcher_id = r.researcher_id
LEFT JOIN (
  SELECT pa.researcher_id,
         COUNT(DISTINCT p.publication_id) AS total_pubs,
         SUM(CASE WHEN p.indexing IN ('Scopus','SCI','SCIE','WoS') THEN 1 ELSE 0 END) AS indexed_pubs
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
  SELECT pi.researcher_id, SUM(ga.grant_amount) AS total_funding_led
  FROM project_investigator AS pi
  JOIN grant_award AS ga ON ga.project_id = pi.project_id
  WHERE pi.role = 'PI'
  GROUP BY pi.researcher_id
) AS pi_grants ON pi_grants.researcher_id = r.researcher_id
ORDER BY total_publications DESC, total_funding_led DESC;

-- R4 Viewer-safe: Department-level researcher productivity summary
SELECT
  d.dept_code,
  d.dept_name,
  COUNT(DISTINCT r.researcher_id) AS faculty_count,
  COUNT(DISTINCT pa.publication_id) AS dept_publications,
  COUNT(DISTINCT pinv.patent_id) AS dept_patents,
  COALESCE(SUM(ga.grant_amount), 0.00) AS total_department_grants
FROM department AS d
JOIN researcher AS r ON r.dept_id = d.dept_id
LEFT JOIN publication_author AS pa ON pa.researcher_id = r.researcher_id
LEFT JOIN patent_inventor AS pinv ON pinv.researcher_id = r.researcher_id
LEFT JOIN (
  SELECT p.dept_id, ga.grant_amount
  FROM project AS p
  JOIN grant_award AS ga ON ga.project_id = p.project_id
) AS ga ON ga.dept_id = d.dept_id
GROUP BY d.dept_id, d.dept_code, d.dept_name
ORDER BY dept_publications DESC;


-- ----------------------------------------------------------------------------
-- REPORT R5: FUNDING AGENCY PORTFOLIO
-- ----------------------------------------------------------------------------
-- R5 Operational & Viewer-safe: Agency summary (no individual project identifiers)
SELECT
  fa.agency_name,
  fa.agency_type,
  fa.country,
  COUNT(DISTINCT ga.grant_id) AS total_grants,
  COUNT(DISTINCT ga.project_id) AS funded_projects_count,
  COALESCE(SUM(ga.grant_amount), 0.00) AS total_sanctioned_amount,
  COALESCE(e.total_spent, 0.00) AS total_spent_amount,
  ROUND(
    (COALESCE(SUM(ga.grant_amount), 0.00) / (SELECT SUM(grant_amount) FROM grant_award)) * 100, 2
  ) AS portfolio_share_pct
FROM funding_agency AS fa
LEFT JOIN grant_award AS ga ON ga.agency_id = fa.agency_id
LEFT JOIN (
  SELECT ga2.agency_id, SUM(exp.amount) AS total_spent
  FROM grant_award AS ga2
  JOIN expenditure AS exp ON exp.grant_id = ga2.grant_id
  GROUP BY ga2.agency_id
) AS e ON e.agency_id = fa.agency_id
GROUP BY fa.agency_id, fa.agency_name, fa.agency_type, fa.country
ORDER BY total_sanctioned_amount DESC;


-- ----------------------------------------------------------------------------
-- REPORT R6: PUBLICATIONS REPORT
-- ----------------------------------------------------------------------------
-- R6 Operational: Publication records with metadata, indexing, authors, and projects
SELECT
  pub.publication_id,
  pub.title,
  pub.pub_type,
  pub.venue,
  YEAR(pub.pub_date) AS pub_year,
  pub.pub_date,
  pub.doi,
  pub.indexing,
  pub.citation_count,
  COALESCE(pp.linked_projects, '') AS linked_projects,
  COALESCE(authors.author_list, '') AS authors
FROM publication AS pub
LEFT JOIN (
  SELECT publication_id, GROUP_CONCAT(DISTINCT p.project_code SEPARATOR ', ') AS linked_projects
  FROM project_publication AS pp
  JOIN project AS p ON p.project_id = pp.project_id
  GROUP BY publication_id
) AS pp ON pp.publication_id = pub.publication_id
LEFT JOIN (
  SELECT pa.publication_id,
         GROUP_CONCAT(CONCAT(r.first_name, ' ', r.last_name) ORDER BY pa.author_order SEPARATOR ', ') AS author_list
  FROM publication_author AS pa
  JOIN researcher AS r ON r.researcher_id = pa.researcher_id
  GROUP BY pa.publication_id
) AS authors ON authors.publication_id = pub.publication_id
ORDER BY pub.pub_date DESC;

-- R6 Viewer-safe: Aggregated publication counts by year, type, and indexing
SELECT
  YEAR(pub_date) AS pub_year,
  pub_type,
  indexing,
  COUNT(*) AS publication_count,
  SUM(citation_count) AS total_citations,
  ROUND(AVG(citation_count), 2) AS avg_citations
FROM publication
GROUP BY YEAR(pub_date), pub_type, indexing
ORDER BY pub_year DESC, pub_type, indexing;


-- ----------------------------------------------------------------------------
-- REPORT R7: DEPARTMENT SUMMARY
-- ----------------------------------------------------------------------------
-- R7 Operational & Viewer-safe: Overview of researchers, projects, grants, and publications
SELECT
  d.dept_code,
  d.dept_name,
  COALESCE(res.total_researchers, 0) AS total_researchers,
  COALESCE(proj.total_projects, 0) AS total_projects,
  COALESCE(proj.active_projects, 0) AS active_projects,
  COALESCE(gr.total_funding, 0.00) AS total_funding,
  COALESCE(pub.total_publications, 0) AS total_publications
FROM department AS d
LEFT JOIN (
  SELECT dept_id, COUNT(*) AS total_researchers FROM researcher GROUP BY dept_id
) AS res ON res.dept_id = d.dept_id
LEFT JOIN (
  SELECT dept_id, COUNT(*) AS total_projects,
         SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) AS active_projects
  FROM project GROUP BY dept_id
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
) AS pub ON pub.dept_id = d.dept_id
ORDER BY total_funding DESC;


-- ----------------------------------------------------------------------------
-- REPORT R8: EXPENDITURE STATEMENT
-- ----------------------------------------------------------------------------
-- R8 Operational: Transaction statement for a grant with running balance
SELECT
  exp.voucher_no,
  exp.expense_date,
  bh.head_name,
  exp.description,
  exp.amount,
  (ga.grant_amount - SUM(exp.amount) OVER (
     ORDER BY exp.expense_date, exp.expenditure_id
     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  )) AS running_grant_balance
FROM expenditure AS exp
JOIN budget_head AS bh ON bh.head_id = exp.head_id
JOIN grant_award AS ga ON ga.grant_id = exp.grant_id
WHERE exp.grant_id = 1
ORDER BY exp.expense_date ASC, exp.expenditure_id ASC;

-- R8 Viewer-safe: Monthly spend totals and running balance across all grants (no voucher / grant IDs)
WITH monthly_spend AS (
  SELECT
    DATE_FORMAT(expense_date, '%Y-%m') AS spend_month,
    COUNT(*) AS transaction_count,
    SUM(amount) AS monthly_amount
  FROM expenditure
  GROUP BY DATE_FORMAT(expense_date, '%Y-%m')
)
SELECT
  spend_month,
  transaction_count,
  monthly_amount,
  SUM(monthly_amount) OVER (ORDER BY spend_month ASC) AS cumulative_expenditure
FROM monthly_spend
ORDER BY spend_month ASC;


-- ----------------------------------------------------------------------------
-- REPORT R9: PATENT STATUS
-- ----------------------------------------------------------------------------
-- R9 Operational: Patent records with inventors and project links
SELECT
  pat.patent_id,
  pat.application_number,
  pat.patent_number,
  pat.title,
  pat.jurisdiction,
  pat.filing_date,
  pat.grant_date,
  pat.status,
  COALESCE(inv.inventor_list, '') AS inventors,
  COALESCE(pp.linked_projects, '') AS linked_projects
FROM patent AS pat
LEFT JOIN (
  SELECT patent_id, GROUP_CONCAT(CONCAT(r.first_name, ' ', r.last_name) SEPARATOR ', ') AS inventor_list
  FROM patent_inventor AS pi
  JOIN researcher AS r ON r.researcher_id = pi.researcher_id
  GROUP BY patent_id
) AS inv ON inv.patent_id = pat.patent_id
LEFT JOIN (
  SELECT patent_id, GROUP_CONCAT(p.project_code SEPARATOR ', ') AS linked_projects
  FROM project_patent AS ppt
  JOIN project AS p ON p.project_id = ppt.project_id
  GROUP BY patent_id
) AS pp ON pp.patent_id = pat.patent_id
ORDER BY pat.filing_date DESC;

-- R9 Viewer-safe: Aggregated patents by status and jurisdiction
SELECT
  status,
  jurisdiction,
  COUNT(*) AS patent_count,
  MIN(filing_date) AS earliest_filing_date,
  MAX(filing_date) AS latest_filing_date
FROM patent
GROUP BY status, jurisdiction
ORDER BY patent_count DESC;


-- ----------------------------------------------------------------------------
-- REPORT R10: CLOSING / UTILIZATION SUMMARY
-- ----------------------------------------------------------------------------
-- R10 Operational: Completed projects financial and output closure
SELECT
  p.project_code,
  p.title,
  d.dept_code,
  p.start_date,
  p.end_date,
  COALESCE(g.total_sanctioned, 0.00) AS total_sanctioned,
  COALESCE(e.total_spent, 0.00) AS total_spent,
  (COALESCE(g.total_sanctioned, 0.00) - COALESCE(e.total_spent, 0.00)) AS unspent_balance,
  COALESCE(pub.pub_count, 0) AS total_publications,
  COALESCE(pat.patent_count, 0) AS total_patents
FROM project AS p
JOIN department AS d ON d.dept_id = p.dept_id
LEFT JOIN (
  SELECT project_id, SUM(grant_amount) AS total_sanctioned
  FROM grant_award GROUP BY project_id
) AS g ON g.project_id = p.project_id
LEFT JOIN (
  SELECT ga.project_id, SUM(exp.amount) AS total_spent
  FROM grant_award AS ga
  JOIN expenditure AS exp ON exp.grant_id = ga.grant_id
  GROUP BY ga.project_id
) AS e ON e.project_id = p.project_id
LEFT JOIN (
  SELECT project_id, COUNT(*) AS pub_count FROM project_publication GROUP BY project_id
) AS pub ON pub.project_id = p.project_id
LEFT JOIN (
  SELECT project_id, COUNT(*) AS patent_count FROM project_patent GROUP BY project_id
) AS pat ON pat.project_id = p.project_id
WHERE p.status = 'Completed'
ORDER BY p.project_code ASC;

-- R10 Viewer-safe: Aggregated closure summary across completed projects
SELECT
  COUNT(*) AS total_completed_projects,
  SUM(COALESCE(g.total_sanctioned, 0.00)) AS total_funding_sanctioned,
  SUM(COALESCE(e.total_spent, 0.00)) AS total_funds_spent,
  SUM(COALESCE(g.total_sanctioned, 0.00) - COALESCE(e.total_spent, 0.00)) AS total_unspent_returned,
  SUM(COALESCE(pub.pub_count, 0)) AS total_deliverable_publications,
  SUM(COALESCE(pat.patent_count, 0)) AS total_deliverable_patents
FROM project AS p
LEFT JOIN (
  SELECT project_id, SUM(grant_amount) AS total_sanctioned
  FROM grant_award GROUP BY project_id
) AS g ON g.project_id = p.project_id
LEFT JOIN (
  SELECT ga.project_id, SUM(exp.amount) AS total_spent
  FROM grant_award AS ga
  JOIN expenditure AS exp ON exp.grant_id = ga.grant_id
  GROUP BY ga.project_id
) AS e ON e.project_id = p.project_id
LEFT JOIN (
  SELECT project_id, COUNT(*) AS pub_count FROM project_publication GROUP BY project_id
) AS pub ON pub.project_id = p.project_id
LEFT JOIN (
  SELECT project_id, COUNT(*) AS patent_count FROM project_patent GROUP BY project_id
) AS pat ON pat.project_id = p.project_id
WHERE p.status = 'Completed';
