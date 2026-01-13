from __future__ import annotations

from datetime import date, datetime


def parse_date_ddmmyyyy_or_iso(value: str) -> date:
    """Parse either DD/MM/YYYY or ISO (YYYY-MM-DD) into a date."""

    raw = (value or "").strip()
    if not raw:
        raise ValueError("Empty date")

    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except Exception:
            continue

    raise ValueError("Invalid date format")


def format_date_ddmmyyyy(value: object) -> str:
    """Format a date-like value into DD/MM/YYYY for templates.

    Supports: date, datetime, ISO string (YYYY-MM-DD), DD/MM/YYYY, or None.
    """

    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")

    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    raw = str(value).strip()
    if not raw:
        return ""

    # Already DD/MM/YYYY
    if len(raw) == 10 and raw[2] == "/" and raw[5] == "/":
        return raw

    # Try ISO
    try:
        d = date.fromisoformat(raw)
        return d.strftime("%d/%m/%Y")
    except Exception:
        return raw


def format_datetime_ddmmyyyy_hhmm(value: object) -> str:
    """Format a datetime-like value into DD/MM/YYYY HH:MM.

    Supports: datetime, date, ISO strings, DD/MM/YYYY, or None.
    """

    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")

    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    raw = str(value).strip()
    if not raw:
        return ""

    # Already DD/MM/YYYY (optionally with time)
    if len(raw) >= 10 and raw[2] == "/" and raw[5] == "/":
        return raw

    # Try ISO datetime, then ISO date
    try:
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass

    try:
        d = date.fromisoformat(raw)
        return d.strftime("%d/%m/%Y")
    except Exception:
        return raw
