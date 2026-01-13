from __future__ import annotations

from fastapi.templating import Jinja2Templates

from app.utils.dates import format_date_ddmmyyyy, format_datetime_ddmmyyyy_hhmm


def register_template_filters(templates: Jinja2Templates) -> None:
    """Register shared Jinja filters on a templates instance."""

    if not templates or not getattr(templates, "env", None):
        return

    # Idempotent: safe to call multiple times.
    templates.env.filters.setdefault("ddmmyyyy", format_date_ddmmyyyy)
    templates.env.filters.setdefault("ddmmyyyy_dt", format_datetime_ddmmyyyy_hhmm)
