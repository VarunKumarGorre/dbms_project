"""
RPGMS Utility Functions & Jinja2 Filters
File: app/utils.py
Author: Antigravity AI

Provides:
- Indian currency formatting (inr, inr_compact)
- Percentage and date formatting (pct, date_short, date_rel)
- Avatar initials and deterministic avatar color generator
- Safe URL return redirect helper
"""

from datetime import date, datetime
from decimal import Decimal
import hashlib
from typing import Optional, Union
from urllib.parse import urlparse, urljoin
from flask import request

def format_inr(amount: Optional[Union[float, int, Decimal, str]]) -> str:
    """Formats a number into Indian currency style: ₹ 12,34,567.00"""
    if amount is None or amount == "":
        return "₹ 0.00"
    try:
        val = Decimal(str(amount))
    except Exception:
        return "₹ 0.00"

    is_negative = val < 0
    val = abs(val)

    # Split into integer and decimal portions
    formatted_val = f"{val:.2f}"
    parts = formatted_val.split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) <= 3:
        grouped = integer_part
    else:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        # Group remaining in blocks of 2
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        grouped = ",".join(groups) + "," + last_three

    sign = "-" if is_negative else ""
    return f"{sign}₹ {grouped}.{decimal_part}"

def format_inr_compact(amount: Optional[Union[float, int, Decimal, str]]) -> str:
    """Formats numbers into compact Indian denominations: ₹ 12.3 L, ₹ 4.82 Cr, ₹ 85 K"""
    if amount is None or amount == "":
        return "₹ 0"
    try:
        val = float(amount)
    except Exception:
        return "₹ 0"

    sign = "-" if val < 0 else ""
    val = abs(val)

    if val >= 10000000:
        cr = val / 10000000
        return f"{sign}₹ {cr:.2f} Cr".rstrip("0").rstrip(".") if cr % 1 != 0 else f"{sign}₹ {int(cr)} Cr"
    elif val >= 100000:
        lac = val / 100000
        return f"{sign}₹ {lac:.2f} L".rstrip("0").rstrip(".") if lac % 1 != 0 else f"{sign}₹ {int(lac)} L"
    elif val >= 1000:
        k = val / 1000
        return f"{sign}₹ {k:.1f} K".rstrip("0").rstrip(".") if k % 1 != 0 else f"{sign}₹ {int(k)} K"
    else:
        return f"{sign}₹ {int(val)}"

def format_pct(value: Optional[Union[float, int, Decimal, str]], decimals: int = 1) -> str:
    """Formats number as percentage: 72.5%"""
    if value is None or value == "":
        return "0%"
    try:
        val = float(value)
        return f"{val:.{decimals}f}%"
    except Exception:
        return "0%"

def format_date_short(dt: Optional[Union[date, datetime, str]]) -> str:
    """Formats date as: 12 Mar 2026"""
    if dt is None or dt == "":
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, "%Y-%m-%d").date()
        except Exception:
            return dt
    return dt.strftime("%d %b %Y")

def format_date_rel(dt: Optional[Union[date, datetime, str]]) -> str:
    """Formats relative date: in 12 days / 8 days overdue / today"""
    if dt is None or dt == "":
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, "%Y-%m-%d").date()
        except Exception:
            return dt
    elif isinstance(dt, datetime):
        dt = dt.date()

    today = date.today()
    delta = (dt - today).days

    if delta == 0:
        return "today"
    elif delta > 0:
        return f"in {delta} days" if delta != 1 else "tomorrow"
    else:
        overdue_days = abs(delta)
        return f"{overdue_days} days overdue" if overdue_days != 1 else "1 day overdue"

def get_initials(name: Optional[str]) -> str:
    """Extracts uppercase initials from a name (e.g., 'Anand Rao' -> 'AR')."""
    if not name:
        return "??"
    parts = name.strip().split()
    if not parts:
        return "??"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()

AVATAR_PALETTE = [
    ("#EBF3FE", "#2457D6"),  # Blue
    ("#E3F6EE", "#166A49"),  # Green
    ("#FFF3D9", "#805000"),  # Amber
    ("#FDE8E8", "#A62929"),  # Red
    ("#E4F2FC", "#145C8A"),  # Cyan
    ("#F3E8FF", "#6B21A8"),  # Purple
    ("#FDF2F8", "#9D174D"),  # Pink
    ("#EDEFF5", "#4B5368"),  # Neutral
]

def get_avatar_color(name: Optional[str]) -> tuple:
    """Returns (bg_color, text_color) based on a deterministic hash of the name."""
    if not name:
        return AVATAR_PALETTE[0]
    idx = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16) % len(AVATAR_PALETTE)
    return AVATAR_PALETTE[idx]

def is_safe_url(target: str) -> bool:
    """Validates that a redirect target URL is local and safe."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc

def safe_return_to(fallback: str) -> str:
    """Returns validated return_to URL from GET parameter or falls back."""
    target = request.args.get("return_to")
    if target and is_safe_url(target):
        return target
    return fallback
