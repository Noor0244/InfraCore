from __future__ import annotations

import re
from datetime import datetime

from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from app.utils.dates import format_date_ddmmyyyy, format_datetime_ddmmyyyy_hhmm


_UNIT_EXP_RE = re.compile(r"(\d+)")


def format_unit_sup(value: str | None) -> Markup:
    text = str(value or "").strip()
    if not text:
        return Markup("")
    # First escape the text, then apply regex and wrap in Markup
    escaped_text = str(escape(text))
    formatted = _UNIT_EXP_RE.sub(r"<sup>\1</sup>", escaped_text)
    return Markup(f'<span class="unit-text">{formatted}</span>')


def local_dt(dt, tz_name='Asia/Kolkata', fmt='%d/%m/%Y %H:%M:%S') -> str:
    """Convert UTC datetime to local timezone."""
    if not dt:
        return ''
    
    try:
        import pytz
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        local = dt.astimezone(pytz.timezone(tz_name))
        return local.strftime(fmt)
    except Exception:
        # Fallback if pytz not available or other issues
        if hasattr(dt, 'strftime'):
            return dt.strftime(fmt)
        return str(dt)


def register_template_filters(templates: Jinja2Templates) -> None:
    """Register shared Jinja filters on a templates instance."""

    if not templates or not getattr(templates, "env", None):
        return

    # Idempotent: safe to call multiple times.
    templates.env.filters.setdefault("ddmmyyyy", format_date_ddmmyyyy)
    templates.env.filters.setdefault("ddmmyyyy_dt", format_datetime_ddmmyyyy_hhmm)
    templates.env.filters.setdefault("unit_sup", format_unit_sup)
    templates.env.filters.setdefault("local_dt", local_dt)
