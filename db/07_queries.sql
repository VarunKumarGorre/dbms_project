-- ============================================================================
-- RPGMS 40 Authoritative SQL Queries
-- File: db/07_queries.sql
-- Description: 40 numbered, commented queries covering basic retrieval,
--              joins, aggregates, nested queries, and window functions / CTEs.
-- ============================================================================

-- ============================================================================
-- SECTION A: BASIC RETRIEVAL (Q01 - Q06)
-- ============================================================================

-- Q01: All active projects with start and end dates, sorted by end date
SELECT project_code, title, start_date, end_date, status
FROM project
WHERE status = 'Active'
ORDER BY end_date ASC;

-- Q02: Researchers of a given department (parameter-style with a user variable)
SET @target_dept_code = 'CSE';
SELECT r.employee_code, CONCAT(r.first_name, ' ', r.last_name) AS full_name,
       r.designation, r.email, d.dept_name
FROM researcher AS r
JOIN department AS d ON d.dept_id = r.dept_id
WHERE d.dept_code = @target_dept_code
ORDER BY r.last_name ASC;

-- Q03: Projects whose title or abstract contains a keyword (LIKE and MATCH...AGAINST)
-- Q03a: LIKE search
SELECT project_code, title, abstract
FROM project
WHERE title LIKE '%sensor%' OR abstract LIKE '%sensor%';

-- Q03b: FULLTEXT search
SELECT project_code, title, abstract,
       ROUND(MATCH(title, abstract) AGAINST('sensor' IN NATURAL LANGUAGE MODE), 4) AS relevance_score
FROM project
WHERE MATCH(title, abstract) AGAINST('sensor' IN NATURAL LANGUAGE MODE);

-- Q04: Grants sanctioned in a given calendar year (2023)
SELECT grant_number, grant_amount, sanction_date, grant_start, grant_end, status
FROM grant_award
WHERE YEAR(sanction_date) = 2023
ORDER BY grant_amount DESC;

-- Q05: Researchers who joined after a given date, with designation filter using IN
SELECT employee_code, CONCAT(first_name, ' ', last_name) AS name, designation, joined_date
FROM researcher
WHERE joined_date >= '2018-01-01'
  AND designation IN ('Assistant Professor', 'Associate Professor')
ORDER BY joined_date ASC;

-- Q06: Patents that are Granted, newest first
SELECT application_number, patent_number, title, jurisdiction, filing_date, grant_date
FROM patent
WHERE status = 'Granted'
ORDER BY grant_date DESC;


-- ============================================================================
-- SECTION B: JOINS (Q07 - Q16)
-- ============================================================================

-- Q07: Project list with department name and PI full name (INNER JOIN, 3 tables)
SELECT p.project_code, p.title, d.dept_name,
       CONCAT(r.first_name, ' ', r.last_name) AS pi_name, r.email AS pi_email
FROM project AS p
JOIN department AS d ON d.dept_id = p.dept_id
JOIN project_investigator AS pi ON pi.project_id = p.project_id AND pi.role = 'PI'
JOIN researcher AS r ON r.researcher_id = pi.researcher_id
ORDER BY p.project_code ASC;

-- Q08: Every project with its funding agency names (JOIN through grant_award)
SELECT p.project_code, p.title, fa.agency_name, ga.grant_number, ga.grant_amount
FROM project AS p
JOIN grant_award AS ga ON ga.project_id = p.project_id
JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
ORDER BY p.project_code, ga.grant_amount DESC;

-- Q09: Researchers with the number of projects they work on — including those with zero (LEFT JOIN)
SELECT r.employee_code, CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
       d.dept_code, COUNT(pi.project_id) AS total_projects_count
FROM researcher AS r
JOIN department AS d ON d.dept_id = r.dept_id
LEFT JOIN project_investigator AS pi ON pi.researcher_id = r.researcher_id
GROUP BY r.researcher_id, r.employee_code, r.first_name, r.last_name, d.dept_code
ORDER BY total_projects_count DESC, r.last_name ASC;

-- Q10: Projects that have no grant yet (LEFT JOIN ... IS NULL)
SELECT p.project_code, p.title, d.dept_code, p.status, p.start_date
FROM project AS p
JOIN department AS d ON d.dept_id = p.dept_id
LEFT JOIN grant_award AS ga ON ga.project_id = p.project_id
WHERE ga.grant_id IS NULL
ORDER BY p.project_code ASC;

-- Q11: Publications with all authors in order, and the project(s) they are linked to
SELECT pub.doi, pub.title AS publication_title, pub.venue, pub.pub_date,
       GROUP_CONCAT(DISTINCT CONCAT(r.first_name, ' ', r.last_name, ' (', pa.author_order, ')')
                    ORDER BY pa.author_order ASC SEPARATOR ', ') AS authors_ordered,
       GROUP_CONCAT(DISTINCT p.project_code SEPARATOR ', ') AS linked_projects
FROM publication AS pub
JOIN publication_author AS pa ON pa.publication_id = pub.publication_id
JOIN researcher AS r ON r.researcher_id = pa.researcher_id
LEFT JOIN project_publication AS pp ON pp.publication_id = pub.publication_id
LEFT JOIN project AS p ON p.project_id = pp.project_id
GROUP BY pub.publication_id, pub.doi, pub.title, pub.venue, pub.pub_date
ORDER BY pub.pub_date DESC;

-- Q12: Self-join: pairs of researchers who are co-authors on at least one publication
SELECT DISTINCT
  CONCAT(r1.first_name, ' ', r1.last_name) AS researcher_1,
  CONCAT(r2.first_name, ' ', r2.last_name) AS researcher_2,
  pub.title AS coauthored_paper
FROM publication_author AS pa1
JOIN publication_author AS pa2 ON pa1.publication_id = pa2.publication_id
                              AND pa1.researcher_id < pa2.researcher_id
JOIN researcher AS r1 ON r1.researcher_id = pa1.researcher_id
JOIN researcher AS r2 ON r2.researcher_id = pa2.researcher_id
JOIN publication AS pub ON pub.publication_id = pa1.publication_id
ORDER BY researcher_1, researcher_2;

-- Q13: Expenditure details: voucher, date, amount, head name, grant number, project title (5-table join)
SELECT exp.voucher_no, exp.expense_date, exp.amount, bh.head_name,
       ga.grant_number, p.project_code, p.title AS project_title
FROM expenditure AS exp
JOIN budget_head AS bh ON bh.head_id = exp.head_id
JOIN grant_award AS ga ON ga.grant_id = exp.grant_id
JOIN project AS p ON p.project_id = ga.project_id
JOIN user_account AS u ON u.user_id = exp.recorded_by
ORDER BY exp.expense_date DESC, exp.voucher_no ASC;

-- Q14: Researchers who are both an inventor on a patent and an author of a publication (INNER JOIN of two derived sets)
SELECT r.employee_code, CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
       d.dept_code, pub_set.pub_count, pat_set.patent_count
FROM researcher AS r
JOIN department AS d ON d.dept_id = r.dept_id
JOIN (
  SELECT researcher_id, COUNT(DISTINCT publication_id) AS pub_count
  FROM publication_author
  GROUP BY researcher_id
) AS pub_set ON pub_set.researcher_id = r.researcher_id
JOIN (
  SELECT researcher_id, COUNT(DISTINCT patent_id) AS patent_count
  FROM patent_inventor
  GROUP BY researcher_id
) AS pat_set ON pat_set.researcher_id = r.researcher_id
ORDER BY pub_set.pub_count DESC;

-- Q15: Departments and their funding agencies (distinct) via projects and grants
SELECT DISTINCT d.dept_code, d.dept_name, fa.agency_name, fa.agency_type
FROM department AS d
JOIN project AS p ON p.dept_id = d.dept_id
JOIN grant_award AS ga ON ga.project_id = p.project_id
JOIN funding_agency AS fa ON fa.agency_id = ga.agency_id
ORDER BY d.dept_code, fa.agency_name;

-- Q16: RIGHT JOIN / UNION demo: all researchers and all patents even where unmatched (FULL OUTER JOIN emulation)
SELECT CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
       pat.application_number, pat.title AS patent_title
FROM researcher AS r
LEFT JOIN patent_inventor AS pi ON pi.researcher_id = r.researcher_id
LEFT JOIN patent AS pat ON pat.patent_id = pi.patent_id

UNION

SELECT CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
       pat.application_number, pat.title AS patent_title
FROM researcher AS r
RIGHT JOIN patent_inventor AS pi ON pi.researcher_id = r.researcher_id
RIGHT JOIN patent AS pat ON pat.patent_id = pi.patent_id
WHERE r.researcher_id IS NULL;


-- ============================================================================
-- SECTION C: AGGREGATES (Q17 - Q26)
-- ============================================================================

-- Q17: Total sanctioned grant amount per funding agency
SELECT fa.agency_name, fa.agency_type,
       COUNT(ga.grant_id) AS total_grants,
       COALESCE(SUM(ga.grant_amount), 0.00) AS total_sanctioned_amount
FROM funding_agency AS fa
LEFT JOIN grant_award AS ga ON ga.agency_id = fa.agency_id
GROUP BY fa.agency_id, fa.agency_name, fa.agency_type
ORDER BY total_sanctioned_amount DESC;

-- Q18: Average grant size per agency type
SELECT fa.agency_type,
       COUNT(ga.grant_id) AS grant_count,
       ROUND(AVG(ga.grant_amount), 2) AS avg_grant_amount,
       MIN(ga.grant_amount) AS min_grant_amount,
       MAX(ga.grant_amount) AS max_grant_amount
FROM funding_agency AS fa
JOIN grant_award AS ga ON ga.agency_id = fa.agency_id
GROUP BY fa.agency_type
ORDER BY avg_grant_amount DESC;

-- Q19: Number of projects per department, with HAVING >= 2
SELECT d.dept_code, d.dept_name, COUNT(p.project_id) AS project_count
FROM department AS d
JOIN project AS p ON p.dept_id = d.dept_id
GROUP BY d.dept_id, d.dept_code, d.dept_name
HAVING COUNT(p.project_id) >= 2
ORDER BY project_count DESC;

-- Q20: Total expenditure per project per budget head
SELECT p.project_code, p.title, bh.head_name,
       SUM(exp.amount) AS total_expenditure
FROM project AS p
JOIN grant_award AS ga ON ga.project_id = p.project_id
JOIN expenditure AS exp ON exp.grant_id = ga.grant_id
JOIN budget_head AS bh ON bh.head_id = exp.head_id
GROUP BY p.project_id, p.project_code, p.title, bh.head_id, bh.head_name
ORDER BY p.project_code, total_expenditure DESC;

-- Q21: Publications per year and per type (GROUP BY with ROLLUP)
SELECT COALESCE(CAST(pub_year AS CHAR), 'ALL YEARS') AS pub_year,
       COALESCE(pub_type, 'ALL TYPES') AS publication_type,
       COUNT(*) AS publication_count
FROM (
  SELECT YEAR(pub_date) AS pub_year, pub_type
  FROM publication
) AS sub
GROUP BY pub_year, pub_type WITH ROLLUP;

-- Q22: Top 5 researchers by number of publications
SELECT r.employee_code, CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
       d.dept_code, COUNT(pa.publication_id) AS total_publications
FROM researcher AS r
JOIN department AS d ON d.dept_id = r.dept_id
JOIN publication_author AS pa ON pa.researcher_id = r.researcher_id
GROUP BY r.researcher_id, r.employee_code, r.first_name, r.last_name, d.dept_code
ORDER BY total_publications DESC
LIMIT 5;

-- Q23: Department-wise total funding and average funding per project
SELECT d.dept_code, d.dept_name,
       COUNT(DISTINCT p.project_id) AS total_projects,
       COALESCE(SUM(ga.grant_amount), 0.00) AS total_funding,
       ROUND(COALESCE(SUM(ga.grant_amount), 0.00) / NULLIF(COUNT(DISTINCT p.project_id), 0), 2) AS avg_funding_per_project
FROM department AS d
JOIN project AS p ON p.dept_id = d.dept_id
LEFT JOIN grant_award AS ga ON ga.project_id = p.project_id
GROUP BY d.dept_id, d.dept_code, d.dept_name
ORDER BY total_funding DESC;

-- Q24: Months with the highest total expenditure (DATE_FORMAT)
SELECT DATE_FORMAT(expense_date, '%Y-%m') AS spend_month,
       COUNT(*) AS transaction_count,
       SUM(amount) AS monthly_spend
FROM expenditure
GROUP BY DATE_FORMAT(expense_date, '%Y-%m')
ORDER BY monthly_spend DESC
LIMIT 6;

-- Q25: Count of milestones by status per project
SELECT p.project_code, p.title,
       COUNT(m.milestone_id) AS total_milestones,
       SUM(CASE WHEN m.status = 'Completed' THEN 1 ELSE 0 END) AS completed_count,
       SUM(CASE WHEN m.status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress_count,
       SUM(CASE WHEN m.status = 'Pending' THEN 1 ELSE 0 END) AS pending_count,
       SUM(CASE WHEN m.status = 'Delayed' THEN 1 ELSE 0 END) AS delayed_count
FROM project AS p
LEFT JOIN milestone AS m ON m.project_id = p.project_id
GROUP BY p.project_id, p.project_code, p.title
ORDER BY p.project_code ASC;

-- Q26: Max, min and average citation count per indexing category
SELECT indexing,
       COUNT(*) AS publication_count,
       MIN(citation_count) AS min_citations,
       MAX(citation_count) AS max_citations,
       ROUND(AVG(citation_count), 2) AS avg_citations
FROM publication
GROUP BY indexing
ORDER BY avg_citations DESC;


-- ============================================================================
-- SECTION D: NESTED / SUBQUERIES (Q27 - Q34)
-- ============================================================================

-- Q27: Projects whose total grant is above the average total grant (scalar subquery)
SELECT p.project_code, p.title, SUM(ga.grant_amount) AS project_funding
FROM project AS p
JOIN grant_award AS ga ON ga.project_id = p.project_id
GROUP BY p.project_id, p.project_code, p.title
HAVING SUM(ga.grant_amount) > (
  SELECT AVG(proj_grant_sum)
  FROM (
    SELECT SUM(grant_amount) AS proj_grant_sum
    FROM grant_award
    GROUP BY project_id
  ) AS sub
)
ORDER BY project_funding DESC;

-- Q28: Researchers who have never authored a publication (NOT EXISTS)
SELECT r.employee_code, CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
       r.designation, d.dept_name
FROM researcher AS r
JOIN department AS d ON d.dept_id = r.dept_id
WHERE NOT EXISTS (
  SELECT 1 FROM publication_author AS pa
  WHERE pa.researcher_id = r.researcher_id
)
ORDER BY r.last_name;

-- Q29: Projects with at least one overdue milestone (EXISTS)
SELECT p.project_code, p.title, p.status, d.dept_code
FROM project AS p
JOIN department AS d ON d.dept_id = p.dept_id
WHERE EXISTS (
  SELECT 1 FROM milestone AS m
  WHERE m.project_id = p.project_id
    AND m.status <> 'Completed'
    AND m.due_date < CURDATE()
)
ORDER BY p.project_code;

-- Q30: Grants where spending is above 80% of the grant amount (derived table)
SELECT g_stat.grant_number, g_stat.grant_amount, g_stat.total_spent,
       ROUND((g_stat.total_spent / g_stat.grant_amount) * 100, 2) AS spend_percentage
FROM (
  SELECT ga.grant_id, ga.grant_number, ga.grant_amount,
         COALESCE(SUM(exp.amount), 0.00) AS total_spent
  FROM grant_award AS ga
  LEFT JOIN expenditure AS exp ON exp.grant_id = ga.grant_id
  GROUP BY ga.grant_id, ga.grant_number, ga.grant_amount
) AS g_stat
WHERE g_stat.total_spent > (0.80 * g_stat.grant_amount)
ORDER BY spend_percentage DESC;

-- Q31: Researchers who are PI on more than one project (IN + GROUP BY)
SELECT r.employee_code, CONCAT(r.first_name, ' ', r.last_name) AS pi_name,
       d.dept_name, COUNT(pi.project_id) AS pi_project_count
FROM researcher AS r
JOIN department AS d ON d.dept_id = r.dept_id
JOIN project_investigator AS pi ON pi.researcher_id = r.researcher_id
WHERE r.researcher_id IN (
  SELECT researcher_id
  FROM project_investigator
  WHERE role = 'PI'
  GROUP BY researcher_id
  HAVING COUNT(*) > 1
) AND pi.role = 'PI'
GROUP BY r.researcher_id, r.employee_code, r.first_name, r.last_name, d.dept_name;

-- Q32: Agencies that fund projects in every department (relational division using double NOT EXISTS)
SELECT fa.agency_id, fa.agency_name
FROM funding_agency AS fa
WHERE NOT EXISTS (
  SELECT 1 FROM department AS d
  WHERE NOT EXISTS (
    SELECT 1 FROM project AS p
    JOIN grant_award AS ga ON ga.project_id = p.project_id
    WHERE ga.agency_id = fa.agency_id
      AND p.dept_id = d.dept_id
  )
);

-- Q33: Projects with total expenditure greater than all milestone-less projects' expenditure (> ALL)
SELECT p.project_code, p.title, SUM(exp.amount) AS total_project_spend
FROM project AS p
JOIN grant_award AS ga ON ga.project_id = p.project_id
JOIN expenditure AS exp ON exp.grant_id = ga.grant_id
GROUP BY p.project_id, p.project_code, p.title
HAVING total_project_spend > ALL (
  SELECT COALESCE(SUM(e.amount), 0.00)
  FROM project AS p2
  LEFT JOIN milestone AS m ON m.project_id = p2.project_id
  LEFT JOIN grant_award AS ga2 ON ga2.project_id = p2.project_id
  LEFT JOIN expenditure AS e ON e.grant_id = ga2.grant_id
  WHERE m.milestone_id IS NULL
  GROUP BY p2.project_id
)
ORDER BY total_project_spend DESC;

-- Q34: The latest expenditure for each grant (correlated subquery)
SELECT e1.grant_id, ga.grant_number, e1.voucher_no, e1.expense_date, e1.amount, e1.description
FROM expenditure AS e1
JOIN grant_award AS ga ON ga.grant_id = e1.grant_id
WHERE e1.expense_date = (
  SELECT MAX(e2.expense_date)
  FROM expenditure AS e2
  WHERE e2.grant_id = e1.grant_id
)
ORDER BY e1.expense_date DESC;


-- ============================================================================
-- SECTION E: ADVANCED (WINDOW FUNCTIONS, CTEs, SET OPERATIONS) (Q35 - Q40)
-- ============================================================================

-- Q35: Rank researchers within each department by publication count (RANK() OVER (PARTITION BY ...))
SELECT d.dept_code,
       CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
       COUNT(pa.publication_id) AS pub_count,
       RANK() OVER (PARTITION BY r.dept_id ORDER BY COUNT(pa.publication_id) DESC) AS dept_rank
FROM researcher AS r
JOIN department AS d ON d.dept_id = r.dept_id
LEFT JOIN publication_author AS pa ON pa.researcher_id = r.researcher_id
GROUP BY r.researcher_id, r.first_name, r.last_name, r.dept_id, d.dept_code
ORDER BY d.dept_code, dept_rank ASC;

-- Q36: Running total of expenditure per grant by date (SUM() OVER)
SELECT ga.grant_number, exp.voucher_no, exp.expense_date, exp.amount,
       SUM(exp.amount) OVER (
         PARTITION BY exp.grant_id
         ORDER BY exp.expense_date, exp.expenditure_id
         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS cumulative_spent
FROM expenditure AS exp
JOIN grant_award AS ga ON ga.grant_id = exp.grant_id
ORDER BY ga.grant_number, exp.expense_date ASC;

-- Q37: Month-over-month spending change using LAG()
WITH monthly_expenditure AS (
  SELECT DATE_FORMAT(expense_date, '%Y-%m') AS spend_month,
         SUM(amount) AS total_spend
  FROM expenditure
  GROUP BY DATE_FORMAT(expense_date, '%Y-%m')
)
SELECT spend_month,
       total_spend,
       LAG(total_spend, 1) OVER (ORDER BY spend_month) AS prev_month_spend,
       ROUND(total_spend - LAG(total_spend, 1) OVER (ORDER BY spend_month), 2) AS mom_difference,
       ROUND(((total_spend - LAG(total_spend, 1) OVER (ORDER BY spend_month)) / LAG(total_spend, 1) OVER (ORDER BY spend_month)) * 100, 2) AS mom_growth_pct
FROM monthly_expenditure
ORDER BY spend_month ASC;

-- Q38: CTE: project hierarchy summary — project → milestones done → spend → publications
WITH proj_milestones AS (
  SELECT project_id,
         COUNT(*) AS total_milestones,
         SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_milestones
  FROM milestone
  GROUP BY project_id
),
proj_spend AS (
  SELECT ga.project_id,
         SUM(exp.amount) AS total_spend
  FROM grant_award AS ga
  JOIN expenditure AS exp ON exp.grant_id = ga.grant_id
  GROUP BY ga.project_id
),
proj_pubs AS (
  SELECT project_id,
         COUNT(DISTINCT publication_id) AS total_publications
  FROM project_publication
  GROUP BY project_id
)
SELECT p.project_code, p.title, p.status,
       COALESCE(pm.completed_milestones, 0) AS completed_milestones,
       COALESCE(pm.total_milestones, 0) AS total_milestones,
       COALESCE(ps.total_spend, 0.00) AS total_spend,
       COALESCE(pp.total_publications, 0) AS total_publications
FROM project AS p
LEFT JOIN proj_milestones AS pm ON pm.project_id = p.project_id
LEFT JOIN proj_spend AS ps ON ps.project_id = p.project_id
LEFT JOIN proj_pubs AS pp ON pp.project_id = p.project_id
ORDER BY p.project_code;

-- Q39: Set operations: researchers who authored publications UNION / INTERSECT-style (emulate INTERSECT with IN) with those who hold patents
SELECT r.employee_code, CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
       'Author AND Inventor' AS activity_status
FROM researcher AS r
WHERE r.researcher_id IN (SELECT researcher_id FROM publication_author)
  AND r.researcher_id IN (SELECT researcher_id FROM patent_inventor)

UNION

SELECT r.employee_code, CONCAT(r.first_name, ' ', r.last_name) AS researcher_name,
       'Author Only' AS activity_status
FROM researcher AS r
WHERE r.researcher_id IN (SELECT researcher_id FROM publication_author)
  AND r.researcher_id NOT IN (SELECT researcher_id FROM patent_inventor)
ORDER BY activity_status, researcher_name;

-- Q40: A query using a view (vw_budget_utilization) joined to vw_project_progress to flag "high spend, low progress" projects
SELECT bu.project_code, bu.project_title,
       bu.grant_number, bu.utilization_pct AS spend_utilization_pct,
       pp.milestone_completion_pct, pp.time_elapsed_pct, pp.rag_status,
       (bu.utilization_pct - COALESCE(pp.milestone_completion_pct, 0.00)) AS spend_lead_over_progress_points
FROM vw_budget_utilization AS bu
JOIN vw_project_progress AS pp ON pp.project_id = bu.project_id
WHERE bu.utilization_pct > COALESCE(pp.milestone_completion_pct, 0.00)
ORDER BY spend_lead_over_progress_points DESC;
