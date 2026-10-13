"""
RPGMS Database Error Handler & Message Mapper
File: app/errors.py
Author: Antigravity AI

Converts raw MySQL exceptions, trigger signals, and CHECK constraint failures
into human-friendly, informative error messages.
"""

import re
import mysql.connector

RULE_MESSAGES = {
    "BR-01": "End date must be after the start date.",
    "BR-02": "Grant dates are invalid. The end date must be after the start date, and the grant cannot start before its sanction date.",
    "BR-03": "The grant period must fall inside the parent project's lifetime.",
    "BR-04": "The milestone due or completion date must fall inside the project's dates.",
    "BR-05": "Grant, allocation and expenditure amounts must be strictly greater than zero.",
    "BR-06": "This expenditure would exceed the remaining budget for this head or total grant.",
    "BR-07": "The expense date must be within the grant period.",
    "BR-08": "A publication with this DOI already exists, or the DOI format is invalid.",
    "BR-09": "Budget allocations cannot exceed the grant amount, and the amount cannot be reduced below existing allocations or spending.",
    "BR-10": "This project must have exactly one Principal Investigator. Use Change PI to transfer responsibility.",
    "BR-11": "This assignment would exceed the 100% effort limit across active projects for this researcher.",
    "BR-12": "Inactive researchers cannot be assigned to projects.",
    "BR-13": "A completed milestone needs a completion date; non-completed milestones cannot have one.",
    "BR-14": "A granted patent needs a valid patent number and grant date on or after its filing date.",
    "BR-15": "Select a budget head that is allocated to this grant.",
    "BR-16": "The publication date cannot be earlier than the start date of a linked project.",
    "BR-17": "This project is closed (Completed or Cancelled); new expenditures, milestones, or team assignments are forbidden.",
    "BR-18": "Each author must appear once per publication and author order must be unique.",
}

CONSTRAINT_TO_RULE = {
    "chk_proj_dates": "BR-01",
    "chk_gr_dates": "BR-02",
    "chk_gr_amount": "BR-05",
    "chk_alloc_amount": "BR-05",
    "chk_exp_amount": "BR-05",
    "chk_pub_doi": "BR-08",
    "uq_one_pi_per_project": "BR-10",
    "chk_ms_completion": "BR-13",
    "chk_pat_dates": "BR-14",
    "chk_pat_status": "BR-14",
    "fk_exp_alloc": "BR-15",
    "uq_author_order": "BR-18",
}

def format_db_error(err: Exception) -> str:
    """Translates a database exception into a user-friendly UI message."""
    if not isinstance(err, mysql.connector.Error):
        return str(err)

    msg = err.msg or ""

    # 1. Custom Trigger/Procedure Signal with BR-xx prefix
    br_match = re.search(r"(BR-\d{2})[:\s]*(.*)", msg)
    if br_match:
        rule_code = br_match.group(1)
        detail = br_match.group(2).strip()
        custom_msg = detail if detail else RULE_MESSAGES.get(rule_code, "Business rule violated.")
        return f"{custom_msg} (rule {rule_code})"

    # 2. Check Constraint Failures (MySQL 3819)
    if err.errno == 3819:
        for constraint, rule_code in CONSTRAINT_TO_RULE.items():
            if constraint in msg:
                return f"{RULE_MESSAGES[rule_code]} (rule {rule_code})"
        return "The entered data violates validation constraints."

    # 3. Duplicate Key (MySQL 1062)
    if err.errno == 1062:
        if "doi" in msg:
            return f"{RULE_MESSAGES['BR-08']} (rule BR-08)"
        if "uq_one_pi_per_project" in msg:
            return f"{RULE_MESSAGES['BR-10']} (rule BR-10)"
        if "uq_author_order" in msg or "PRIMARY" in msg and "publication_author" in msg:
            return f"{RULE_MESSAGES['BR-18']} (rule BR-18)"
        if "project_code" in msg:
            return "That project code is already in use."
        if "grant_number" in msg:
            return "That grant number is already in use."
        if "voucher_no" in msg:
            return "That voucher number has already been recorded."
        if "username" in msg:
            return "That username is already taken."
        return "That record or unique identifier is already in use."

    # 4. Foreign Key Constraints (MySQL 1451, 1452)
    if err.errno in (1451, 1452):
        if "fk_exp_alloc" in msg:
            return f"{RULE_MESSAGES['BR-15']} (rule BR-15)"
        if err.errno == 1451:
            return "Cannot delete or modify this record because related operational records depend on it."
        return "The referenced entity does not exist in the database."

    # 5. Fallback clean message
    return "An error occurred while saving to the database. No changes were made."
