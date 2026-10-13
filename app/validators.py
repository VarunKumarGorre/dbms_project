"""
RPGMS Input Validators
File: app/validators.py
Author: Antigravity AI

Validates all form fields prior to hitting the database.
Handles regex patterns, boundary conditions, date orders, and financial decimal rules.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Dict, List, Optional, Tuple

REGEX_PROJECT_CODE = re.compile(r"^RP-[0-9]{4}-[0-9]{3}$")
REGEX_DOI = re.compile(r"^10\.[0-9]{4,9}/.+$")
REGEX_ORCID = re.compile(r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$")
REGEX_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
REGEX_PHONE = re.compile(r"^[0-9+() -]{7,15}$")

def validate_required(value: Any, field_name: str) -> Optional[str]:
    """Ensures a field is non-empty after stripping whitespace."""
    if value is None:
        return f"{field_name} is required."
    if isinstance(value, str) and not value.strip():
        return f"{field_name} is required."
    return None

def validate_max_length(value: Optional[str], max_len: int, field_name: str) -> Optional[str]:
    """Validates maximum string length."""
    if value and len(value.strip()) > max_len:
        return f"{field_name} cannot exceed {max_len} characters."
    return None

def validate_email(email: Optional[str], required: bool = True) -> Optional[str]:
    """Validates email format."""
    if not email or not email.strip():
        return "Email is required." if required else None
    email = email.strip()
    if not REGEX_EMAIL.match(email):
        return "Please enter a valid email address."
    return None

def validate_phone(phone: Optional[str]) -> Optional[str]:
    """Validates phone number format."""
    if not phone or not phone.strip():
        return None
    phone = phone.strip()
    if not REGEX_PHONE.match(phone):
        return "Please enter a valid phone number (7-15 digits, +, -)."
    return None

def validate_orcid(orcid: Optional[str]) -> Optional[str]:
    """Validates ORCID identifier format (e.g. 0000-0002-1825-0097)."""
    if not orcid or not orcid.strip():
        return None
    orcid = orcid.strip()
    if not REGEX_ORCID.match(orcid):
        return "ORCID must be in format 0000-0000-0000-0000."
    return None

def validate_project_code(code: Optional[str]) -> Optional[str]:
    """Validates project code format (RP-YYYY-NNN)."""
    if not code or not code.strip():
        return "Project code is required."
    code = code.strip()
    if not REGEX_PROJECT_CODE.match(code):
        return "Project code must match format RP-YYYY-NNN (e.g., RP-2024-001)."
    return None

def validate_doi(doi: Optional[str]) -> Optional[str]:
    """Validates publication DOI format."""
    if not doi or not doi.strip():
        return None
    doi = doi.strip()
    if not REGEX_DOI.match(doi):
        return "DOI must match format 10.NNNN/... (e.g., 10.1109/JSEN.2024.12345)."
    return None

def validate_positive_money(amount_str: Any, field_name: str = "Amount") -> Tuple[Optional[Decimal], Optional[str]]:
    """Validates that a money amount is a positive number with <= 2 decimal places."""
    if amount_str is None or str(amount_str).strip() == "":
        return None, f"{field_name} is required."
    try:
        clean_str = str(amount_str).replace(",", "").replace("₹", "").strip()
        val = Decimal(clean_str)
    except (InvalidOperation, ValueError):
        return None, f"{field_name} must be a valid number."

    if val <= 0:
        return None, f"{field_name} must be greater than zero."

    # Verify at most 2 decimal places
    if val.as_tuple().exponent < -2:
        return None, f"{field_name} cannot have more than 2 decimal places."

    return val, None

def validate_date(date_val: Any, field_name: str = "Date") -> Tuple[Optional[date], Optional[str]]:
    """Parses and validates a date value."""
    if not date_val:
        return None, f"{field_name} is required."
    if isinstance(date_val, date):
        return date_val, None
    try:
        parsed = datetime.strptime(str(date_val).strip(), "%Y-%m-%d").date()
        return parsed, None
    except ValueError:
        return None, f"{field_name} must be a valid date in YYYY-MM-DD format."

def validate_date_range(start_val: Any, end_val: Any, start_label: str = "Start date", end_label: str = "End date") -> Optional[str]:
    """Validates that end date is strictly after start date."""
    d_start, err_start = validate_date(start_val, start_label)
    if err_start:
        return err_start
    d_end, err_end = validate_date(end_val, end_label)
    if err_end:
        return err_end

    if d_end <= d_start:
        return f"{end_label} must be after {start_label}."
    return None

def validate_effort_percent(effort: Any) -> Tuple[Optional[Decimal], Optional[str]]:
    """Validates effort percentage (1 to 100)."""
    if effort is None or str(effort).strip() == "":
        return None, "Effort percentage is required."
    try:
        val = Decimal(str(effort).strip())
    except (InvalidOperation, ValueError):
        return None, "Effort percentage must be a valid number."

    if val <= 0 or val > 100:
        return None, "Effort percentage must be between 1 and 100."
    return val, None
