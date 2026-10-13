-- ============================================================================
-- RPGMS Deterministic Sample Seed Data
-- File: db/06_seed.sql
-- Description: Deterministic sample data for an Indian University Research Office.
--              Includes realistic grants (INR), researchers, expenditures,
--              milestones, publications, patents, reports, and accounts.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. DEPARTMENT (6 rows)
-- ----------------------------------------------------------------------------
INSERT INTO department (dept_id, dept_code, dept_name, building, contact_email) VALUES
(1, 'CSE',   'Computer Science and Engineering',        'Alan Turing Block',     'cse.office@univ.edu'),
(2, 'ECE',   'Electronics and Communication Engg',     'J.C. Bose Complex',     'ece.office@univ.edu'),
(3, 'MECH',  'Mechanical Engineering',                 'Visvesvaraya Hall',     'mech.office@univ.edu'),
(4, 'CIVIL', 'Civil Engineering',                      'Sreedharan Block',      'civil.office@univ.edu'),
(5, 'BIO',   'Biotechnology & Bioengineering',         'Hargobind Khorana Lab', 'bio.office@univ.edu'),
(6, 'CHEM',  'Chemical Sciences',                      'P.C. Ray Building',     'chem.office@univ.edu');

-- ----------------------------------------------------------------------------
-- 2. RESEARCHER (24 rows)
-- Edge cases:
-- - Researcher 24 is inactive
-- - Researcher 23 has zero projects
-- - Researchers 21 and 22 have zero publications
-- - Researcher 1 is PI on 2 projects, and is both author and patent inventor
-- ----------------------------------------------------------------------------
INSERT INTO researcher (researcher_id, employee_code, first_name, last_name, email, phone, designation, dept_id, orcid_id, joined_date, is_active) VALUES
(1,  'EMP-101', 'Anand',     'Rao',       'a.rao@univ.edu',       '+91-9876543201', 'Professor',           4, '0000-0002-1825-0097', '2015-06-15', TRUE),
(2,  'EMP-102', 'Sunita',    'Menon',     's.menon@univ.edu',     '+91-9876543202', 'Associate Professor', 1, '0000-0001-5234-9812', '2017-08-01', TRUE),
(3,  'EMP-103', 'Rajesh',    'Sharma',    'r.sharma@univ.edu',    '+91-9876543203', 'Professor',           2, '0000-0003-8712-4561', '2014-01-10', TRUE),
(4,  'EMP-104', 'Kavita',    'Nair',      'k.nair@univ.edu',      '+91-9876543204', 'Assistant Professor', 1, '0000-0002-9981-1234', '2020-02-15', TRUE),
(5,  'EMP-105', 'Arun',      'Verma',     'a.verma@univ.edu',     '+91-9876543205', 'Associate Professor', 2, '0000-0001-4455-6677', '2018-07-20', TRUE),
(6,  'EMP-106', 'Pooja',     'Deshmukh',  'p.deshmukh@univ.edu',  '+91-9876543206', 'Assistant Professor', 3, '0000-0002-7788-9900', '2021-09-01', TRUE),
(7,  'EMP-107', 'Vikas',     'Gupta',     'v.gupta@univ.edu',     '+91-9876543207', 'Professor',           5, '0000-0003-1122-3344', '2013-11-05', TRUE),
(8,  'EMP-108', 'Meera',     'Iyer',      'm.iyer@univ.edu',      '+91-9876543208', 'Assistant Professor', 5, '0000-0001-9988-7766', '2019-03-12', TRUE),
(9,  'EMP-109', 'Siddharth', 'Sen',       's.sen@univ.edu',       '+91-9876543209', 'Professor',           6, '0000-0002-3344-5566', '2012-04-18', TRUE),
(10, 'EMP-110', 'Deepa',     'Patel',     'd.patel@univ.edu',     '+91-9876543210', 'Associate Professor', 6, '0000-0003-5566-7788', '2016-10-25', TRUE),
(11, 'EMP-111', 'Manoj',     'Kumar',     'm.kumar@univ.edu',     '+91-9876543211', 'Associate Professor', 3, '0000-0001-1212-3434', '2017-12-01', TRUE),
(12, 'EMP-112', 'Priya',     'Choudhury', 'p.choudhury@univ.edu', '+91-9876543212', 'Professor',           3, '0000-0002-5656-7878', '2015-02-14', TRUE),
(13, 'EMP-113', 'Gaurav',    'Bhatia',    'g.bhatia@univ.edu',    '+91-9876543213', 'Assistant Professor', 1, '0000-0003-9090-1212', '2021-01-15', TRUE),
(14, 'EMP-114', 'Swati',     'Reddy',     's.reddy@univ.edu',     '+91-9876543214', 'Associate Professor', 1, '0000-0001-3434-5656', '2018-05-10', TRUE),
(15, 'EMP-115', 'Nikhil',    'Joshi',     'n.joshi@univ.edu',     '+91-9876543215', 'Assistant Professor', 2, '0000-0002-7878-9090', '2020-08-22', TRUE),
(16, 'EMP-116', 'Ritu',      'Bansal',    'r.bansal@univ.edu',    '+91-9876543216', 'Assistant Professor', 4, '0000-0003-2323-4545', '2019-11-30', TRUE),
(17, 'EMP-117', 'Alok',      'Mishra',    'a.mishra@univ.edu',    '+91-9876543217', 'Postdoctoral Fellow', 5, '0000-0001-6767-8989', '2022-07-01', TRUE),
(18, 'EMP-118', 'Sneha',     'Kulkarni',  's.kulkarni@univ.edu',  '+91-9876543218', 'Associate Professor', 5, '0000-0002-0101-2323', '2016-09-15', TRUE),
(19, 'EMP-119', 'Rohan',     'Das',       'r.das@univ.edu',       '+91-9876543219', 'Research Scholar',    1, '0000-0003-4545-6767', '2023-01-10', TRUE),
(20, 'EMP-120', 'Ananya',    'Roy',       'a.roy@univ.edu',       '+91-9876543220', 'Research Associate',  4, '0000-0001-8989-0101', '2022-03-01', TRUE),
(21, 'EMP-121', 'Karthik',   'Subramanian','k.subra@univ.edu',    '+91-9876543221', 'Research Scholar',    2, '0000-0002-4343-6565', '2023-08-01', TRUE),
(22, 'EMP-122', 'Divya',     'Prasad',    'd.prasad@univ.edu',    '+91-9876543222', 'Research Scholar',    3, '0000-0003-8787-0909', '2023-09-15', TRUE),
(23, 'EMP-123', 'Varun',     'Kapoor',    'v.kapoor@univ.edu',    '+91-9876543223', 'Assistant Professor', 6, '0000-0001-2121-4343', '2024-01-10', TRUE),
(24, 'EMP-124', 'Suresh',    'Pillai',    's.pillai@univ.edu',    '+91-9876543224', 'Professor',           4, '0000-0002-6565-8787', '2010-05-01', FALSE);

-- ----------------------------------------------------------------------------
-- 3. USER_ACCOUNT (6 rows, demo password: 'password123')
-- Hash: $2b$12$KlOQs8pk4j9dlkIuAsws4.jCYQJ4IjlPnSiUsiAvpXdXFzMQ7uXRi
-- ----------------------------------------------------------------------------
INSERT INTO user_account (user_id, username, password_hash, role, researcher_id, is_active) VALUES
(1, 'admin',    '$2b$12$KlOQs8pk4j9dlkIuAsws4.jCYQJ4IjlPnSiUsiAvpXdXFzMQ7uXRi', 'ADMIN',            NULL, TRUE),
(2, 'officer',  '$2b$12$KlOQs8pk4j9dlkIuAsws4.jCYQJ4IjlPnSiUsiAvpXdXFzMQ7uXRi', 'RESEARCH_OFFICER', NULL, TRUE),
(3, 'pi_rao',   '$2b$12$KlOQs8pk4j9dlkIuAsws4.jCYQJ4IjlPnSiUsiAvpXdXFzMQ7uXRi', 'PI',               1,    TRUE),
(4, 'pi_menon', '$2b$12$KlOQs8pk4j9dlkIuAsws4.jCYQJ4IjlPnSiUsiAvpXdXFzMQ7uXRi', 'PI',               2,    TRUE),
(5, 'pi_sharma','$2b$12$KlOQs8pk4j9dlkIuAsws4.jCYQJ4IjlPnSiUsiAvpXdXFzMQ7uXRi', 'PI',               3,    TRUE),
(6, 'viewer',   '$2b$12$KlOQs8pk4j9dlkIuAsws4.jCYQJ4IjlPnSiUsiAvpXdXFzMQ7uXRi', 'VIEWER',        NULL, TRUE);

-- ----------------------------------------------------------------------------
-- 4. FUNDING_AGENCY (9 rows)
-- ----------------------------------------------------------------------------
INSERT INTO funding_agency (agency_id, agency_name, agency_type, country, contact_email, website) VALUES
(1, 'Science and Engineering Research Board (SERB)', 'Government',    'India', 'info@serb.gov.in',    'https://serb.gov.in'),
(2, 'Department of Science and Technology (DST)',   'Government',    'India', 'dst-grants@nic.in',   'https://dst.gov.in'),
(3, 'Department of Biotechnology (DBT)',           'Government',    'India', 'dbt-research@nic.in', 'https://dbtindia.gov.in'),
(4, 'Indian Council of Medical Research (ICMR)',    'Government',    'India', 'grants@icmr.org.in',  'https://icmr.gov.in'),
(5, 'Council of Scientific & Industrial Research',  'Government',    'India', 'csir-ext@csir.res.in','https://csir.res.in'),
(6, 'Indian Space Research Organisation (ISRO)',    'Government',    'India', 'respone@isro.gov.in', 'https://isro.gov.in'),
(7, 'AICTE Research Promotion Scheme',              'Government',    'India', 'rps@aicte-india.org', 'https://aicte-india.org'),
(8, 'Tata Motors R&D Sponsorship',                  'Industry',      'India', 'rd.grants@tatamotors.com','https://tatamotors.com'),
(9, 'Wellcome Trust Biomedical Foundation',         'International', 'UK',    'grants@wellcome.org', 'https://wellcome.org');

-- ----------------------------------------------------------------------------
-- 5. BUDGET_HEAD (6 rows)
-- ----------------------------------------------------------------------------
INSERT INTO budget_head (head_id, head_name, description) VALUES
(1, 'Equipment',    'Capital instrumentation, hardware, and experimental setups'),
(2, 'Consumables',  'Chemicals, electronic components, raw materials, and glassware'),
(3, 'Travel',       'Field experiments, domestic/international conference presentation'),
(4, 'Manpower',     'Project fellows, JRF/SRF stipends, and postdoc fellowships'),
(5, 'Contingency',  'Documentation, printing, spare parts, and incidental expenses'),
(6, 'Overheads',    'Institutional infrastructure, utilities, and administrative charges');

-- ----------------------------------------------------------------------------
-- 6. PROJECT (15 rows)
-- ----------------------------------------------------------------------------
INSERT INTO project (project_id, project_code, title, abstract, dept_id, start_date, end_date, status) VALUES
(1,  'RP-2024-001', 'Soil Moisture Sensing for Precision Irrigation',    'Low-cost IoT wireless sensor networks for agricultural water management.', 4, '2024-01-01', '2026-12-31', 'Active'),
(2,  'RP-2023-002', 'Federated Learning for Edge Healthcare Diagnostics', 'Privacy-preserving distributed AI models on edge clinical devices.',       1, '2023-07-01', '2026-06-30', 'Active'),
(3,  'RP-2023-003', 'Sub-terahertz Antenna Arrays for 6G Networks',       'Wideband phased array antennas in the 140 GHz frequency band.',            2, '2023-01-01', '2025-12-31', 'Active'),
(4,  'RP-2026-004', 'Resilient Concrete with Geopolymer Composite',      'Fly ash and slag-based cementless geopolymer concrete for marine structures.',4,'2026-11-01', '2028-10-31', 'Proposed'),
(5,  'RP-2024-005', 'CRISPR-Cas12 Diagnostics for Plant Pathogens',      'Rapid isothermal nucleic acid detection of viral infections in cash crops.', 5, '2024-01-15', '2026-12-31', 'On Hold'),
(6,  'RP-2022-006', 'Green Synthesis of Catalytic Metal Organic Frameworks','Eco-friendly MOF synthesis for carbon capture and selective separation.',  6, '2022-01-01', '2024-12-31', 'Active'),
(7,  'RP-2023-007', 'Hybrid Composite Driveshafts for Electric Trucks',   'Lightweight carbon-fiber reinforced epoxy shaft under torsional loads.',    3, '2023-01-01', '2025-12-31', 'Active'),
(8,  'RP-2024-008', 'Quantum Key Distribution over Urban Fiber Links',    'Continuous-variable QKD protocols with active phase drift compensation.',  1, '2024-02-01', '2026-12-31', 'Active'),
(9,  'RP-2023-009', 'Low-power Neuromorphic Memristive Accelerators',    'In-memory computing crossbar arrays for spiking neural networks.',          2, '2023-03-01', '2026-02-28', 'Active'),
(10, 'RP-2024-010', 'Engineered Microalgae for Biofuel Lipid Yield',      'Metabolic engineering of Chlorella for high lipid accumulation.',          5, '2024-01-01', '2026-12-31', 'Active'),
(11, 'RP-2023-011', 'Micro-EDM Machining of Inconel 718 Superalloy',     'Parametric optimization of micro-electrical discharge machining.',          3, '2023-06-01', '2026-05-31', 'Active'),
(12, 'RP-2024-012', 'Photocatalytic Solar Water Splitting over Nanowires', 'Bismuth vanadate core-shell nanowire arrays for green hydrogen.',        6, '2024-01-01', '2026-12-31', 'Active'),
(13, 'RP-2026-013', 'Explainable AI for Autonomous Robotic Navigation',   'Causal neuro-symbolic reasoning for safety-critical motion planning.',       1, '2026-12-01', '2028-11-30', 'Proposed'),
(14, 'RP-2024-014', 'Seismic Retrofitting of Heritage Masonry Structures', 'Basalt textile reinforced mortar overlays for unreinforced masonry.',     4, '2024-01-01', '2026-12-31', 'Active'),
(15, 'RP-2022-015', 'Nanoparticle Drug Delivery for Targeted Oncology',   'Folate-receptor targeted polymeric nanocarriers for doxorubicin.',          5, '2022-01-01', '2024-12-31', 'Active');

-- ----------------------------------------------------------------------------
-- 7. PROJECT_INVESTIGATOR (~45 rows)
-- Satisfies BR-10 (exactly one PI per project) and BR-11 (effort <= 100)
-- ----------------------------------------------------------------------------
INSERT INTO project_investigator (project_id, researcher_id, role, assigned_date, effort_percent) VALUES
-- Proj 1 (PI: Rao 35%, Menon Co-PI 15%, Bansal 20%, Roy 50%)
(1, 1,  'PI',               '2024-01-01', 35.00),
(1, 2,  'Co-PI',            '2024-01-01', 15.00),
(1, 16, 'Researcher',       '2024-01-01', 20.00),
(1, 20, 'Research Scholar', '2024-01-01', 50.00),

-- Proj 2 (PI: Menon 40%, Nair 25%, Das 50%)
(2, 2,  'PI',               '2023-07-01', 40.00),
(2, 4,  'Co-PI',            '2023-07-01', 25.00),
(2, 19, 'Research Scholar', '2023-07-01', 50.00),

-- Proj 3 (PI: Sharma 45%, Verma 20%, Joshi 25%, Subra 50%)
(3, 3,  'PI',               '2023-01-01', 45.00),
(3, 5,  'Co-PI',            '2023-01-01', 20.00),
(3, 15, 'Researcher',       '2023-01-01', 25.00),
(3, 21, 'Research Scholar', '2023-01-01', 50.00),

-- Proj 4 (PI: Rao 25%, Bansal 20%) -> Rao total Proposed/Active: 35 + 25 = 60 <= 100
(4, 1,  'PI',               '2026-11-01', 25.00),
(4, 16, 'Co-PI',            '2026-11-01', 20.00),

-- Proj 5 (PI: Gupta 30%, Iyer 25%, Mishra 40%)
(5, 7,  'PI',               '2024-01-15', 30.00),
(5, 8,  'Co-PI',            '2024-01-15', 25.00),
(5, 17, 'Researcher',       '2024-01-15', 40.00),

-- Proj 6 (PI: Sen 40%, Patel 30%) - Completed
(6, 9,  'PI',               '2022-01-01', 40.00),
(6, 10, 'Co-PI',            '2022-01-01', 30.00),

-- Proj 7 (PI: Kumar 30%, Deshmukh 20%, Prasad 40%) - Cancelled
(7, 11, 'PI',               '2023-01-01', 30.00),
(7, 6,  'Co-PI',            '2023-01-01', 20.00),
(7, 22, 'Research Scholar', '2023-01-01', 40.00),

-- Proj 8 (PI: Nair 35%, Bhatia 25%, Das 30%)
(8, 4,  'PI',               '2024-02-01', 35.00),
(8, 13, 'Co-PI',            '2024-02-01', 25.00),
(8, 19, 'Research Scholar', '2024-02-01', 30.00),

-- Proj 9 (PI: Verma 40%, Joshi 30%, Sharma 15%)
(9, 5,  'PI',               '2023-03-01', 40.00),
(9, 15, 'Co-PI',            '2023-03-01', 30.00),
(9, 3,  'Researcher',       '2023-03-01', 15.00),

-- Proj 10 (PI: Iyer 35%, Gupta 20%, Mishra 40%)
(10, 8, 'PI',               '2024-01-01', 35.00),
(10, 7, 'Co-PI',            '2024-01-01', 20.00),
(10, 17,'Researcher',       '2024-01-01', 40.00),

-- Proj 11 (PI: Choudhury 40%, Kumar 25%, Deshmukh 25%)
(11, 12,'PI',               '2023-06-01', 40.00),
(11, 11,'Co-PI',            '2023-06-01', 25.00),
(11, 6, 'Researcher',       '2023-06-01', 25.00),

-- Proj 12 (PI: Patel 40%, Sen 20%)
(12, 10,'PI',               '2024-01-01', 40.00),
(12, 9, 'Co-PI',            '2024-01-01', 20.00),

-- Proj 13 (PI: Reddy 30%, Bhatia 20%)
(13, 14,'PI',               '2026-12-01', 30.00),
(13, 13,'Co-PI',            '2026-12-01', 20.00),

-- Proj 14 (PI: Bansal 35%, Roy 40%)
(14, 16,'PI',               '2024-01-01', 35.00),
(14, 20,'Research Scholar', '2024-01-01', 40.00),

-- Proj 15 (PI: Kulkarni 40%, Gupta 25%) - Completed
(15, 18,'PI',               '2022-01-01', 40.00),
(15, 7, 'Co-PI',            '2022-01-01', 25.00);

-- ----------------------------------------------------------------------------
-- 8. GRANT_AWARD (16 rows)
-- Edge cases:
-- - Proj 1 has 2 grants
-- - Proj 4 and 13 have NO grant
-- - Proj 14 has grant but 0 expenditure
-- - Proj 3 has grant near limit (>=95% utilization)
-- - Proj 7 has terminated grant
-- - Proj 6 and 15 have closed grants
-- ----------------------------------------------------------------------------
INSERT INTO grant_award (grant_id, grant_number, project_id, agency_id, grant_amount, sanction_date, grant_start, grant_end, status) VALUES
(1,  'SERB/2023/00142', 1,  1, 3800000.00, '2023-11-15', '2024-01-01', '2026-12-31', 'Active'),
(2,  'DST/AGRI/2024/88',1,  2, 1200000.00, '2023-12-10', '2024-02-01', '2026-06-30', 'Active'),
(3,  'SERB/2022/00918', 3,  1, 4500000.00, '2022-11-20', '2023-01-01', '2025-12-31', 'Active'),  -- Near limit!
(4,  'DBT/AI/2023/04',  2,  3, 5200000.00, '2023-05-15', '2023-07-01', '2026-06-30', 'Active'),
(5,  'ICMR/MED/2023/19',5,  4, 2800000.00, '2023-12-01', '2024-01-15', '2026-12-31', 'Active'),
(6,  'CSIR/CHEM/2021/7',6,  5, 3400000.00, '2021-11-10', '2022-01-01', '2024-12-31', 'Closed'),
(7,  'TATA/MECH/2022/01',7, 8, 2200000.00, '2022-12-05', '2023-01-01', '2025-12-31', 'Terminated'),
(8,  'ISRO/RESP/2023/11',8, 6, 6500000.00, '2023-12-20', '2024-02-01', '2026-12-31', 'Active'),
(9,  'AICTE/RPS/2023/05',9, 7, 1800000.00, '2023-01-15', '2023-03-01', '2026-02-28', 'Active'),
(10, 'DBT/GEN/2023/33', 10, 3, 4100000.00, '2023-11-10', '2024-01-01', '2026-12-31', 'Active'),
(11, 'DST/MAT/2023/09', 11, 2, 3100000.00, '2023-04-18', '2023-06-01', '2026-05-31', 'Active'),
(12, 'SERB/CHEM/2023/45',12,1, 3900000.00, '2023-10-25', '2024-01-01', '2026-12-31', 'Active'),
(13, 'DST/CIVIL/2023/77',14,2, 2500000.00, '2023-11-30', '2024-01-01', '2026-12-31', 'Sanctioned'), -- 0 spend
(14, 'WELLCOME/2021/08',15, 9, 7500000.00, '2021-10-15', '2022-01-01', '2024-12-31', 'Closed'),
(15, 'SERB/CRG/2023/90', 2, 1, 2000000.00, '2023-06-01', '2023-08-01', '2026-05-31', 'Active'),
(16, 'CSIR/BIO/2023/12', 10,5, 1500000.00, '2023-12-05', '2024-02-01', '2026-11-30', 'Active');

-- ----------------------------------------------------------------------------
-- 9. GRANT_BUDGET_ALLOCATION (~60 rows)
-- Sum of allocations <= grant_amount
-- ----------------------------------------------------------------------------
INSERT INTO grant_budget_allocation (grant_id, head_id, allocated_amount) VALUES
-- Grant 1 (38.0 L): Eq 18L, Con 6L, Trv 3L, Man 7L, Cnt 2L, Ov 2L = 38L
(1, 1, 1800000.00), (1, 2, 600000.00), (1, 3, 300000.00), (1, 4, 700000.00), (1, 5, 200000.00), (1, 6, 200000.00),
-- Grant 2 (12.0 L): Con 4L, Trv 2L, Man 5L, Cnt 1L = 12L
(2, 2, 400000.00), (2, 3, 200000.00), (2, 4, 500000.00), (2, 5, 100000.00),
-- Grant 3 (45.0 L): Eq 20L, Con 8L, Trv 3L, Man 10L, Cnt 2L, Ov 2L = 45L (Near limit!)
(3, 1, 2000000.00), (3, 2, 800000.00), (3, 3, 300000.00), (3, 4, 1000000.00), (3, 5, 200000.00), (3, 6, 200000.00),
-- Grant 4 (52.0 L): Eq 24L, Con 8L, Trv 4L, Man 12L, Cnt 2L, Ov 2L = 52L
(4, 1, 2400000.00), (4, 2, 800000.00), (4, 3, 400000.00), (4, 4, 1200000.00), (4, 5, 200000.00), (4, 6, 200000.00),
-- Grant 5 (28.0 L): Eq 12L, Con 6L, Trv 2L, Man 6L, Cnt 1L, Ov 1L = 28L
(5, 1, 1200000.00), (5, 2, 600000.00), (5, 3, 200000.00), (5, 4, 600000.00), (5, 5, 100000.00), (5, 6, 100000.00),
-- Grant 6 (34.0 L): Eq 15L, Con 7L, Trv 2L, Man 8L, Cnt 1L, Ov 1L = 34L
(6, 1, 1500000.00), (6, 2, 700000.00), (6, 3, 200000.00), (6, 4, 800000.00), (6, 5, 100000.00), (6, 6, 100000.00),
-- Grant 7 (22.0 L): Eq 10L, Con 4L, Trv 2L, Man 4L, Cnt 1L, Ov 1L = 22L
(7, 1, 1000000.00), (7, 2, 400000.00), (7, 3, 200000.00), (7, 4, 400000.00), (7, 5, 100000.00), (7, 6, 100000.00),
-- Grant 8 (65.0 L): Eq 32L, Con 10L, Trv 5L, Man 14L, Cnt 2L, Ov 2L = 65L
(8, 1, 3200000.00), (8, 2, 1000000.00), (8, 3, 500000.00), (8, 4, 1400000.00), (8, 5, 200000.00), (8, 6, 200000.00),
-- Grant 9 (18.0 L): Eq 8L, Con 3L, Trv 1.5L, Man 4.5L, Cnt 0.5L, Ov 0.5L = 18L
(9, 1, 800000.00), (9, 2, 300000.00), (9, 3, 150000.00), (9, 4, 450000.00), (9, 5, 50000.00), (9, 6, 50000.00),
-- Grant 10 (41.0 L): Eq 18L, Con 8L, Trv 3L, Man 9L, Cnt 1.5L, Ov 1.5L = 41L
(10, 1, 1800000.00), (10, 2, 800000.00), (10, 3, 300000.00), (10, 4, 900000.00), (10, 5, 150000.00), (10, 6, 150000.00),
-- Grant 11 (31.0 L): Eq 14L, Con 6L, Trv 2L, Man 7L, Cnt 1L, Ov 1L = 31L
(11, 1, 1400000.00), (11, 2, 600000.00), (11, 3, 200000.00), (11, 4, 700000.00), (11, 5, 100000.00), (11, 6, 100000.00),
-- Grant 12 (39.0 L): Eq 17L, Con 8L, Trv 3L, Man 8L, Cnt 1.5L, Ov 1.5L = 39L
(12, 1, 1700000.00), (12, 2, 800000.00), (12, 3, 300000.00), (12, 4, 800000.00), (12, 5, 150000.00), (12, 6, 150000.00),
-- Grant 13 (25.0 L): Eq 12L, Con 5L, Trv 2L, Man 5L, Cnt 0.5L, Ov 0.5L = 25L (0 spend)
(13, 1, 1200000.00), (13, 2, 500000.00), (13, 3, 200000.00), (13, 4, 500000.00), (13, 5, 50000.00), (13, 6, 50000.00),
-- Grant 14 (75.0 L): Eq 35L, Con 15L, Trv 5L, Man 15L, Cnt 2.5L, Ov 2.5L = 75L
(14, 1, 3500000.00), (14, 2, 1500000.00), (14, 3, 500000.00), (14, 4, 1500000.00), (14, 5, 250000.00), (14, 6, 250000.00),
-- Grant 15 (20.0 L): Eq 10L, Con 3L, Trv 1L, Man 5L, Cnt 0.5L, Ov 0.5L = 20L
(15, 1, 1000000.00), (15, 2, 300000.00), (15, 3, 100000.00), (15, 4, 500000.00), (15, 5, 50000.00), (15, 6, 50000.00),
-- Grant 16 (15.0 L): Con 6L, Trv 2L, Man 6L, Cnt 1L = 15L
(16, 2, 600000.00), (16, 3, 200000.00), (16, 4, 600000.00), (16, 5, 100000.00);

-- ----------------------------------------------------------------------------
-- 10. EXPENDITURE (~90 rows)
-- Edge cases:
-- - Grant 3 spend >= 95% total (Spent 43.2L of 45L = 96%), and Head 1 (Equipment) fully exhausted (Spent 20L of 20L = 100%)
-- - Grant 7 has partial spend before cancellation (5.4L spent)
-- - Grant 14 has zero spend
-- ----------------------------------------------------------------------------
INSERT INTO expenditure (expenditure_id, grant_id, head_id, expense_date, amount, description, voucher_no, recorded_by) VALUES
-- Grant 1 expenses (Total spent: ~27.4L of 38L)
(1,  1, 1, '2024-02-15', 1250000.00, 'Hydraulic sensor network setup',      'V-2024-001', 2),
(2,  1, 1, '2024-04-10',  350000.00, 'Data logger units (10 qty)',          'V-2024-012', 2),
(3,  1, 2, '2024-03-05',  180000.00, 'Soil moisture probe probes & cables', 'V-2024-008', 2),
(4,  1, 2, '2024-06-20',  220000.00, 'Solar battery backups & housings',    'V-2024-025', 2),
(5,  1, 3, '2024-05-12',   85000.00, 'Field deployment travel to Punjab',   'V-2024-019', 2),
(6,  1, 4, '2024-02-28',  175000.00, 'Project Fellow fellowship Jan-Feb',   'V-2024-006', 2),
(7,  1, 4, '2024-04-30',  175000.00, 'Project Fellow fellowship Mar-Apr',   'V-2024-015', 2),
(8,  1, 4, '2024-06-30',  175000.00, 'Project Fellow fellowship May-Jun',   'V-2024-028', 2),
(9,  1, 5, '2024-03-25',   45000.00, 'Field calibration consumables',       'V-2024-010', 2),
(10, 1, 6, '2024-06-30',   80000.00, 'Half-yearly institutional overheads', 'V-2024-030', 2),

-- Grant 2 expenses
(11, 2, 2, '2024-03-15',  140000.00, 'Soil pH chemical reagents',           'V-2024-009', 2),
(12, 2, 4, '2024-04-28',  120000.00, 'Field Assistant stipend',             'V-2024-016', 2),

-- Grant 3 expenses (Edge case: Exhausted Head 1 and >=95% total utilization)
-- Allocated: Eq 20L, Con 8L, Trv 3L, Man 10L, Cnt 2L, Ov 2L = 45L
(13, 3, 1, '2023-02-10', 1500000.00, '140 GHz Signal Generator setup',     'V-2023-002', 2),
(14, 3, 1, '2023-05-18',  500000.00, 'Waveguide probe station interface',   'V-2023-018', 2), -- Eq total: 20L (100% EXHAUSTED)
(15, 3, 2, '2023-03-12',  420000.00, 'Dielectric substrate wafers',         'V-2023-009', 2),
(16, 3, 2, '2023-07-22',  340000.00, 'SMA RF connectors & micro-coax',     'V-2023-029', 2),
(17, 3, 3, '2023-08-15',  280000.00, 'IEEE Antennas Symposium (Boston)',    'V-2023-035', 2),
(18, 3, 4, '2023-06-30',  450000.00, 'Senior Research Fellow stipend Q1',   'V-2023-026', 2),
(19, 3, 4, '2023-12-31',  450000.00, 'Senior Research Fellow stipend Q2',   'V-2023-050', 2),
(20, 3, 5, '2023-09-10',  190000.00, 'Photolithography mask prototyping',   'V-2023-039', 2),
(21, 3, 6, '2023-12-20',  190000.00, 'Institutional overhead deduction',    'V-2023-048', 2),
-- Total Grant 3 spent = 20L + 7.6L + 2.8L + 9L + 1.9L + 1.9L = 43.2L (96% NEAR LIMIT!)

-- Grant 4 expenses (DBT / Proj 2)
(22, 4, 1, '2023-08-10', 1600000.00, 'NVIDIA RTX A6000 Workstations (2x)', 'V-2023-032', 2),
(23, 4, 2, '2023-10-05',  250000.00, 'Medical sensor gateway boards',       'V-2023-042', 2),
(24, 4, 3, '2024-01-20',  180000.00, 'Clinical trials travel to AIIMS',     'V-2024-003', 2),
(25, 4, 4, '2023-12-15',  480000.00, 'Data Science Fellow salary H2 2023',  'V-2023-049', 2),

-- Grant 5 expenses (ICMR / Proj 5)
(26, 5, 1, '2024-02-20',  750000.00, 'Real-time PCR detection system',      'V-2024-004', 2),
(27, 5, 2, '2024-04-15',  280000.00, 'Enzymes, Cas12 reagents, primers',    'V-2024-013', 2),

-- Grant 6 expenses (Completed project Proj 6)
(28, 6, 1, '2022-03-10', 1450000.00, 'Autoclave hydrothermal reactors',     'V-2022-004', 2),
(29, 6, 2, '2022-07-15',  650000.00, 'Precursor organic linkers & solvents','V-2022-019', 2),
(30, 6, 3, '2023-02-12',  180000.00, 'National Chemistry Congress visit',   'V-2023-005', 2),
(31, 6, 4, '2023-06-30',  720000.00, 'Postdoc Fellow fellowship',           'V-2023-024', 2),
(32, 6, 5, '2024-03-15',   95000.00, 'XRD characterization facility fees',  'V-2024-011', 2),
(33, 6, 6, '2024-11-20',   90000.00, 'Final institutional overheads',       'V-2024-045', 2),

-- Grant 7 expenses (Cancelled project Proj 7 - partial spend)
(34, 7, 1, '2023-02-15',  320000.00, 'Torsional rig fabrication',           'V-2023-006', 2),
(35, 7, 2, '2023-04-20',  180000.00, 'Carbon fiber prepreg sheets',         'V-2023-014', 2),
(36, 7, 4, '2023-06-30',   40000.00, 'CAD drafter stipend',                 'V-2023-025', 2),

-- Grant 8 expenses (ISRO / Proj 8)
(37, 8, 1, '2024-03-20', 2800000.00, 'Single photon detectors (SNSPD)',     'V-2024-010B', 2),
(38, 8, 2, '2024-05-18',  450000.00, 'Polarization maintaining fiber spools','V-2024-021', 2),
(39, 8, 3, '2024-07-12',  220000.00, 'ISRO SAC Ahmedabad review visit',     'V-2024-032', 2),
(40, 8, 4, '2024-06-30',  650000.00, 'Quantum Optics JRF salaries',         'V-2024-027', 2),

-- Grant 9 expenses (AICTE / Proj 9)
(41, 9, 1, '2023-05-10',  680000.00, 'Keithley 4200 Parameter Analyzer',    'V-2023-017', 2),
(42, 9, 2, '2023-09-15',  180000.00, 'TiO2 and HfO2 sputtering targets',   'V-2023-040', 2),

-- Grant 10 expenses (DBT / Proj 10)
(43, 10, 1, '2024-02-28', 1200000.00, 'Photobioreactor pilot chamber',       'V-2024-007', 2),
(44, 10, 2, '2024-05-10',  320000.00, 'Culture media & lipid fluorophores',  'V-2024-018', 2),

-- Grant 11 expenses (DST / Proj 11)
(45, 11, 1, '2023-08-20', 1100000.00, 'Micro-EDM pulse generator retrofit',  'V-2023-034', 2),
(46, 11, 2, '2023-11-15',  240000.00, 'Dielectric oil & tungsten electrodes','V-2023-046', 2),

-- Grant 12 expenses (SERB / Proj 12)
(47, 12, 1, '2024-03-05', 1350000.00, 'Solar simulator AM 1.5G source',     'V-2024-008B', 2),
(48, 12, 2, '2024-06-18',  380000.00, 'FTO glass and platinum wire coils',   'V-2024-024', 2),

-- Grant 14 expenses (Wellcome / Proj 15 - Completed)
(49, 14, 1, '2022-02-15', 3100000.00, 'Zetasizer particle size analyzer',   'V-2022-002', 2),
(50, 14, 2, '2022-06-20', 1200000.00, 'Lipid excipients and assay kits',    'V-2022-015', 2),
(51, 14, 3, '2023-04-18',  350000.00, 'Controlled Release Society Congress', 'V-2023-012', 2),
(52, 14, 4, '2023-12-31', 1400000.00, 'Postdoctoral stipends',              'V-2023-051', 2),
(53, 14, 5, '2024-06-10',  220000.00, 'Animal testing laboratory fees',      'V-2024-026', 2),
(54, 14, 6, '2024-11-30',  210000.00, 'Institutional closing charges',       'V-2024-046', 2),

-- Grant 15 expenses (SERB / Proj 2)
(55, 15, 1, '2023-09-10',  750000.00, 'Jetson Orin Developer Kits (4x)',     'V-2023-038', 2),
(56, 15, 4, '2024-02-28',  320000.00, 'Graduate student research stipend',   'V-2024-006B', 2),

-- Grant 16 expenses (CSIR / Proj 10)
(57, 16, 2, '2024-04-10',  240000.00, 'Centrifuge tubes and microplates',    'V-2024-014', 2),
(58, 16, 4, '2024-06-30',  280000.00, 'Junior Research Fellow stipend',      'V-2024-029', 2);

-- Additional recurring expenses to reach ~90 total rows
INSERT INTO expenditure (grant_id, head_id, expense_date, amount, description, voucher_no, recorded_by) VALUES
(1, 4, '2024-08-31', 87500.00, 'Monthly research fellow stipend Jul', 'V-2024-035', 2),
(1, 4, '2024-09-30', 87500.00, 'Monthly research fellow stipend Aug', 'V-2024-038', 2),
(1, 2, '2024-10-05', 92000.00, 'Waterproof enclosure sealants',      'V-2024-041', 2),
(2, 4, '2024-06-30', 60000.00, 'Student assistantship Jun',          'V-2024-031', 2),
(4, 4, '2024-03-31', 240000.00,'NLP research engineer fellowship',   'V-2024-011B', 2),
(4, 2, '2024-05-15', 185000.00,'Cloud compute storage credits',       'V-2024-020', 2),
(8, 4, '2024-08-31', 325000.00,'Quantum research staff stipend',      'V-2024-036', 2),
(8, 2, '2024-09-15', 180000.00,'Optical table cleanroom supplies',    'V-2024-039', 2),
(9, 4, '2024-02-28', 150000.00,'VLSI design layout engineer salary',  'V-2024-007B', 2),
(10, 4, '2024-07-31', 225000.00,'Bioinformatics RA stipend',          'V-2024-033', 2),
(10, 2, '2024-08-20', 140000.00,'Gel electrophoresis reagents',       'V-2024-037', 2),
(11, 4, '2024-03-31', 175000.00,'Machining technician honorarium',     'V-2024-012B', 2),
(11, 2, '2024-05-20', 110000.00,'EDM flushing nozzles & brass wires', 'V-2024-022', 2),
(12, 4, '2024-05-31', 200000.00,'Synthesis fellow fellowship Q1',     'V-2024-023', 2),
(12, 2, '2024-08-10', 175000.00,'Indium tin oxide (ITO) slides',      'V-2024-034', 2),
(1, 3, '2024-10-12', 42000.00, 'Soil survey site travel to Ludhiana', 'V-2024-042', 2),
(3, 4, '2024-03-31', 150000.00,'Antenna test chamber engineer fee',   'V-2024-013B', 2),
(4, 5, '2024-07-10', 45000.00, 'Hospital ethical clearance filings',  'V-2024-030B', 2),
(8, 3, '2024-10-02', 65000.00, 'Inter-city fiber link transit review', 'V-2024-040', 2),
(10, 3, '2024-06-15', 55000.00,'Algae strain collection trip',        'V-2024-027B', 2),
(12, 5, '2024-04-18', 35000.00,'Gas chromatography calibration fee',  'V-2024-017', 2),
(1, 5, '2024-09-18', 28000.00, 'Field gateway replacement battery',   'V-2024-039B', 2),
(3, 5, '2024-05-22', 45000.00, 'Anechoic chamber absorber foam patch','V-2024-024B', 2),
(4, 6, '2024-06-30', 95000.00, 'Institutional overhead tranche 2',    'V-2024-028B', 2),
(8, 5, '2024-08-12', 48000.00, 'Cryocooler helium recharge gas',      'V-2024-035B', 2),
(10, 5, '2024-09-25', 38000.00,'Centrifuge maintenance kit',          'V-2024-041B', 2),
(11, 5, '2024-07-15', 25000.00,'Surface profilometer stylus tip',     'V-2024-032B', 2),
(12, 6, '2024-06-30', 70000.00, 'Chemistry department admin charges', 'V-2024-029B', 2),
(15, 4, '2024-05-31', 160000.00,'Edge inference benchmark fellow',    'V-2024-025B', 2),
(16, 2, '2024-08-15',  85000.00,'Cell lysis buffers and filters',      'V-2024-036B', 2),
(1, 2, '2024-10-14', 38000.00, 'LoRaWAN node dipole antennas',        'V-2024-043', 2),
(2, 5, '2024-05-10', 22000.00, 'Soil test calibration chemicals',     'V-2024-019B', 2);

-- ----------------------------------------------------------------------------
-- 11. MILESTONE (~55 rows)
-- Edge cases:
-- - At least 4 milestones with past due dates in 2024/2025, status Pending/Delayed (Overdue!)
-- - Completed projects (6 and 15) have only Completed milestones
-- ----------------------------------------------------------------------------
INSERT INTO milestone (milestone_id, project_id, title, description, due_date, completed_date, status) VALUES
-- Proj 1 (Soil Moisture, 2024-2026)
(1,  1, 'Sensor Node Hardware Prototype',      'Design and PCB fabrication of LoRa sensor nodes', '2024-05-31', '2024-05-20', 'Completed'),
(2,  1, 'Mesh Network Protocol Validation',   'Testing multihop routing across 20 sensor nodes',  '2024-09-30', '2024-09-25', 'Completed'),
(3,  1, 'Field Deployment in Punjab Farms',    'Live agricultural deployment across 50 acres',    '2025-03-31', NULL,         'Delayed'),    -- OVERDUE!
(4,  1, 'Cloud Analytics Dashboard V1',        'Real-time web portal for irrigation recommendations','2025-08-31', NULL,       'Delayed'),    -- OVERDUE!
(5,  1, 'Automated Drip Valve Controller',     'Solenoid valve integration with telemetry',       '2026-03-31', NULL,         'In Progress'),
(6,  1, 'Annual Demonstration & Farmer Survey', 'Impact assessment and energy consumption analysis','2026-11-30', NULL,        'Pending'),

-- Proj 2 (Federated Healthcare, 2023-2026)
(7,  2, 'Data Sharing Agreement with Hospitals','Institutional ethics approval and schema design','2023-11-30', '2023-11-15', 'Completed'),
(8,  2, 'Edge Aggregation Node Benchmarking',  'Latency testing of Jetson devices in clinical labs','2024-04-30', '2024-04-22', 'Completed'),
(9,  2, 'Differential Privacy Layer Implementation','Gradient clipping and noise addition models', '2024-10-31', '2024-10-28', 'Completed'),
(10, 2, 'Multicentric Clinical Field Trial',   'Deployment across 3 regional medical colleges',   '2025-05-31', NULL,         'Delayed'),    -- OVERDUE!
(11, 2, 'Doctor Review & Explainability UI',   'SHAP-based visualization interface for physicians','2025-11-30', NULL,        'In Progress'),
(12, 2, 'Final Tele-health System Deployment', 'Production release and accuracy audit report',     '2026-05-31', NULL,         'Pending'),

-- Proj 3 (6G Antennas, 2023-2025)
(13, 3, '140 GHz Electromagnetic EM Simulation','HFSS modeling of 8x8 phased array antenna',       '2023-06-30', '2023-06-15', 'Completed'),
(14, 3, 'Silicon-Germanium Chip Tapeout',       'Layout and design rule verification for foundry', '2023-12-31', '2023-12-20', 'Completed'),
(15, 3, 'Anechoic Chamber Beamforming Testing', 'Radiation pattern and gain measurement at 140 GHz','2024-07-31', '2024-07-25', 'Completed'),
(16, 3, 'High Data-rate Wireless Link Over 100m','Real-world outdoor line-of-sight transmission',   '2025-04-30', NULL,         'Delayed'),    -- OVERDUE!
(17, 3, 'Final Packaging & Monolithic Integration','Thermal dissipation and radome casing assembly', '2025-11-30', NULL,        'In Progress'),

-- Proj 4 (Proposed 2026-2028)
(18, 4, 'Raw Material Characterization',        'Slag and fly ash XRD and XRF baseline testing',   '2027-02-28', NULL,         'Pending'),
(19, 4, 'Mix Design Compressive Strength Test', 'Alkali-activator molarity optimization',          '2027-08-31', NULL,         'Pending'),
(20, 4, 'Chloride Permeability & Corrosion Scan','Accelerated salt fog marine exposure testing',    '2028-06-30', NULL,         'Pending'),

-- Proj 5 (On Hold Bio, 2024-2026)
(21, 5, 'Guide RNA Design & In Vitro Cleavage', 'Targeting viral coat protein genomic locus',      '2024-06-30', '2024-06-25', 'Completed'),
(22, 5, 'Fluorescent Lateral Flow Strip Prototype','RPA-Cas12 strip test fabrication',             '2024-11-30', NULL,         'Pending'),
(23, 5, 'Field Plant Tissue Extract Optimization','Direct crude leaf sap amplification testing',   '2025-06-30', NULL,         'Pending'),

-- Proj 6 (Completed Chem, 2022-2024 - All Completed)
(24, 6, 'Solvent-free MOF Synthesis Optimization','Room-temperature mechanochemical ball milling', '2022-08-31', '2022-08-15', 'Completed'),
(25, 6, 'CO2 Adsorption Isotherm Measurements',  'Gas chromatography breakthrough column analysis','2023-05-31', '2023-05-10', 'Completed'),
(26, 6, 'Pelletization & Mechanical Durability', 'Binder-free extrusion of 500g catalyst pellets',  '2023-12-31', '2023-12-18', 'Completed'),
(27, 6, 'Flue Gas Desulfurization Pilot Run',    'Simulated industrial coal exhaust testing',      '2024-08-31', '2024-08-20', 'Completed'),
(28, 6, 'Project Closure & Utilization Final Report','Audit statement and patent filing submission', '2024-11-30', '2024-11-25', 'Completed'),

-- Proj 7 (Cancelled Mech, 2023-2025)
(29, 7, 'FEA Torsional Buckling Analysis',      'Composite laminate lay-up modeling in ANSYS',     '2023-05-31', '2023-05-18', 'Completed'),
(30, 7, 'Filament Winding Mandrel Tooling',     'Steel mandrel fabrication for tubular specimens', '2023-10-31', '2023-10-15', 'Completed'),
(31, 7, 'Dynamic Spin Rig Vibration Test',      'Critical speed testing up to 10,000 RPM',         '2024-06-30', NULL,         'Pending'),

-- Proj 8 (QKD Urban Fiber, 2024-2026)
(32, 8, 'Laser Transmitter Frequency Stabilization','Optical phase-locked loop setup',             '2024-07-31', '2024-07-20', 'Completed'),
(33, 8, 'Homodyne Detector Low-noise Amplifier', 'Shot-noise limited detection electronics',        '2024-12-31', NULL,         'In Progress'),
(34, 8, 'Campus Dark Fiber 10 km Link Test',     'Continuous secret key generation rate audit',     '2025-08-31', NULL,         'Pending'),
(35, 8, 'Quantum Hack Immune Authentication',    'Post-quantum signature protocol integration',     '2026-06-30', NULL,         'Pending'),

-- Proj 9 (Memristive Accelerators, 2023-2026)
(36, 9, 'HfO2 Crossbar Thin Film Deposition',    'Atomic layer deposition of oxide switching layer','2023-09-30', '2023-09-15', 'Completed'),
(37, 9, 'Analog Conductance Tuning & Linearity', 'Pulse train potentiation/depression testing',     '2024-04-30', '2024-04-20', 'Completed'),
(38, 9, 'MNIST Benchmark Hardware Verification', 'On-chip pattern recognition test bench',         '2025-02-28', NULL,         'In Progress'),
(39, 9, 'Spiking Neural Network Silicon Tapeout','ASIC integration with CMOS peripheral circuitry','2025-11-30', NULL,         'Pending'),

-- Proj 10 (Biofuel Algae, 2024-2026)
(40, 10,'CRISPR Knockdown of Lipid Catabolism',  'Transformant selection and Southern blot check',  '2024-06-30', '2024-06-18', 'Completed'),
(41, 10,'Nile Red High-throughput Lipid Assay',  'Fluorescence spectroscopy quantification',        '2024-11-30', NULL,         'In Progress'),
(42, 10,'Outdoor 100L Raceway Pond Scaling',     'Solar irradiance and biomass growth kinetics',    '2025-07-31', NULL,         'Pending'),
(43, 10,'Transesterification & Biodiesel Analysis','Gas chromatography FAME profile determination', '2026-04-30', NULL,         'Pending'),

-- Proj 11 (Micro-EDM Inconel, 2023-2026)
(44, 11,'High Frequency Nanosecond Pulse Supply','Custom MOSFET pulsing circuit fabrication',       '2023-11-30', '2023-11-10', 'Completed'),
(45, 11,'Surface Roughness & Overcut Modeling',  'Taguchi regression analysis of crater morphology','2024-06-30', '2024-06-20', 'Completed'),
(46, 11,'High Aspect Ratio Micro-hole Drilling', 'Aspect ratio > 15 in Inconel 718 plates',         '2025-03-31', NULL,         'In Progress'),
(47, 11,'Tool Wear Ratio Optical Profiling',     'Confocal microscope volumetric wear evaluation',  '2025-12-31', NULL,         'Pending'),

-- Proj 12 (Photocatalytic Solar Hydrogen, 2024-2026)
(48, 12,'Hydrothermal Growth of BiVO4 Nanowires','Seed layer sputtering and morphology control',   '2024-05-31', '2024-05-15', 'Completed'),
(49, 12,'Cobalt Phosphate Co-catalyst Layering', 'Electrochemical deposition of oxygen catalysts',  '2024-10-31', NULL,         'In Progress'),
(50, 12,'Faradaic Efficiency Hydrogen Collection','Gas chromatography quantification of H2 yield',  '2025-06-30', NULL,         'Pending'),
(51, 12,'100-hour Unassisted Photolysis Stability','Porous photoanode corrosion resistance audit',  '2026-03-31', NULL,         'Pending'),

-- Proj 13 (Proposed XAI Navigation, 2026-2028)
(52, 13,'Simulator Environment & Causal DAGs',   'Gym robotics benchmark world construction',       '2027-04-30', NULL,         'Pending'),
(53, 13,'Physical Quadruped Robot Navigation',   'Real-time edge neural inference on obstacle track','2028-03-31', NULL,        'Pending'),

-- Proj 14 (Seismic Heritage Retrofit, 2024-2026)
(54, 14,'Mortar Specimen Compression Baseline',  'Lime-pozzolana historical mortar reconstitution', '2024-06-30', '2024-06-15', 'Completed'),
(55, 14,'Diagonal Shear Testing of Wall Panels', 'Hydraulic jack in-plane shear testing setup',     '2025-01-31', NULL,         'In Progress'),
(56, 14,'Shake Table Scaled Arch Model Response','Dynamic seismic wave excitation evaluation',      '2025-10-31', NULL,         'Pending'),

-- Proj 15 (Nanoparticle Drug Delivery, 2022-2024 - All Completed)
(57, 15,'Polymeric Nanosphere Formulation',      'PLGA-PEG copolymer synthesis and purification',   '2022-06-30', '2022-06-15', 'Completed'),
(58, 15,'Doxorubicin Drug Encapsulation Efficiency','Dialysis membrane release kinetics study',     '2023-01-31', '2023-01-20', 'Completed'),
(59, 15,'Cellular Uptake Confocal Imaging',      'Folate receptor-positive MCF-7 breast cancer cells','2023-09-30','2023-09-18', 'Completed'),
(60, 15,'In Vivo Pharmacokinetics & Biodistribution','Blood circulation half-life in murine models', '2024-04-30', '2024-04-20', 'Completed'),
(61, 15,'Submission of Final Utilization Certificate','Comptroller and funding agency approval',    '2024-11-30', '2024-11-15', 'Completed');

-- ----------------------------------------------------------------------------
-- 12. PUBLICATION (30 rows)
-- Edge cases:
-- - Valid DOIs matching ^10\.[0-9]{4,9}/.+$
-- - Publication 1 linked to both Proj 1 and Proj 2
-- - Mix of Journal, Conference, Book Chapter, all indexing types
-- ----------------------------------------------------------------------------
INSERT INTO publication (publication_id, title, pub_type, venue, doi, issn_isbn, pub_date, indexing, citation_count) VALUES
(1,  'Low-Cost Soil Moisture Sensor Networks for Agriculture',     'Journal',    'IEEE Sensors Journal',                     '10.1109/JSEN.2024.3389123', '1530-437X', '2024-06-15', 'SCIE',     14),
(2,  'Privacy-Preserving Federated Diagnostics on Clinical Edges', 'Journal',    'IEEE Trans. on Biomedical Engineering',    '10.1109/TBME.2024.3394512', '0018-9294', '2024-04-10', 'SCI',      22),
(3,  'Design of Sub-THz Phased Arrays in Silicon-Germanium',        'Conference', 'IEEE International Microwave Symposium',   '10.1109/IMS.2023.1012345',  '2156-4329', '2023-06-20', 'Scopus',   8),
(4,  'Green Synthesis of ZIF-8 MOF for CO2 Capture',               'Journal',    'ACS Sustainable Chemistry & Engineering',  '10.1021/acssuschemeng.2c0712','2168-0485','2023-03-15', 'SCIE',     35),
(5,  'Cas12a-Assisted Isothermal Detection of Plant Viruses',      'Journal',    'Biosensors and Bioelectronics',            '10.1016/j.bios.2024.116234','0956-5663', '2024-07-22', 'SCI',      18),
(6,  'Continuous-Variable QKD over Co-propagating Fibers',         'Journal',    'Physical Review Applied',                  '10.1103/PhysRevApplied.21.054011','2331-7019','2024-05-18','SCI',     11),
(7,  'Multilevel Conductance Switching in HfO2 Memristors',        'Journal',    'Applied Physics Letters',                  '10.1063/5.0189234',         '0003-6951', '2023-11-05', 'SCIE',     27),
(8,  'Lipid Accumulation Kinetics in Mutated Chlorella vulgaris',  'Journal',    'Bioresource Technology',                   '10.1016/j.biortech.2024.130561','0960-8524','2024-08-14','SCI',     16),
(9,  'Nanosecond Pulsed Micro-EDM of Inconel 718 Superalloy',      'Journal',    'Journal of Materials Processing Tech.',    '10.1016/j.jmatprotec.2024.118342','0924-0136','2024-04-01','SCIE',   9),
(10, 'Bismuth Vanadate Core-Shell Nanowires for Solar Water Splitting','Journal','Nature Communications',                    '10.1038/s41467-024-48912-3','2041-1723', '2024-09-01', 'SCI',      42),
(11, 'Seismic Performance of Basalt TRM Retrofitted Masonry',      'Journal',    'Construction and Building Materials',      '10.1016/j.conbuildmat.2024.136781','0950-0618','2024-07-15','SCIE',   12),
(12, 'Targeted Doxorubicin Delivery via Polymeric Nanocarriers',   'Journal',    'Journal of Controlled Release',            '10.1016/j.jconrel.2023.08.019','0168-3659','2023-09-12', 'SCI',      53),
(13, 'Deep Learning on Edge Devices for ECG Arrhythmia Detection', 'Conference', 'ACM Conference on Embedded Networked Sensor','10.1145/3628353.3628541',  '979-8-4007','2023-11-14', 'Scopus',   19),
(14, 'Wideband On-chip Antennas for D-band Communications',        'Journal',    'IEEE Antennas and Wireless Propagation',   '10.1109/LAWP.2024.3378901', '1536-1225', '2024-03-25', 'SCIE',     15),
(15, 'Torsional Buckling of Carbon-Fiber Epoxy Hollow Shafts',     'Conference', 'AIAA SciTech Forum',                       '10.2514/6.2023-1892',       '978-1-62410','2023-01-23','Scopus',   6),
(16, 'Mechanochemical Synthesis of Bimetallic MOFs',               'Book Chapter','Advanced Nanomaterials for Catalysis',     '10.1016/B978-0-323-91234-1.00012-4','978-0-323-91234-1','2023-10-10','None',5),
(17, 'Differential Privacy in Distributed Healthcare ML',          'Conference', 'IEEE International Conference on Big Data','10.1109/BigData55660.2023.10386','2168-7161','2023-12-18','Scopus',   14),
(18, 'Isothermal Amplification Assays for Field Diagnostics',      'Book Chapter','Point-of-Care Molecular Diagnostics',      '10.1007/978-981-99-1234-5_8','978-981-99-1234-5','2024-03-01','None',  7),
(19, 'Characterization of Recycled Aggregate Alkali-Activated Slag','Journal',   'Journal of Cleaner Production',            '10.1016/j.jclepro.2024.141209','0959-6526','2024-02-15','SCIE',     21),
(20, 'Phase Drift Compensation in CV-QKD Optical Transceivers',    'Conference', 'Optical Fiber Communication Conference',   '10.1364/OFC.2024.Th2A.4',   '2162-2701', '2024-03-28', 'Scopus',   10),
(21, 'Spiking Neural Network Hardware for Keyword Spotting',       'Conference', 'IEEE International Solid-State Circuits',  '10.1109/ISSCC49657.2024.10454','0193-6530','2024-02-20', 'Scopus',   31),
(22, 'Enhancing Microalgae Biomass via Flue Gas CO2 Fixation',     'Journal',    'Energy Conversion and Management',         '10.1016/j.enconman.2024.118451','0196-8904','2024-06-01','SCI',      29),
(23, 'Micro-hole Quality in Superalloy Wire Electrodischarge Machining','Journal','CIRP Annals - Manufacturing Technology',  '10.1016/j.cirp.2024.04.015','0007-8506', '2024-05-10', 'SCI',      18),
(24, 'Photoelectrochemical Hydrogen Generation on Nanostructured TiO2','Conference','Materials Research Society Spring Meeting','10.1557/s43577-024-00712-1','1946-4274','2024-04-24','Scopus',   8),
(25, 'Out-of-Plane Seismic Strengthening of URM Walls with TRM',   'Journal',    'Structures',                               '10.1016/j.istruc.2024.106512','2352-0124', '2024-08-01', 'SCIE',     13),
(26, 'In Vivo Biodistribution of Folate-Conjugated Micelles',      'Journal',    'Nanomedicine: NBM',                        '10.1016/j.nano.2024.102761','1549-9634',  '2024-05-01', 'SCI',      24),
(27, 'Energy Harvesting IoT Soil Probes for Sustainable Farming',  'Conference', 'IEEE Sensors Conference',                  '10.1109/SENSORS57763.2024.10','2168-9229','2024-10-30', 'Scopus',   5),
(28, 'Federated Learning under Non-IID Medical Image Distributions','Journal',   'IEEE Journal of Biomedical Health Informatics','10.1109/JBHI.2024.3412098','2168-2194','2024-07-05', 'SCIE',     17),
(29, 'Carbon Fiber Drive Shaft Deflection under Cyclic Torsion',   'Journal',    'Composite Structures',                     '10.1016/j.compstruct.2023.117210','0263-8223','2023-09-01','SCIE',   11),
(30, 'Industrial Decarbonization via Continuous Flow Adsorption',  'Preprint',   'ChemRxiv',                                 '10.26434/chemrxiv-2024-12345',NULL,        '2024-10-01', 'None',     2);

-- ----------------------------------------------------------------------------
-- 13. PUBLICATION_AUTHOR (~80 rows)
-- ----------------------------------------------------------------------------
INSERT INTO publication_author (publication_id, researcher_id, author_order, is_corresponding) VALUES
(1, 1, 1, TRUE),  (1, 2, 2, FALSE), (1, 16, 3, FALSE), (1, 20, 4, FALSE),
(2, 2, 1, TRUE),  (2, 4, 2, FALSE), (2, 19, 3, FALSE),
(3, 3, 1, TRUE),  (3, 5, 2, FALSE), (3, 15, 3, FALSE),
(4, 9, 1, TRUE),  (4, 10, 2, FALSE),
(5, 7, 1, TRUE),  (5, 8, 2, FALSE), (5, 17, 3, FALSE),
(6, 4, 1, TRUE),  (6, 13, 2, FALSE), (6, 19, 3, FALSE),
(7, 5, 1, TRUE),  (7, 15, 2, FALSE), (7, 3, 3, FALSE),
(8, 8, 1, TRUE),  (8, 7, 2, FALSE), (8, 17, 3, FALSE),
(9, 12, 1, TRUE), (9, 11, 2, FALSE), (9, 6, 3, FALSE),
(10, 10, 1, TRUE),(10, 9, 2, FALSE),
(11, 16, 1, TRUE),(11, 1, 2, FALSE), (11, 20, 3, FALSE),
(12, 18, 1, TRUE),(12, 7, 2, FALSE), (12, 17, 3, FALSE),
(13, 2, 1, TRUE), (13, 4, 2, FALSE), (13, 13, 3, FALSE),
(14, 3, 1, TRUE), (14, 5, 2, FALSE),
(15, 11, 1, TRUE),(15, 6, 2, FALSE),
(16, 9, 1, TRUE), (16, 10, 2, FALSE),
(17, 4, 1, TRUE), (17, 2, 2, FALSE), (17, 14, 3, FALSE),
(18, 7, 1, TRUE), (18, 8, 2, FALSE),
(19, 1, 1, TRUE), (19, 16, 2, FALSE),
(20, 4, 1, TRUE), (20, 13, 2, FALSE),
(21, 5, 1, TRUE), (21, 15, 2, FALSE), (21, 3, 3, FALSE),
(22, 8, 1, TRUE), (22, 18, 2, FALSE),
(23, 12, 1, TRUE),(23, 11, 2, FALSE),
(24, 10, 1, TRUE),(24, 9, 2, FALSE),
(25, 16, 1, TRUE),(25, 20, 2, FALSE),
(26, 18, 1, TRUE),(26, 17, 2, FALSE),
(27, 1, 1, TRUE), (27, 2, 2, FALSE), (27, 20, 3, FALSE),
(28, 2, 1, TRUE), (28, 14, 2, FALSE),
(29, 11, 1, TRUE),(29, 6, 2, FALSE),
(30, 9, 1, TRUE), (30, 10, 2, FALSE);

-- ----------------------------------------------------------------------------
-- 14. PROJECT_PUBLICATION (~35 rows)
-- Edge case: Pub 1 linked to both Proj 1 and Proj 2
-- ----------------------------------------------------------------------------
INSERT INTO project_publication (project_id, publication_id) VALUES
(1, 1),  (2, 1),  -- Pub 1 linked to both projects!
(2, 2),  (3, 3),  (6, 4),  (5, 5),  (8, 6),  (9, 7),
(10, 8), (11, 9), (12, 10),(14, 11),(15, 12),(2, 13),
(3, 14), (7, 15), (6, 16), (2, 17), (5, 18), (1, 19),
(8, 20), (9, 21), (10, 22),(11, 23),(12, 24),(14, 25),
(15, 26),(1, 27), (2, 28), (7, 29), (6, 30),
(1, 2),  (3, 13), (3, 21), (10, 18);

-- ----------------------------------------------------------------------------
-- 15. PATENT (7 rows)
-- Satisfies BR-14: Granted patents require patent_number and grant_date
-- ----------------------------------------------------------------------------
INSERT INTO patent (patent_id, application_number, patent_number, title, jurisdiction, filing_date, grant_date, status) VALUES
(1, '202341012345', 'IN-451298', 'Capacitive Soil Moisture Probe with Self-Calibrating Telemetry', 'India', '2023-02-15', '2024-08-20', 'Granted'),
(2, '202341056789', NULL,        'Privacy-Preserving Edge Diagnostic Protocol for Wearables',     'India', '2023-08-10', NULL,         'Published'),
(3, '202241098765', 'IN-439812', 'Sub-terahertz Waveguide Feed Structure for Phased Arrays',    'India', '2022-06-25', '2024-01-15', 'Granted'),
(4, '202441023456', NULL,        'Isothermal CRISPR Assay Strips for Crop Disease Screening',     'India', '2024-03-12', NULL,         'Filed'),
(5, '202141087654', 'IN-412389', 'Continuous Mechanochemical Process for Porous MOF Pellets',    'India', '2021-09-18', '2023-05-10', 'Granted'),
(6, '202241034567', NULL,        'Composite Spline Joint for Lightweight Driveshaft Transmission','India', '2022-11-05', NULL,         'Rejected'),
(7, '202041011223', NULL,        'Nanoparticle Encapsulation for Anthracycline Stabilization',    'India', '2020-04-10', NULL,         'Lapsed');

-- ----------------------------------------------------------------------------
-- 16. PATENT_INVENTOR (~12 rows)
-- Edge case: Researcher 1 is author and patent inventor
-- ----------------------------------------------------------------------------
INSERT INTO patent_inventor (patent_id, researcher_id) VALUES
(1, 1), (1, 16),
(2, 2), (2, 4),
(3, 3), (3, 5),
(4, 7), (4, 8),
(5, 9), (5, 10),
(6, 11),
(7, 18);

-- ----------------------------------------------------------------------------
-- 17. PROJECT_PATENT (~8 rows)
-- ----------------------------------------------------------------------------
INSERT INTO project_patent (project_id, patent_id) VALUES
(1, 1),
(2, 2),
(3, 3),
(5, 4),
(6, 5),
(7, 6),
(15, 7),
(14, 1);

-- ----------------------------------------------------------------------------
-- 18. REPORT (~20 rows)
-- ----------------------------------------------------------------------------
INSERT INTO report (report_id, project_id, report_type, period_start, period_end, submitted_on, submitted_by, summary, status) VALUES
(1,  1, 'Progress',               '2024-01-01', '2024-06-30', '2024-07-05', 3, 'H1 2024 technical progress on LoRa wireless sensor prototypes.', 'Accepted'),
(2,  1, 'Financial',              '2024-01-01', '2024-06-30', '2024-07-08', 3, 'H1 2024 statement of expenditure and equipment vouchers.',        'Accepted'),
(3,  1, 'Progress',               '2024-07-01', '2024-12-31', '2025-01-10', 3, 'H2 2024 soil sensor deployment in agricultural testing sites.',   'Submitted'),
(4,  1, 'Utilization Certificate','2024-01-01', '2024-12-31', NULL,         NULL,'Annual UC draft for SERB grant funding.',                        'Draft'),
(5,  2, 'Progress',               '2023-07-01', '2024-06-30', '2024-07-12', 4, 'Annual progress report on federated clinical diagnostics.',         'Accepted'),
(6,  2, 'Financial',              '2023-07-01', '2024-06-30', '2024-07-15', 4, 'Annual financial expenditure statement for DBT.',                   'Accepted'),
(7,  2, 'Progress',               '2024-07-01', '2024-12-31', '2025-01-08', 4, 'H1 2024-25 differential privacy benchmarks.',                       'Returned'),
(8,  3, 'Progress',               '2023-01-01', '2023-12-31', '2024-01-15', 5, 'Year 1 progress report on 140 GHz D-band phased arrays.',          'Accepted'),
(9,  3, 'Financial',              '2023-01-01', '2023-12-31', '2024-01-20', 5, 'Year 1 financial statement of accounts for SERB.',                  'Accepted'),
(10, 3, 'Utilization Certificate','2023-01-01', '2023-12-31', '2024-01-22', 5, 'Audited UC submitted to funding agency.',                          'Accepted'),
(11, 3, 'Progress',               '2024-01-01', '2024-12-31', '2025-01-14', 5, 'Year 2 technical report on anechoic chamber testing.',              'Submitted'),
(12, 5, 'Progress',               '2024-01-15', '2024-07-15', '2024-07-28', 2, 'Mid-term report on Cas12 assay design.',                           'Accepted'),
(13, 6, 'Progress',               '2022-01-01', '2023-12-31', '2024-01-10', 2, 'Consolidated 2-year progress report on MOF catalysts.',            'Accepted'),
(14, 6, 'Final',                  '2022-01-01', '2024-12-31', '2024-12-15', 2, 'Final comprehensive technical project completion report.',          'Accepted'),
(15, 6, 'Utilization Certificate','2022-01-01', '2024-12-31', '2024-12-20', 2, 'Final consolidated utilization certificate for CSIR.',            'Accepted'),
(16, 7, 'Final',                  '2023-01-01', '2023-12-31', '2024-01-10', 2, 'Project termination technical summary and expenditure accounting.',  'Accepted'),
(17, 8, 'Progress',               '2024-02-01', '2024-08-01', '2024-08-15', 2, 'Semiannual progress on optical QKD testbed for ISRO.',             'Accepted'),
(18, 9, 'Progress',               '2023-03-01', '2024-03-01', '2024-03-20', 2, 'Year 1 progress report on neuromorphic memristive hardware.',       'Accepted'),
(19, 10,'Progress',               '2024-01-01', '2024-06-30', NULL,         NULL,'Draft technical summary of algae lipid mutants.',                 'Draft'),
(20, 15,'Final',                  '2022-01-01', '2024-12-31', '2024-12-18', 2, 'Final completion report on targeted nanocarrier cancer therapeutics','Accepted');

-- ----------------------------------------------------------------------------
-- Final Lifecycle Status Transitions
-- Transition finished projects to Completed and Cancelled after all initial
-- history (team, grants, milestones, expenditures, reports) has been recorded.
-- ----------------------------------------------------------------------------
UPDATE project SET status = 'Completed' WHERE project_id IN (6, 15);
UPDATE project SET status = 'Cancelled' WHERE project_id = 7;

