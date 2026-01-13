from typing import Dict, List
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.activity_progress import ActivityProgress
from app.models.project_activity import ProjectActivity
from app.models.daily_entry import DailyEntry
from app.models.activity import Activity
from app.models.activity_material import ActivityMaterial
from app.utils.activity_units import convert_hours_to_days, normalize_hours_per_day
from app.services.material_progress_analytics import get_material_progress_analytics


def get_project_dashboard_analytics(db: Session, project_id: int, time_unit: str | None = None) -> Dict:
    """
    Aggregate project-level KPIs (TRUTH-BASED + HYBRID CRITICAL PATH):
    - Activity status counts
    - Quantity-weighted overall progress %
    - Material health summary
    - Risk flags (delays & over-consumption)
    - Critical path (hybrid)
    - Delay heatmap
    """

    today = date.today()

    # ------------------ Fetch planned activities ------------------
    planned_activities: List[ProjectActivity] = (
        db.query(ProjectActivity)
        .filter(ProjectActivity.project_id == project_id)
        .all()
    )

    total_activities = len(planned_activities)

    status_counts = {
        "not_started": 0,
        "in_progress": 0,
        "completed": 0,
        "delayed": 0,
    }

    delayed_activities: List[int] = []
    over_consumption_activities: List[int] = []

    # 🔥 NEW
    critical_activities: List[int] = []
    delay_heatmap: Dict[int, str] = {}

    # ------------------ Quantity-weighted progress ------------------
    total_planned_qty = sum(pa.planned_quantity for pa in planned_activities)

    total_executed_qty = (
        db.query(func.sum(DailyEntry.quantity_done))
        .filter(DailyEntry.project_id == project_id)
        .scalar()
        or 0.0
    )

    overall_progress_percent = (
        round((total_executed_qty / total_planned_qty) * 100, 2)
        if total_planned_qty > 0 else 0.0
    )

    # ------------------ Time-weighted KPIs (base = hours) ------------------
    activity_ids = sorted({int(pa.activity_id) for pa in planned_activities})

    # ------------------ Material risk KPI ------------------
    if activity_ids:
        risky_activity_ids = (
            db.query(ActivityMaterial.activity_id)
            .filter(ActivityMaterial.activity_id.in_(activity_ids), ActivityMaterial.is_material_risk == True)  # noqa: E712
            .distinct()
            .all()
        )
        material_risk_count = len(risky_activity_ids)
    else:
        material_risk_count = 0

    if not activity_ids:
        act_rows = []
    else:
        act_q = db.query(Activity).filter(Activity.project_id == project_id, Activity.id.in_(activity_ids))
        act_rows = act_q.all()
    act_by_id = {int(a.id): a for a in act_rows}

    total_planned_hours = sum(float(getattr(a, "planned_quantity_hours", 0.0) or 0.0) for a in act_rows)
    if not activity_ids:
        total_executed_hours = 0.0
    else:
        total_executed_hours = (
            db.query(func.sum(DailyEntry.quantity_done_hours))
            .filter(DailyEntry.project_id == project_id, DailyEntry.activity_id.in_(activity_ids))
            .scalar()
            or 0.0
        )

    overall_time_progress_percent = (
        round((total_executed_hours / total_planned_hours) * 100, 2)
        if total_planned_hours > 0 else 0.0
    )

    # For days display, respect per-activity hours_per_day by summing per activity.
    exec_hours_q = db.query(DailyEntry.activity_id, func.sum(DailyEntry.quantity_done_hours)).filter(
        DailyEntry.project_id == project_id
    )
    if activity_ids:
        exec_hours_q = exec_hours_q.filter(DailyEntry.activity_id.in_(activity_ids))
    exec_hours_by_activity_rows = exec_hours_q.group_by(DailyEntry.activity_id).all()
    exec_hours_by_activity = {int(aid): float(total or 0.0) for (aid, total) in exec_hours_by_activity_rows}

    total_planned_days = 0.0
    total_executed_days = 0.0
    for aid in activity_ids:
        act = act_by_id.get(aid)
        if not act:
            continue
        hpd = normalize_hours_per_day(getattr(act, "hours_per_day", None), default=8.0)
        ph = float(getattr(act, "planned_quantity_hours", 0.0) or 0.0)
        eh = float(exec_hours_by_activity.get(aid, 0.0) or 0.0)
        total_planned_days += convert_hours_to_days(ph, hpd)
        total_executed_days += convert_hours_to_days(eh, hpd)

    # Return a convenient display block based on query param
    tu = (time_unit or "hours").strip().lower()
    if tu not in {"hours", "days"}:
        tu = "hours"
    if tu == "days":
        time_display = {
            "unit": "days",
            "planned": round(total_planned_days, 3),
            "executed": round(total_executed_days, 3),
        }
    else:
        time_display = {
            "unit": "hours",
            "planned": round(float(total_planned_hours or 0.0), 3),
            "executed": round(float(total_executed_hours or 0.0), 3),
        }

    # ------------------ Activity evaluation ------------------
    for pa in planned_activities:

        ap = (
            db.query(ActivityProgress)
            .filter(
                ActivityProgress.project_id == project_id,
                ActivityProgress.activity_id == pa.activity_id
            )
            .first()
        )

        # ---------- Status counters ----------
        if not ap or ap.progress_percent == 0:
            status_counts["not_started"] += 1
            delay_heatmap[pa.activity_id] = "ON_TRACK"
            continue

        if ap.status == "IN_PROGRESS":
            status_counts["in_progress"] += 1
        elif ap.status == "COMPLETED":
            status_counts["completed"] += 1
        elif ap.status == "DELAYED":
            status_counts["delayed"] += 1
            delayed_activities.append(pa.activity_id)

        # ---------- Delay heatmap ----------
        if ap.status == "DELAYED":
            delay_heatmap[pa.activity_id] = "DELAYED"
        elif today >= ap.planned_end:
            delay_heatmap[pa.activity_id] = "AT_RISK"
        else:
            delay_heatmap[pa.activity_id] = "ON_TRACK"

        # ---------- Hybrid critical path ----------
        qty_weight = (
            pa.planned_quantity / total_planned_qty
            if total_planned_qty > 0 else 0
        )

        if (
            ap.status == "DELAYED"
            or (
                ap.progress_percent < 60
                and qty_weight >= 0.15
            )
        ):
            critical_activities.append(pa.activity_id)

    # ------------------ Material health summary ------------------
    material_health = {
        "ok": 0,
        "warning": 0,
        "over_consumption": 0,
    }

    for pa in planned_activities:
        try:
            analytics = get_material_progress_analytics(
                db=db,
                project_id=project_id,
                activity_id=pa.activity_id
            )

            for m in analytics.get("materials", []):
                status = m.get("status")
                if status == "OK":
                    material_health["ok"] += 1
                elif status == "WARNING":
                    material_health["warning"] += 1
                elif status == "OVER_CONSUMPTION":
                    material_health["over_consumption"] += 1
                    over_consumption_activities.append(pa.activity_id)

        except ValueError:
            continue

    # ------------------ FINAL RESPONSE ------------------
    return {
        "project_id": project_id,

        # ✅ EXISTING (UNCHANGED)
        "activities": {
            "total": total_activities,
            **status_counts
        },

        "overall_progress_percent": overall_progress_percent,

        "material_risk_activities": material_risk_count,

        # Time-based summary (additive; does not break legacy clients)
        "time": {
            "overall_progress_percent": overall_time_progress_percent,
            "planned_hours": round(float(total_planned_hours or 0.0), 3),
            "executed_hours": round(float(total_executed_hours or 0.0), 3),
            "planned_days": round(float(total_planned_days or 0.0), 3),
            "executed_days": round(float(total_executed_days or 0.0), 3),
            "display": time_display,
        },

        "material_health": material_health,

        "risk_flags": {
            "delayed_activities": list(set(delayed_activities)),
            "over_consumption_activities": list(set(over_consumption_activities)),
        },

        # 🔥 NEW (SAFE ADDITIONS)
        "critical_path": {
            "critical_activities": list(set(critical_activities)),
            "count": len(set(critical_activities)),
        },

        "delay_heatmap": delay_heatmap,
    }
