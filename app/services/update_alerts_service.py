from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.activity import Activity
from app.models.activity_material import ActivityMaterial
from app.models.activity_progress import ActivityProgress
from app.models.material import Material
from app.models.material_stock import MaterialStock
from app.models.material_usage_daily import MaterialUsageDaily
from app.models.material_vendor import MaterialVendor
from app.models.project_material_vendor import ProjectMaterialVendor
from app.models.project_activity import ProjectActivity
from app.utils.material_lead_time import resolve_effective_lead_time_days


@dataclass(frozen=True)
class AlertConfig:
    lookahead_days: int = 30
    due_soon_days: int = 7
    max_rows: int = 30


def _status_for_order(to_order: float, order_by: date | None, today: date, due_soon_days: int) -> tuple[str, str]:
    if to_order <= 0:
        return ("OK", "Stock OK")

    if not order_by:
        return ("UNKNOWN", "No start date")

    if order_by < today:
        days = (today - order_by).days
        return ("LATE", f"Order Late by {days}d")

    if order_by == today:
        return ("DUE", "Order Today")

    if order_by <= (today + timedelta(days=due_soon_days)):
        days = (order_by - today).days
        return ("DUE_SOON", f"Order Due in {days}d")

    return ("UPCOMING", f"Order by {order_by.isoformat()}")


def _explain_row(today: date, start: date | None, lead_time_days: int, order_by: date | None) -> str:
    parts: list[str] = []
    if start:
        parts.append(f"Activity starts: {start.isoformat()}")
    parts.append(f"Supply lead time: {int(lead_time_days)}d")
    if order_by:
        parts.append(f"Order-by date: {order_by.isoformat()}")
    parts.append(f"Today: {today.isoformat()}")
    return " | ".join(parts)


def compute_project_update_alerts(
    db: Session,
    project_id: int,
    today: date | None = None,
    cfg: AlertConfig | None = None,
) -> dict[str, object]:
    """Compute dashboard alerts for upcoming activities and material ordering.

    Uses:
    - ProjectActivity for planned quantity + dates
    - ActivityProgress for progress_percent (if exists)
    - ActivityMaterial + vendor/default lead time for order-by date
    - MaterialStock for available quantities
    """

    cfg = cfg or AlertConfig()
    today = today or date.today()

    usage_window_days = 14

    # Planned schedule/qty
    pa_rows = (
        db.query(ProjectActivity)
        .filter(ProjectActivity.project_id == int(project_id))
        .all()
    )
    pa_by_activity_id = {int(pa.activity_id): pa for pa in pa_rows}

    # Progress
    progress_rows = (
        db.query(ActivityProgress)
        .filter(ActivityProgress.project_id == int(project_id))
        .all()
    )
    progress_by_activity_id = {int(p.activity_id): int(p.progress_percent or 0) for p in progress_rows}

    # Activities (project-scoped)
    activities = (
        db.query(Activity)
        .filter(
            Activity.project_id == int(project_id),
            Activity.is_active == True,  # noqa: E712
        )
        .order_by(Activity.id.asc())
        .all()
    )

    # Stocks
    stock_rows = (
        db.query(MaterialStock)
        .filter(
            MaterialStock.project_id == int(project_id),
            MaterialStock.is_active == True,  # noqa: E712
        )
        .all()
    )
    stock_by_material_id = {int(s.material_id): float(s.quantity_available or 0.0) for s in stock_rows}

    # Recent daily usage (project-level, per material)
    usage_start = today - timedelta(days=usage_window_days)
    usage_rows = (
        db.query(
            MaterialUsageDaily.material_id,
            func.coalesce(func.sum(MaterialUsageDaily.quantity_used), 0.0),
        )
        .filter(
            MaterialUsageDaily.project_id == int(project_id),
            MaterialUsageDaily.usage_date >= usage_start,
        )
        .group_by(MaterialUsageDaily.material_id)
        .all()
    )
    usage_by_material_id = {int(mid): float(total or 0.0) for (mid, total) in usage_rows}

    # Project-scoped vendors per material (lead time overrides + price)
    vendor_rows = (
        db.query(ProjectMaterialVendor, MaterialVendor)
        .join(MaterialVendor, MaterialVendor.id == ProjectMaterialVendor.vendor_id)
        .filter(
            ProjectMaterialVendor.project_id == int(project_id),
            MaterialVendor.is_active == True,  # noqa: E712
        )
        .all()
    )
    vendors_by_material_id: dict[int, list[dict[str, object]]] = {}
    for pmv, vendor in vendor_rows:
        mid = int(pmv.material_id)
        eff_lead = pmv.lead_time_days if pmv.lead_time_days is not None else vendor.lead_time_days
        vendors_by_material_id.setdefault(mid, []).append(
            {
                "vendor_id": int(vendor.id),
                "vendor_name": str(vendor.vendor_name or ""),
                "lead_time_days": int(eff_lead or 0),
                "unit_price": float(vendor.unit_price) if vendor.unit_price is not None else None,
                "vendor_priority": str(vendor.vendor_priority or ""),
            }
        )

    # Material links for this project (via Activity → project_id)
    mapping_rows = (
        db.query(ActivityMaterial, Activity, Material, MaterialVendor)
        .join(Activity, Activity.id == ActivityMaterial.activity_id)
        .join(Material, Material.id == ActivityMaterial.material_id)
        .outerjoin(MaterialVendor, MaterialVendor.id == ActivityMaterial.vendor_id)
        .filter(
            Activity.project_id == int(project_id),
            Activity.is_active == True,  # noqa: E712
        )
        .all()
    )

    mappings_by_activity_id: dict[int, list[tuple[ActivityMaterial, Material, MaterialVendor | None]]] = {}
    for am, act, mat, vendor in mapping_rows:
        mappings_by_activity_id.setdefault(int(act.id), []).append((am, mat, vendor))

    # Upcoming / in-progress activities
    upcoming_activities: list[dict[str, object]] = []
    for a in activities:
        aid = int(a.id)
        pa = pa_by_activity_id.get(aid)
        if not pa or not getattr(pa, "start_date", None):
            continue

        progress = int(progress_by_activity_id.get(aid, 0) or 0)
        if progress >= 100:
            continue

        start = getattr(pa, "start_date", None)
        # include in-progress even if start already passed
        in_lookahead = start <= (today + timedelta(days=int(cfg.lookahead_days)))
        if not in_lookahead and start >= today:
            continue

        upcoming_activities.append(
            {
                "activity_id": aid,
                "activity_code": str(getattr(a, "code", "") or ""),
                "activity_name": str(getattr(a, "name", "") or ""),
                "start_date": start,
                "end_date": getattr(pa, "end_date", None),
                "progress_percent": progress,
            }
        )

    upcoming_activities.sort(key=lambda r: (r.get("start_date") or today, int(r.get("activity_id") or 0)))

    next_activity = upcoming_activities[0] if upcoming_activities else None

    # Material order suggestions
    order_rows: list[dict[str, object]] = []

    for act_row in upcoming_activities:
        aid = int(act_row["activity_id"])
        pa = pa_by_activity_id.get(aid)
        if not pa:
            continue

        planned_qty = float(getattr(pa, "planned_quantity", 0.0) or 0.0)
        progress = float(act_row.get("progress_percent") or 0.0)
        remaining_factor = max(0.0, 1.0 - (progress / 100.0))
        remaining_qty = planned_qty * remaining_factor

        start = act_row.get("start_date")
        if not isinstance(start, date):
            continue

        mats = mappings_by_activity_id.get(aid, [])
        for am, mat, vendor in mats:
            consumption_rate = float(getattr(am, "consumption_rate", 0.0) or 0.0)
            required_remaining = max(0.0, remaining_qty * consumption_rate)

            mid = int(mat.id)
            available = float(stock_by_material_id.get(mid, 0.0) or 0.0)
            to_order = max(0.0, required_remaining - available)

            vendor_lead = int(getattr(vendor, "lead_time_days", 0) or 0) if vendor else None
            effective_lead = resolve_effective_lead_time_days(
                lead_time_days_override=getattr(am, "lead_time_days_override", None),
                vendor_lead_time_days=vendor_lead,
                material_default_lead_time_days=getattr(mat, "default_lead_time_days", None),
                material_legacy_lead_time_days=getattr(mat, "lead_time_days", None),
            )
            effective_lead_i = int(effective_lead or 0)
            order_by = start - timedelta(days=effective_lead_i)

            # Vendor recommendation
            vendor_options = list(vendors_by_material_id.get(mid, []))
            recommended_vendor = None
            if vendor is not None:
                recommended_vendor = {
                    "vendor_id": int(vendor.id),
                    "vendor_name": str(vendor.vendor_name or ""),
                    "lead_time_days": int(vendor_lead or 0),
                    "unit_price": float(vendor.unit_price) if vendor.unit_price is not None else None,
                    "vendor_priority": str(vendor.vendor_priority or ""),
                }
            elif vendor_options:
                vendor_options_sorted = sorted(
                    vendor_options,
                    key=lambda v: (
                        int(v.get("lead_time_days") or 0),
                        float(v.get("unit_price") or 1e18),
                        str(v.get("vendor_priority") or ""),
                    ),
                )
                recommended_vendor = vendor_options_sorted[0]

            avg_daily_usage = float(usage_by_material_id.get(mid, 0.0) or 0.0) / float(usage_window_days)
            stock_days = None
            if avg_daily_usage > 0:
                stock_days = float(available) / avg_daily_usage

            status_kind, status_label = _status_for_order(to_order, order_by, today, cfg.due_soon_days)
            explain = _explain_row(today=today, start=start, lead_time_days=effective_lead_i, order_by=order_by)

            order_rows.append(
                {
                    "status_kind": status_kind,
                    "status_label": status_label,
                    "order_by": order_by,
                    "lead_time_days": effective_lead_i,
                    "explain": explain,
                    "project_id": int(project_id),
                    "activity_id": aid,
                    "activity_code": str(act_row.get("activity_code") or ""),
                    "activity_name": str(act_row.get("activity_name") or ""),
                    "activity_start": start,
                    "material_id": mid,
                    "material_code": str(getattr(mat, "code", "") or ""),
                    "material_name": str(getattr(mat, "name", "") or ""),
                    "unit": str(getattr(mat, "unit", "") or ""),
                    "required_qty": round(required_remaining, 3),
                    "available_qty": round(available, 3),
                    "to_order_qty": round(to_order, 3),
                    "vendor_options": vendor_options,
                    "recommended_vendor": recommended_vendor,
                    "avg_daily_usage": round(avg_daily_usage, 3),
                    "stock_days": round(stock_days, 1) if stock_days is not None else None,
                }
            )

    # prioritize: LATE, DUE, DUE_SOON, UPCOMING, OK
    rank = {"LATE": 0, "DUE": 1, "DUE_SOON": 2, "UPCOMING": 3, "UNKNOWN": 4, "OK": 5}
    order_rows.sort(
        key=lambda r: (
            rank.get(str(r.get("status_kind")), 99),
            r.get("order_by") or (today + timedelta(days=9999)),
            -(float(r.get("to_order_qty") or 0.0)),
        )
    )

    # Procurement snapshot: compact summary for items needing action this week
    snapshot_window_days = 7
    window_end = today + timedelta(days=snapshot_window_days)
    snapshot_rank = {"LATE": 0, "DUE": 1, "DUE_SOON": 2, "UPCOMING": 3, "UNKNOWN": 4, "OK": 5}
    snapshot_by_material: dict[int, dict[str, object]] = {}

    for r in order_rows:
        to_order = float(r.get("to_order_qty") or 0.0)
        if to_order <= 0:
            continue
        kind = str(r.get("status_kind") or "")
        if kind not in {"LATE", "DUE", "DUE_SOON"}:
            continue
        ob = r.get("order_by")
        if isinstance(ob, date) and ob > window_end:
            continue

        mid = int(r.get("material_id") or 0)
        if mid <= 0:
            continue

        existing = snapshot_by_material.get(mid)
        if not existing:
            snapshot_by_material[mid] = {
                "material_id": mid,
                "material_code": str(r.get("material_code") or ""),
                "material_name": str(r.get("material_name") or ""),
                "unit": str(r.get("unit") or ""),
                "total_to_order_qty": float(to_order),
                "earliest_order_by": ob,
                "status_kind": kind,
                "status_label": str(r.get("status_label") or ""),
            }
        else:
            existing["total_to_order_qty"] = float(existing.get("total_to_order_qty") or 0.0) + float(to_order)
            # earliest order-by
            ex_ob = existing.get("earliest_order_by")
            if isinstance(ob, date) and (not isinstance(ex_ob, date) or ob < ex_ob):
                existing["earliest_order_by"] = ob
            # highest urgency
            if snapshot_rank.get(kind, 99) < snapshot_rank.get(str(existing.get("status_kind") or ""), 99):
                existing["status_kind"] = kind
                existing["status_label"] = str(r.get("status_label") or "")

    procurement_snapshot = list(snapshot_by_material.values())
    procurement_snapshot.sort(
        key=lambda x: (
            snapshot_rank.get(str(x.get("status_kind") or ""), 99),
            x.get("earliest_order_by") or (today + timedelta(days=9999)),
            -(float(x.get("total_to_order_qty") or 0.0)),
        )
    )
    procurement_snapshot = procurement_snapshot[: min(8, int(cfg.max_rows))]

    order_rows = order_rows[: int(cfg.max_rows)]

    warnings_count = sum(1 for r in order_rows if str(r.get("status_kind")) in {"LATE", "DUE", "DUE_SOON"} and float(r.get("to_order_qty") or 0) > 0)

    return {
        "today": today,
        "next_activity": next_activity,
        "upcoming_activities": upcoming_activities[:10],
        "material_orders": order_rows,
        "procurement_snapshot": procurement_snapshot,
        "warnings_count": int(warnings_count),
        "cfg": {
            "lookahead_days": int(cfg.lookahead_days),
            "due_soon_days": int(cfg.due_soon_days),
            "max_rows": int(cfg.max_rows),
        },
    }
