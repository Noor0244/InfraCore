from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.activity_material import ActivityMaterial
from app.models.material import Material
from app.models.material_stock import MaterialStock
from app.models.material_vendor import MaterialVendor
from app.models.project_activity import ProjectActivity
from app.models.road_stretch import RoadStretch
from app.models.stretch_activity import StretchActivity
from app.utils.material_lead_time import resolve_effective_lead_time_days


@dataclass(frozen=True)
class StretchDashboardConfig:
    lookahead_days: int = 30
    due_soon_days: int = 7
    max_rows: int = 50


def _pct(n: float | None) -> int:
    try:
        return int(round(float(n or 0.0)))
    except Exception:
        return 0


def _planned_progress(today: date, start: date | None, end: date | None) -> int | None:
    if not start or not end:
        return None
    if end <= start:
        return 100 if today >= end else 0
    if today <= start:
        return 0
    if today >= end:
        return 100
    total = (end - start).days
    done = (today - start).days
    if total <= 0:
        return 0
    return int(round(100.0 * (done / total)))


def compute_stretch_intelligence(
    *,
    db: Session,
    project_id: int,
    today: date | None = None,
    cfg: StretchDashboardConfig | None = None,
    # optional filters
    stretch_id: int | None = None,
    status: str | None = None,
    activity_id: int | None = None,
    material_id: int | None = None,
) -> dict[str, object]:
    """Compute stretch-aware dashboard intelligence.

    This is designed to be a server-side, non-breaking extension of the existing dashboard.
    """

    cfg = cfg or StretchDashboardConfig()
    today = today or date.today()

    stretches_q = db.query(RoadStretch).filter(
        RoadStretch.project_id == int(project_id),
        RoadStretch.is_active == True,  # noqa: E712
    )
    if stretch_id:
        stretches_q = stretches_q.filter(RoadStretch.id == int(stretch_id))

    stretches = stretches_q.order_by(RoadStretch.sequence_no.asc()).all()
    if not stretches:
        return {
            "today": today,
            "has_stretches": False,
            "stretches": [],
            "alerts": [],
            "filters": {
                "stretch_id": int(stretch_id) if stretch_id else None,
                "status": status or None,
                "activity_id": int(activity_id) if activity_id else None,
                "material_id": int(material_id) if material_id else None,
            },
            "cfg": {
                "lookahead_days": int(cfg.lookahead_days),
                "due_soon_days": int(cfg.due_soon_days),
                "max_rows": int(cfg.max_rows),
            },
        }

    stretch_ids = [int(s.id) for s in stretches]

    # Stocks (project)
    stock_rows = (
        db.query(MaterialStock)
        .filter(
            MaterialStock.project_id == int(project_id),
            MaterialStock.is_active == True,  # noqa: E712
        )
        .all()
    )
    stock_by_material_id = {int(s.material_id): float(s.quantity_available or 0.0) for s in stock_rows}

    # Stretch activities (with project_activity and activity)
    sa_rows = (
        db.query(StretchActivity, ProjectActivity, Activity)
        .join(RoadStretch, RoadStretch.id == StretchActivity.stretch_id)
        .join(ProjectActivity, ProjectActivity.id == StretchActivity.project_activity_id)
        .join(Activity, Activity.id == ProjectActivity.activity_id)
        .filter(
            RoadStretch.project_id == int(project_id),
            RoadStretch.id.in_(stretch_ids),
            RoadStretch.is_active == True,  # noqa: E712
            Activity.is_active == True,  # noqa: E712
        )
        .all()
    )

    sa_by_stretch_id: dict[int, list[tuple[StretchActivity, ProjectActivity, Activity]]] = {}
    for sa, pa, act in sa_rows:
        sa_by_stretch_id.setdefault(int(sa.stretch_id), []).append((sa, pa, act))

    # Activity -> materials mapping (project)
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

    # Allocation simulation across stretches (sequence order)
    remaining_stock = {int(mid): float(qty) for mid, qty in stock_by_material_id.items()}

    lookahead_end = today + timedelta(days=int(cfg.lookahead_days))

    alerts: list[dict[str, object]] = []
    stretch_cards: list[dict[str, object]] = []

    for s in stretches:
        sid = int(s.id)
        rows = sa_by_stretch_id.get(sid, [])

        # Planned window (prefer stretch planned dates, fallback to project activity dates)
        starts: list[date] = []
        ends: list[date] = []
        for sa, pa, _act in rows:
            if sa.planned_start_date:
                starts.append(sa.planned_start_date)
            elif pa.start_date:
                starts.append(pa.start_date)

            if sa.planned_end_date:
                ends.append(sa.planned_end_date)
            elif pa.end_date:
                ends.append(pa.end_date)

        planned_start = min(starts) if starts else None
        planned_end = max(ends) if ends else None

        # Actual progress = avg stretch activity progress
        progress_vals = [_pct(getattr(sa, "progress_percent", None)) for (sa, _pa, _act) in rows]
        actual = int(round(sum(progress_vals) / max(len(progress_vals), 1))) if progress_vals else 0

        planned = _planned_progress(today, planned_start, planned_end)

        # Critical activity (next unfinished by planned start)
        critical = None
        if rows:
            ordered = sorted(
                rows,
                key=lambda t: (
                    t[0].planned_start_date or t[1].start_date or date.max,
                    int(getattr(t[1], "id", 0) or 0),
                ),
            )
            for sa, pa, act in ordered:
                pct = _pct(getattr(sa, "progress_percent", None))
                if pct < 100:
                    critical = {
                        "activity_id": int(act.id),
                        "activity_code": str(getattr(act, "code", "") or ""),
                        "activity_name": str(getattr(act, "name", "") or ""),
                        "start_date": sa.planned_start_date or pa.start_date,
                        "end_date": sa.planned_end_date or pa.end_date,
                        "progress_percent": pct,
                    }
                    break

        # Status logic
        status_kind = "NOT_STARTED"
        if actual >= 100:
            status_kind = "COMPLETED"
        elif actual > 0:
            status_kind = "IN_PROGRESS"
        else:
            if planned_start and today >= planned_start:
                status_kind = "IN_PROGRESS"

        if planned is not None and status_kind != "COMPLETED":
            # if behind plan by any meaningful margin -> delayed
            if today >= (planned_start or today) and actual + 1 < planned:
                status_kind = "DELAYED"

        status_label = {
            "NOT_STARTED": "Not Started",
            "IN_PROGRESS": "In Progress",
            "COMPLETED": "Completed",
            "DELAYED": "Delayed",
        }.get(status_kind, status_kind)

        if status_kind == "DELAYED":
            alerts.append(
                {
                    "kind": "DELAY",
                    "severity": "warning",
                    "title": f"Stretch {s.stretch_code} is DELAYED",
                    "detail": f"Actual {actual}% vs Planned {planned if planned is not None else '—'}%",
                    "stretch_id": sid,
                    "stretch_code": str(s.stretch_code),
                }
            )

        # Material forecast (stretch-level, lookahead)
        # We estimate required remaining for activities starting within lookahead window.
        required_by_material: dict[int, float] = {}
        earliest_need_date_by_material: dict[int, date] = {}

        for sa, pa, act in rows:
            # optional activity filter
            if activity_id and int(act.id) != int(activity_id):
                continue

            start = sa.planned_start_date or pa.start_date
            if not isinstance(start, date):
                continue

            if start > lookahead_end:
                continue

            pct = _pct(getattr(sa, "progress_percent", None))
            if pct >= 100:
                continue

            # Prefer stretch planned quantity if set, else fall back to project planned qty.
            planned_qty = getattr(sa, "planned_quantity", None)
            if planned_qty is None:
                planned_qty = getattr(pa, "planned_quantity", 0.0) or 0.0
            planned_qty_f = float(planned_qty or 0.0)

            remaining_factor = max(0.0, 1.0 - (float(pct) / 100.0))
            remaining_qty = planned_qty_f * remaining_factor

            mats = mappings_by_activity_id.get(int(act.id), [])
            for am, mat, vendor in mats:
                mid = int(mat.id)
                if material_id and mid != int(material_id):
                    continue

                consumption_rate = float(getattr(am, "consumption_rate", 0.0) or 0.0)
                req = max(0.0, remaining_qty * consumption_rate)
                if req <= 0:
                    continue

                required_by_material[mid] = float(required_by_material.get(mid, 0.0)) + float(req)
                if mid not in earliest_need_date_by_material or start < earliest_need_date_by_material[mid]:
                    earliest_need_date_by_material[mid] = start

        # Simulate allocation by stretch sequence
        shortages: list[dict[str, object]] = []
        due_soon: list[dict[str, object]] = []

        for mid, req in required_by_material.items():
            available_before = float(remaining_stock.get(mid, 0.0) or 0.0)
            allocated = min(available_before, float(req))
            remaining_stock[mid] = available_before - allocated
            shortage_qty = max(0.0, float(req) - allocated)

            need_date = earliest_need_date_by_material.get(mid)
            if not need_date:
                continue

            # lead time via vendor/default, same as project alert logic
            vendor_lead = None
            effective_lead = 0
            try:
                # find any mapping row for this material to get vendor + override (best effort)
                # note: this is approximate; if multiple activities map to same material, we pick the max lead time.
                effective_lead_candidates: list[int] = []
                for sa, pa, act in rows:
                    mats = mappings_by_activity_id.get(int(act.id), [])
                    for am, mat, vendor in mats:
                        if int(mat.id) != int(mid):
                            continue
                        vendor_lead = int(getattr(vendor, "lead_time_days", 0) or 0) if vendor else None
                        eff = resolve_effective_lead_time_days(
                            lead_time_days_override=getattr(am, "lead_time_days_override", None),
                            vendor_lead_time_days=vendor_lead,
                            material_default_lead_time_days=getattr(mat, "default_lead_time_days", None),
                            material_legacy_lead_time_days=getattr(mat, "lead_time_days", None),
                        )
                        effective_lead_candidates.append(int(eff or 0))
                effective_lead = max(effective_lead_candidates) if effective_lead_candidates else 0
            except Exception:
                effective_lead = 0

            order_by = need_date - timedelta(days=int(effective_lead))
            days_to_need = (need_date - today).days

            if shortage_qty > 0:
                shortages.append(
                    {
                        "material_id": int(mid),
                        "required_qty": float(req),
                        "shortage_qty": float(shortage_qty),
                        "need_date": need_date,
                        "order_by": order_by,
                        "lead_time_days": int(effective_lead),
                    }
                )

                if days_to_need >= 0:
                    alerts.append(
                        {
                            "kind": "SHORTAGE",
                            "severity": "warning",
                            "title": f"{int(shortage_qty)} shortage for {s.stretch_code}",
                            "detail": f"Material #{mid} required by {need_date.isoformat()} (order by {order_by.isoformat()})",
                            "stretch_id": sid,
                            "stretch_code": str(s.stretch_code),
                            "material_id": int(mid),
                        }
                    )

            # due soon alerts even if no shortage (ordering urgency)
            if order_by <= (today + timedelta(days=int(cfg.due_soon_days))):
                due_soon.append(
                    {
                        "material_id": int(mid),
                        "required_qty": float(req),
                        "need_date": need_date,
                        "order_by": order_by,
                        "lead_time_days": int(effective_lead),
                    }
                )

        # Material risk summary
        material_risk_kind = "OK"
        material_risk_label = "OK"
        if shortages:
            material_risk_kind = "SHORTAGE"
            material_risk_label = "Shortage"
        elif due_soon:
            material_risk_kind = "DUE_SOON"
            material_risk_label = "Due Soon"

        if material_risk_kind == "SHORTAGE":
            alerts.append(
                {
                    "kind": "MATERIAL_RISK",
                    "severity": "warning",
                    "title": f"Material shortage risk in {s.stretch_code}",
                    "detail": f"{len(shortages)} material(s) short",
                    "stretch_id": sid,
                    "stretch_code": str(s.stretch_code),
                }
            )

        if status_kind == "COMPLETED":
            alerts.append(
                {
                    "kind": "COMPLETED",
                    "severity": "info",
                    "title": f"Stretch {s.stretch_code} completed",
                    "detail": "Release resources and move forward",
                    "stretch_id": sid,
                    "stretch_code": str(s.stretch_code),
                }
            )

        stretch_cards.append(
            {
                "stretch_id": sid,
                "stretch_code": str(s.stretch_code),
                "stretch_name": str(s.stretch_name),
                "chainage": f"{s.start_chainage} – {s.end_chainage}",
                "length_m": int(s.length_m or 0),
                "planned_start": planned_start,
                "planned_end": planned_end,
                "planned_progress": planned,
                "actual_progress": int(actual),
                "status_kind": status_kind,
                "status_label": status_label,
                "critical_activity": critical,
                "material_risk_kind": material_risk_kind,
                "material_risk_label": material_risk_label,
            }
        )

    # Optional status filter (after computation)
    if status:
        want = str(status or "").strip().upper()
        stretch_cards = [c for c in stretch_cards if str(c.get("status_kind") or "").upper() == want]

    # cap alerts
    alerts = alerts[: int(cfg.max_rows)]

    total_length_m = sum(int(s.get("length_m") or 0) for s in stretch_cards) or 0

    return {
        "today": today,
        "has_stretches": True,
        "total_length_m": int(total_length_m),
        "stretches": stretch_cards,
        "alerts": alerts,
        "filters": {
            "stretch_id": int(stretch_id) if stretch_id else None,
            "status": status or None,
            "activity_id": int(activity_id) if activity_id else None,
            "material_id": int(material_id) if material_id else None,
        },
        "cfg": {
            "lookahead_days": int(cfg.lookahead_days),
            "due_soon_days": int(cfg.due_soon_days),
            "max_rows": int(cfg.max_rows),
        },
    }
