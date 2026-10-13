-- ============================================================================
-- RPGMS Database Schema DDL
-- File: db/01_schema.sql
-- Description: Table DDL definitions for the 19 core entities.
-- Note: Does NOT contain DROP, CREATE, or USE database statements.
--       Executed inside the allowlisted database selected by db/setup_db.py.
-- ============================================================================

CREATE TABLE department (
  dept_id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  dept_code      VARCHAR(10)  NOT NULL UNIQUE,
  dept_name      VARCHAR(100) NOT NULL UNIQUE,
  building       VARCHAR(60),
  contact_email  VARCHAR(120),
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_dept_email CHECK (contact_email IS NULL OR contact_email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE researcher (
  researcher_id  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  employee_code  VARCHAR(20) NOT NULL UNIQUE,
  first_name     VARCHAR(50) NOT NULL,
  last_name      VARCHAR(50) NOT NULL,
  email          VARCHAR(120) NOT NULL UNIQUE,
  phone          VARCHAR(15),
  designation    ENUM('Professor','Associate Professor','Assistant Professor',
                      'Research Scholar','Postdoctoral Fellow','Research Associate') NOT NULL,
  dept_id        INT UNSIGNED NOT NULL,
  orcid_id       CHAR(19) UNIQUE,
  joined_date    DATE NOT NULL,
  is_active      BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT fk_res_dept  FOREIGN KEY (dept_id) REFERENCES department(dept_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_res_email CHECK (email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}$'),
  CONSTRAINT chk_res_phone CHECK (phone IS NULL OR phone REGEXP '^[0-9+() -]{7,15}$'),
  CONSTRAINT chk_res_orcid CHECK (orcid_id IS NULL OR
                                  orcid_id REGEXP '^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user_account (
  user_id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  username       VARCHAR(40)  NOT NULL UNIQUE,
  password_hash  VARCHAR(100) NOT NULL,                 -- bcrypt hash, never plain text
  role           ENUM('ADMIN','RESEARCH_OFFICER','PI','VIEWER') NOT NULL DEFAULT 'VIEWER',
  researcher_id  INT UNSIGNED UNIQUE,                   -- required when role = 'PI'
  is_active      BOOLEAN NOT NULL DEFAULT TRUE,
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_user_res FOREIGN KEY (researcher_id) REFERENCES researcher(researcher_id)
                         ON UPDATE RESTRICT ON DELETE RESTRICT,
  CONSTRAINT chk_user_pi_link CHECK (role <> 'PI' OR researcher_id IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE funding_agency (
  agency_id      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  agency_name    VARCHAR(120) NOT NULL UNIQUE,
  agency_type    ENUM('Government','Private','Industry','International','Institutional') NOT NULL,
  country        VARCHAR(60) NOT NULL DEFAULT 'India',
  contact_email  VARCHAR(120),
  website        VARCHAR(200),
  CONSTRAINT chk_ag_email CHECK (contact_email IS NULL OR contact_email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project (
  project_id     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  project_code   VARCHAR(20)  NOT NULL UNIQUE,          -- e.g. RP-2024-001
  title          VARCHAR(200) NOT NULL,
  abstract       TEXT,
  dept_id        INT UNSIGNED NOT NULL,
  start_date     DATE NOT NULL,
  end_date       DATE NOT NULL,
  status         ENUM('Proposed','Active','On Hold','Completed','Cancelled') NOT NULL DEFAULT 'Proposed',
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_proj_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_proj_dates CHECK (end_date > start_date),                      -- BR-01
  CONSTRAINT chk_proj_code  CHECK (project_code REGEXP '^RP-[0-9]{4}-[0-9]{3}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project_investigator (
  project_id     INT UNSIGNED NOT NULL,
  researcher_id  INT UNSIGNED NOT NULL,
  role           ENUM('PI','Co-PI','Researcher','Research Scholar') NOT NULL,
  assigned_date  DATE NOT NULL,
  effort_percent DECIMAL(5,2) NOT NULL DEFAULT 10.00,
  -- Exactly one PI per project: pi_flag is 1 only for PI rows, NULL otherwise;
  -- UNIQUE allows many NULLs but only one '1' per project.
  pi_flag        TINYINT GENERATED ALWAYS AS (IF(role = 'PI', 1, NULL)) STORED,
  PRIMARY KEY (project_id, researcher_id),
  UNIQUE KEY uq_one_pi_per_project (project_id, pi_flag),                       -- BR-10
  CONSTRAINT fk_pi_proj FOREIGN KEY (project_id)    REFERENCES project(project_id)
                        ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_pi_res  FOREIGN KEY (researcher_id) REFERENCES researcher(researcher_id)
                        ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_pi_effort CHECK (effort_percent > 0 AND effort_percent <= 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE grant_award (
  grant_id       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  grant_number   VARCHAR(40) NOT NULL UNIQUE,
  project_id     INT UNSIGNED NOT NULL,
  agency_id      INT UNSIGNED NOT NULL,
  grant_amount   DECIMAL(14,2) NOT NULL,
  sanction_date  DATE NOT NULL,
  grant_start    DATE NOT NULL,
  grant_end      DATE NOT NULL,
  status         ENUM('Sanctioned','Active','Closed','Terminated') NOT NULL DEFAULT 'Sanctioned',
  CONSTRAINT fk_gr_proj   FOREIGN KEY (project_id) REFERENCES project(project_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_gr_agency FOREIGN KEY (agency_id)  REFERENCES funding_agency(agency_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_gr_amount CHECK (grant_amount > 0),                            -- BR-05
  CONSTRAINT chk_gr_dates  CHECK (grant_end > grant_start AND grant_start >= sanction_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE budget_head (
  head_id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  head_name      VARCHAR(50) NOT NULL UNIQUE,
  description    VARCHAR(200)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE grant_budget_allocation (
  grant_id         INT UNSIGNED NOT NULL,
  head_id          INT UNSIGNED NOT NULL,
  allocated_amount DECIMAL(14,2) NOT NULL,
  PRIMARY KEY (grant_id, head_id),
  CONSTRAINT fk_alloc_grant FOREIGN KEY (grant_id) REFERENCES grant_award(grant_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_alloc_head  FOREIGN KEY (head_id)  REFERENCES budget_head(head_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_alloc_amount CHECK (allocated_amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE expenditure (
  expenditure_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  grant_id       INT UNSIGNED NOT NULL,
  head_id        INT UNSIGNED NOT NULL,
  expense_date   DATE NOT NULL,
  amount         DECIMAL(14,2) NOT NULL,
  description    VARCHAR(250) NOT NULL,
  voucher_no     VARCHAR(30) NOT NULL UNIQUE,
  recorded_by    INT UNSIGNED,
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  -- composite FK: you can only spend on a head that was actually allocated for that grant
  CONSTRAINT fk_exp_alloc FOREIGN KEY (grant_id, head_id)
                          REFERENCES grant_budget_allocation(grant_id, head_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_exp_user  FOREIGN KEY (recorded_by) REFERENCES user_account(user_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_exp_amount CHECK (amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE milestone (
  milestone_id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  project_id     INT UNSIGNED NOT NULL,
  title          VARCHAR(150) NOT NULL,
  description    VARCHAR(500),
  due_date       DATE NOT NULL,
  completed_date DATE,
  status         ENUM('Pending','In Progress','Completed','Delayed') NOT NULL DEFAULT 'Pending',
  UNIQUE KEY uq_milestone_title (project_id, title),
  CONSTRAINT fk_ms_proj FOREIGN KEY (project_id) REFERENCES project(project_id)
                        ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_ms_completion CHECK (
      (status = 'Completed' AND completed_date IS NOT NULL) OR
      (status <> 'Completed' AND completed_date IS NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE publication (
  publication_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title          VARCHAR(300) NOT NULL,
  pub_type       ENUM('Journal','Conference','Book Chapter','Book','Preprint') NOT NULL,
  venue          VARCHAR(200) NOT NULL,                -- journal / conference / publisher name
  doi            VARCHAR(100) UNIQUE,                  -- BR-08 unique publication identifier
  issn_isbn      VARCHAR(20),
  pub_date       DATE NOT NULL,
  indexing       ENUM('Scopus','SCI','SCIE','WoS','UGC-CARE','None') NOT NULL DEFAULT 'None',
  citation_count INT UNSIGNED NOT NULL DEFAULT 0,
  CONSTRAINT chk_pub_doi CHECK (doi IS NULL OR doi REGEXP '^10\\.[0-9]{4,9}/.+$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE publication_author (
  publication_id  INT UNSIGNED NOT NULL,
  researcher_id   INT UNSIGNED NOT NULL,
  author_order    TINYINT UNSIGNED NOT NULL,
  is_corresponding BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (publication_id, researcher_id),
  UNIQUE KEY uq_author_order (publication_id, author_order),
  CONSTRAINT fk_pa_pub FOREIGN KEY (publication_id) REFERENCES publication(publication_id)
                       ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_pa_res FOREIGN KEY (researcher_id)  REFERENCES researcher(researcher_id)
                       ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_pa_order CHECK (author_order >= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project_publication (
  project_id     INT UNSIGNED NOT NULL,
  publication_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (project_id, publication_id),
  CONSTRAINT fk_pp_proj FOREIGN KEY (project_id)     REFERENCES project(project_id)         ON DELETE CASCADE,
  CONSTRAINT fk_pp_pub  FOREIGN KEY (publication_id) REFERENCES publication(publication_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE patent (
  patent_id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  application_number VARCHAR(40) NOT NULL UNIQUE,
  patent_number      VARCHAR(40) UNIQUE,                -- NULL until granted
  title              VARCHAR(300) NOT NULL,
  jurisdiction       VARCHAR(40) NOT NULL DEFAULT 'India',
  filing_date        DATE NOT NULL,
  grant_date         DATE,
  status             ENUM('Filed','Published','Granted','Rejected','Lapsed') NOT NULL DEFAULT 'Filed',
  CONSTRAINT chk_pat_dates  CHECK (grant_date IS NULL OR grant_date >= filing_date),
  CONSTRAINT chk_pat_status CHECK ((status = 'Granted' AND grant_date IS NOT NULL AND patent_number IS NOT NULL)
                                   OR status <> 'Granted')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE patent_inventor (
  patent_id     INT UNSIGNED NOT NULL,
  researcher_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (patent_id, researcher_id),
  CONSTRAINT fk_pi2_pat FOREIGN KEY (patent_id)     REFERENCES patent(patent_id)       ON DELETE CASCADE,
  CONSTRAINT fk_pi2_res FOREIGN KEY (researcher_id) REFERENCES researcher(researcher_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project_patent (
  project_id INT UNSIGNED NOT NULL,
  patent_id  INT UNSIGNED NOT NULL,
  PRIMARY KEY (project_id, patent_id),
  CONSTRAINT fk_ppt_proj FOREIGN KEY (project_id) REFERENCES project(project_id) ON DELETE CASCADE,
  CONSTRAINT fk_ppt_pat  FOREIGN KEY (patent_id)  REFERENCES patent(patent_id)   ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE report (
  report_id      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  project_id     INT UNSIGNED NOT NULL,
  report_type    ENUM('Progress','Financial','Utilization Certificate','Final') NOT NULL,
  period_start   DATE NOT NULL,
  period_end     DATE NOT NULL,
  submitted_on   DATE,
  submitted_by   INT UNSIGNED,
  summary        TEXT,
  status         ENUM('Draft','Submitted','Accepted','Returned') NOT NULL DEFAULT 'Draft',
  CONSTRAINT fk_rep_proj FOREIGN KEY (project_id)   REFERENCES project(project_id)       ON DELETE RESTRICT,
  CONSTRAINT fk_rep_user FOREIGN KEY (submitted_by) REFERENCES user_account(user_id)     ON DELETE RESTRICT,
  CONSTRAINT chk_rep_period CHECK (period_end >= period_start),
  CONSTRAINT chk_rep_submit CHECK ((status = 'Draft' AND submitted_on IS NULL AND submitted_by IS NULL) OR
                                      (status <> 'Draft' AND submitted_on IS NOT NULL AND submitted_by IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE audit_log (
  log_id      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  table_name  VARCHAR(40) NOT NULL,
  record_id   VARCHAR(40) NOT NULL,
  action      ENUM('INSERT','UPDATE','DELETE') NOT NULL,
  old_values  JSON,
  new_values  JSON,
  changed_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  changed_by  VARCHAR(80) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
