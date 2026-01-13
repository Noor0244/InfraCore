from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class DeliveryCheck:
    expected_delivery_date: date | None
    is_risk: bool
    days_late: int
    status: str  # AVAILABLE | PENDING | LATE | UNKNOWN


def normalize_lead_time_days(value: int | float | str | None, default: int = 0) -> int:
    try:
        v = int(float(value))
    except Exception:
        v = default
    if v < 0:
        v = 0
    return v


def compute_expected_delivery_date(order_date: date | None, lead_time_days: int | None) -> date | None:
    if not order_date:
        return None
    ltd = normalize_lead_time_days(lead_time_days, default=0)
    return order_date + timedelta(days=ltd)


def resolve_effective_lead_time_days(
    *,
    lead_time_days_override: int | None,
    vendor_lead_time_days: int | None,
    material_default_lead_time_days: int | None,
    material_legacy_lead_time_days: int | None,
) -> int:
    if lead_time_days_override is not None:
        return normalize_lead_time_days(lead_time_days_override, default=0)

    if vendor_lead_time_days is not None:
        return normalize_lead_time_days(vendor_lead_time_days, default=0)

    if material_default_lead_time_days is not None:
        return normalize_lead_time_days(material_default_lead_time_days, default=0)

    if material_legacy_lead_time_days is not None:
        return normalize_lead_time_days(material_legacy_lead_time_days, default=0)

    return 0


def evaluate_delivery_risk(
    *,
    activity_start_date: date | None,
    order_date: date | None,
    expected_delivery_date: date | None,
    today: date | None = None,
) -> DeliveryCheck:
    today = today or date.today()

    if not activity_start_date:
        return DeliveryCheck(expected_delivery_date=expected_delivery_date, is_risk=False, days_late=0, status="UNKNOWN")

    if not order_date or not expected_delivery_date:
        return DeliveryCheck(expected_delivery_date=expected_delivery_date, is_risk=False, days_late=0, status="UNKNOWN")

    if expected_delivery_date > activity_start_date:
        return DeliveryCheck(
            expected_delivery_date=expected_delivery_date,
            is_risk=True,
            days_late=max((expected_delivery_date - activity_start_date).days, 0),
            status="LATE",
        )

    # Not late vs start date
    if expected_delivery_date <= today:
        return DeliveryCheck(expected_delivery_date=expected_delivery_date, is_risk=False, days_late=0, status="AVAILABLE")

    return DeliveryCheck(expected_delivery_date=expected_delivery_date, is_risk=False, days_late=0, status="PENDING")


def compute_reorder_suggestion(
    *,
    available_qty: float | int | None,
    required_qty: float | int | None,
    unit_label: str | None,
) -> str | None:
    try:
        available = float(available_qty or 0.0)
    except Exception:
        available = 0.0
    try:
        required = float(required_qty or 0.0)
    except Exception:
        required = 0.0

    if required <= 0:
        return None

    if available + 1e-9 >= required:
        return None

    shortage = max(required - available, 0.0)
    unit = (unit_label or "").strip()

    # Keep copy short and actionable.
    if unit:
        return f"You have only {available:g} {unit}. Required: {required:g}. Order at least {shortage:g} more."
    return f"You have only {available:g}. Required: {required:g}. Order at least {shortage:g} more."