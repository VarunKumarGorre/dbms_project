# Entity-Relationship (ER) Model

This document outlines the conceptual data model for the Research Project, Publication & Grant Management System (RPGMS). It visualizes all 19 entities, their key attributes, primary and foreign key constraints, and relational cardinalities.

---

## 1. Complete Entity-Relationship Diagram

```mermaid
erDiagram
    DEPARTMENT ||--o{ RESEARCHER : "employs"
    DEPARTMENT ||--o{ PROJECT : "hosts"
    RESEARCHER ||--o| USER_ACCOUNT : "links_to"
    PROJECT ||--|{ PROJECT_INVESTIGATOR : "staffed_by"
    RESEARCHER ||--o{ PROJECT_INVESTIGATOR : "participates_in"
    FUNDING_AGENCY ||--o{ GRANT_AWARD : "sanctions"
    PROJECT ||--o{ GRANT_AWARD : "awarded_to"
    GRANT_AWARD ||--|{ GRANT_BUDGET_ALLOCATION : "subdivided_into"
    BUDGET_HEAD ||--o{ GRANT_BUDGET_ALLOCATION : "classifies"
    GRANT_BUDGET_ALLOCATION ||--o{ EXPENDITURE : "spent_against"
    USER_ACCOUNT ||--o{ EXPENDITURE : "audits_recording_of"
    PROJECT ||--o{ MILESTONE : "schedules"
    PUBLICATION ||--|{ PUBLICATION_AUTHOR : "credits"
    RESEARCHER ||--o{ PUBLICATION_AUTHOR : "authors"
    PROJECT ||--o{ PROJECT_PUBLICATION : "produces"
    PUBLICATION ||--o{ PROJECT_PUBLICATION : "credited_to"
    PATENT ||--|{ PATENT_INVENTOR : "credits"
    RESEARCHER ||--o{ PATENT_INVENTOR : "invents"
    PROJECT ||--o{ PROJECT_PATENT : "yields"
    PATENT ||--o{ PROJECT_PATENT : "credited_to"
    PROJECT ||--o{ REPORT : "documents"
    USER_ACCOUNT ||--o{ REPORT : "submits"

    DEPARTMENT {
        int dept_id PK
        string dept_code UK
        string dept_name UK
        string building
        string contact_email
    }

    RESEARCHER {
        int researcher_id PK
        string employee_code UK
        string first_name
        string last_name
        string email UK
        string phone
        string designation
        int dept_id FK
        string orcid_id UK
        date joined_date
        boolean is_active
    }

    USER_ACCOUNT {
        int user_id PK
        string username UK
        string password_hash
        string role
        int researcher_id FK
        boolean is_active
    }

    FUNDING_AGENCY {
        int agency_id PK
        string agency_name UK
        string agency_type
        string country
        string contact_email
        string website
    }

    PROJECT {
        int project_id PK
        string project_code UK
        string title
        string abstract
        int dept_id FK
        date start_date
        date end_date
        string status
    }

    PROJECT_INVESTIGATOR {
        int project_id PK,FK
        int researcher_id PK,FK
        string role
        date assigned_date
        decimal effort_percent
        int pi_flag UK
    }

    GRANT_AWARD {
        int grant_id PK
        string grant_number UK
        int project_id FK
        int agency_id FK
        decimal grant_amount
        date sanction_date
        date grant_start
        date grant_end
        string status
    }

    BUDGET_HEAD {
        int head_id PK
        string head_name UK
        string description
    }

    GRANT_BUDGET_ALLOCATION {
        int grant_id PK,FK
        int head_id PK,FK
        decimal allocated_amount
    }

    EXPENDITURE {
        int expenditure_id PK
        int grant_id FK
        int head_id FK
        date expense_date
        decimal amount
        string description
        string voucher_no UK
        int recorded_by FK
    }

    MILESTONE {
        int milestone_id PK
        int project_id FK
        string title UK
        string description
        date due_date
        date completed_date
        string status
    }

    PUBLICATION {
        int publication_id PK
        string title
        string pub_type
        string venue
        string doi UK
        string issn_isbn
        date pub_date
        string indexing
        int citation_count
    }

    PUBLICATION_AUTHOR {
        int publication_id PK,FK
        int researcher_id PK,FK
        int author_order UK
        boolean is_corresponding
    }

    PROJECT_PUBLICATION {
        int project_id PK,FK
        int publication_id PK,FK
    }

    PATENT {
        int patent_id PK
        string application_number UK
        string patent_number UK
        string title
        string jurisdiction
        date filing_date
        date grant_date
        string status
    }

    PATENT_INVENTOR {
        int patent_id PK,FK
        int researcher_id PK,FK
    }

    PROJECT_PATENT {
        int project_id PK,FK
        int patent_id PK,FK
    }

    REPORT {
        int report_id PK
        int project_id FK
        string report_type
        date period_start
        date period_end
        date submitted_on
        int submitted_by FK
        string summary
        string status
    }

    AUDIT_LOG {
        bigint log_id PK
        string table_name
        string record_id
        string action
        json old_values
        json new_values
        string changed_by
    }
```

---

## 2. Plain-Language Tour of the Model

The RPGMS data model is architected around the operational reality of university research administration:

1. **Academic Organization:**
   - A `DEPARTMENT` anchors academic faculties and research projects.
   - Each `RESEARCHER` belongs to exactly one department (`1 : N`), while a department hosts multiple faculty members and students.
   - Faculty members can be assigned a `USER_ACCOUNT` (`0..1 : 0..1`), linking web login identities to academic researcher profiles.

2. **Project Governance & Staffing:**
   - A `PROJECT` represents an approved research initiative, hosted in a department (`1 : N`).
   - Researchers join projects through `PROJECT_INVESTIGATOR` (`M : N`).
   - A key constraint in this relationship is the **Principal Investigator (PI) Invariant**: every project must have exactly one PI. This is modeled using a stored generated column `pi_flag` (value `1` for PI, `NULL` otherwise) and a unique key on `(project_id, pi_flag)`. MySQL unique indexes permit multiple `NULL` values but strictly one `1`, enforcing that a project never has more than one PI.

3. **Financial Lifecycle (Grants, Allocations & Expenditures):**
   - External sponsors (`FUNDING_AGENCY`) sanction `GRANT_AWARD` records for specific projects (`1 : N`).
   - Rather than spending freely against a lump sum, a grant is subdivided across standardized expense categories (`BUDGET_HEAD`) in `GRANT_BUDGET_ALLOCATION` (`M : N`).
   - When money is spent, an `EXPENDITURE` row is recorded. Notice the **composite foreign key** `(grant_id, head_id)` pointing directly to `GRANT_BUDGET_ALLOCATION`. This enforces at the database constraint level that money can only be disbursed against a budget head that was formally allocated to that specific grant.

4. **Technical Progress & Reporting:**
   - Deliverables are scheduled in `MILESTONE` with explicit due dates bounded by the parent project's lifetime.
   - Periodical compliance and progress are recorded in `REPORT`, tracking draft, submission, and research office review stages.

5. **Scholarly & Intellectual Output:**
   - Research papers (`PUBLICATION`) credit multiple researchers in an ordered sequence through `PUBLICATION_AUTHOR` (`M : N`), and are linked to the sponsoring grants via `PROJECT_PUBLICATION` (`M : N`).
   - Inventions (`PATENT`) track legal statuses (Filed, Published, Granted) and are attributed to inventors via `PATENT_INVENTOR` and projects via `PROJECT_PATENT`.

6. **System Accountability:**
   - Every state change across these 18 business entities triggers an automated entry in `AUDIT_LOG`, capturing the mutation type, affected table and record identifier, previous and new JSON row representations, timestamp, and authenticated application username (`@rpgms_actor`).
