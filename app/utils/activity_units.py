from __future__ import annotations

"""Activity time unit conversion.

InfraCore historically tracks *activity quantity* in arbitrary physical units (m3/sqm/km/etc).
This module introduces a separate, optional *time-based* tracking system for activities.

Core rules (time tracking only):
- Base unit: hours (persisted)
- Display unit: hours or days (user preference)
- 1 day = hours_per_day (configurable per-activity; default 8)

IMPORTANT:
- Do not do conversion math directly in templates.
- Do not hardcode 8 in business logic; call these helpers.
"""

from typing import Literal

ActivityDisplayUnit = Literal["hours", "days"]


def normalize_display_unit(unit: str | None) -> ActivityDisplayUnit:
    u = (unit or "").strip().lower()
    if u in {"day", "days", "d"}:
        return "days"
    return "hours"


def normalize_hours_per_day(hours_per_day: float | None, default: float = 8.0) -> float:
    try:
        hpd = float(hours_per_day) if hours_per_day is not None else float(default)
    except Exception:
        hpd = float(default)
    # Guard against division by 0 / negative configs.
    if hpd <= 0:
        hpd = float(default)
    return hpd


def convert_days_to_hours(days: float, hours_per_day: float | None = None) -> float:
    hpd = normalize_hours_per_day(hours_per_day)
    return float(days or 0) * hpd


def convert_hours_to_days(hours: float, hours_per_day: float | None = None) -> float:
    hpd = normalize_hours_per_day(hours_per_day)
    return float(hours or 0) / hpd


def hours_to_display(hours: float, display_unit: str | None, hours_per_day: float | None = None) -> float:
    unit = normalize_display_unit(display_unit)
    if unit == "days":
        return convert_hours_to_days(hours, hours_per_day)
    return float(hours or 0)


def display_to_hours(value: float, display_unit: str | None, hours_per_day: float | None = None) -> float:
    unit = normalize_display_unit(display_unit)
    if unit == "days":
        return convert_days_to_hours(value, hours_per_day)
    return float(value or 0)


def unit_label(unit: str | None) -> str:
    """Short unit label for UI (hrs/days)."""
    return "days" if normalize_display_unit(unit) == "days" else "hrs"
