from datetime import date
from typing import List, Dict
from sqlalchemy.orm import Session

from app.models.activity_progress import ActivityProgress
from app.models.activity_material import ActivityMaterial
from app.utils.material_lead_time import evaluate_delivery_risk, compute_expected_delivery_date


# ============================================================
# Schedule & Progress Service
# ============================================================

def set_planned_schedule(
    db: Session,
    project_id: int,
    activity_id: int,
    planned_start: date,
    planned_end: date
) -> ActivityProgress:
    """
    Create or update planned schedule for a project activity
    """

    if planned_end < planned_start:
        raise ValueError("Planned end date cannot be before planned start date")

    record = (
        db.query(ActivityProgress)
        .filter(
            ActivityProgress.project_id == project_id,
            ActivityProgress.activity_id == activity_id
        )
        .first()
    )

    if record:
        record.planned_start = planned_start
        record.planned_end = planned_end
    else:
        record = ActivityProgress(
            project_id=project_id,
            activity_id=activity_id,
            planned_start=planned_start,
            planned_end=planned_end,
            progress_percent=0,
            status="NOT_STARTED"
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


# ------------------------------------------------------------

def update_progress(
    db: Session,
    project_id: int,
    activity_id: int,
    progress_percent: int
) -> ActivityProgress:
    """
    Update progress percentage for a project activity
    """

    if progress_percent < 0 or progress_percent > 100:
        raise ValueError("Progress percent must be between 0 and 100")

    record = (
        db.query(ActivityProgress)
        .filter(
            ActivityProgress.project_id == project_id,
            ActivityProgress.activity_id == activity_id
        )
        .first()
    )

    if not record:
        raise ValueError("Planned schedule not found for this activity")

    today = date.today()
    record.progress_percent = progress_percent

    # Auto actual start
    if progress_percent > 0 and record.actual_start is None:
        record.actual_start = today

    # Auto actual end
    if progress_percent == 100:
        record.actual_end = today
        record.status = "COMPLETED"
    else:
        record.status = _calculate_status(record, today)

    db.commit()
    db.refresh(record)
    return record


# ------------------------------------------------------------

def get_project_schedule(
    db: Session,
    project_id: int
) -> List[Dict]:
    """
    Get full schedule & delay analytics for a project
    """

    today = date.today()

    records = (
        db.query(ActivityProgress)
        .filter(ActivityProgress.project_id == project_id)
        .all()
    )

    activity_ids = [int(r.activity_id) for r in records]
    am_rows = []
    if activity_ids:
        am_rows = (
            db.query(ActivityMaterial)
            .filter(ActivityMaterial.activity_id.in_(activity_ids))
            .all()
        )

    am_by_activity: dict[int, list[ActivityMaterial]] = {}
    for am in am_rows:
        am_by_activity.setdefault(int(am.activity_id), []).append(am)

    response: List[Dict] = []

    for r in records:
        planned_duration = (r.planned_end - r.planned_start).days

        if r.actual_start:
            actual_end = r.actual_end or today
            actual_duration = (actual_end - r.actual_start).days
        else:
            actual_duration = 0

        delay_days = actual_duration - planned_duration if r.actual_start else 0
        status = _calculate_status(r, today)

        # ---------------- Material availability indicator ----------------
        mats = am_by_activity.get(int(r.activity_id), [])
        worst = "UNKNOWN"
        any_risk = False
        max_days_late = 0
        for am in mats:
            expected = getattr(am, "expected_delivery_date", None)
            if expected is None:
                expected = compute_expected_delivery_date(getattr(am, "order_date", None), getattr(am, "lead_time_days", None))
            check = evaluate_delivery_risk(
                activity_start_date=r.planned_start,
                order_date=getattr(am, "order_date", None),
                expected_delivery_date=expected,
                today=today,
            )
            is_risk = bool(check.is_risk)
            if is_risk:
                any_risk = True
                max_days_late = max(max_days_late, int(check.days_late or 0))
                worst = "LATE"
                continue
            if worst != "LATE" and check.status == "PENDING":
                worst = "PENDING"
            if worst == "UNKNOWN" and check.status == "AVAILABLE":
                worst = "AVAILABLE"

        if worst == "LATE":
            icon = "🔴"
        elif worst == "PENDING":
            icon = "🟡"
        elif worst == "AVAILABLE":
            icon = "🟢"
        else:
            icon = "—"

        response.append({
            "project_id": r.project_id,
            "activity_id": r.activity_id,
            "planned_start": r.planned_start,
            "planned_end": r.planned_end,
            "actual_start": r.actual_start,
            "actual_end": r.actual_end,
            "progress_percent": r.progress_percent,
            "planned_duration_days": planned_duration,
            "actual_duration_days": actual_duration,
            "delay_days": delay_days,
            "status": status,

            # Material availability planning
            "material_status": worst,
            "material_is_risk": any_risk,
            "material_days_late": max_days_late,
            "material_icon": icon,
        })

    return response


# ============================================================
# INTERNAL UTIL
# ============================================================

def _calculate_status(record: ActivityProgress, today: date) -> str:
    """
    Derive status based on dates & progress
    """

    if record.progress_percent == 0:
        return "NOT_STARTED"

    if record.progress_percent == 100:
        if record.actual_end and record.actual_end > record.planned_end:
            return "DELAYED"
        return "COMPLETED"

    if today > record.planned_end:
        return "DELAYED"

    return "IN_PROGRESS"
