# ============================================================
# Auto-align and optimize stretch schedules
# ============================================================
from sqlalchemy.orm import Session

def align_and_optimize_stretch_schedules(
    db: Session,
    project_id: int,
    reference_stretch_id: int,
    allow_manual_override: bool = True
) -> None:
    """
    Auto-align and optimize all stretches' activity schedules based on reference stretch (usually Stretch 1).
    Scales activity durations by stretch length and aligns start/end dates.
    Skips stretches/activities with manual overrides if allow_manual_override is True.
    """
    from app.models.road_stretch import RoadStretch
    from app.models.stretch_activity import StretchActivity

    # Fetch all stretches for the project, ordered by sequence
    stretches = db.query(RoadStretch).filter(RoadStretch.project_id == project_id).order_by(RoadStretch.sequence_no).all()
    if not stretches or len(stretches) < 2:
        return  # Nothing to align

    # Find reference stretch and its activities
    ref_stretch = next((s for s in stretches if s.id == reference_stretch_id), None)
    if not ref_stretch:
        return
    ref_activities = db.query(StretchActivity).filter(StretchActivity.stretch_id == ref_stretch.id).order_by(StretchActivity.id).all()
    if not ref_activities:
        return

    ref_length = ref_stretch.length_m or 1

    # Prepare reference activity schedule template
    ref_activity_templates = []
    for act in ref_activities:
        if not act.planned_start_date or not act.planned_end_date:
            continue
        duration_days = (act.planned_end_date - act.planned_start_date).days or 1
        ref_activity_templates.append({
            'project_activity_id': act.project_activity_id,
            'order': act.id,  # Use id order for now
            'duration_days': duration_days,
            'planned_start_offset': 0,  # Will be calculated below
        })

    # Calculate offsets for sequential activities in reference stretch
    running_offset = 0
    for template in ref_activity_templates:
        template['planned_start_offset'] = running_offset
        running_offset += template['duration_days']

    # Align all other stretches
    for stretch in stretches:
        if stretch.id == reference_stretch_id:
            continue  # Skip reference
        scale = (stretch.length_m or 1) / ref_length
        stretch_start = stretch.planned_start_date or stretch.start_date or ref_stretch.planned_start_date
        if not stretch_start:
            continue  # Cannot align without a start date

        for template in ref_activity_templates:
            # Find or create StretchActivity for this stretch and project_activity
            sa = db.query(StretchActivity).filter(
                StretchActivity.stretch_id == stretch.id,
                StretchActivity.project_activity_id == template['project_activity_id']
            ).first()
            if not sa:
                # Optionally, create if missing (depends on business logic)
                continue

            # If manual override is allowed and this activity has manual dates, skip
            if allow_manual_override and sa.planned_start_date and sa.planned_end_date:
                continue

            scaled_duration = max(1, int(round(template['duration_days'] * scale)))
            planned_start = stretch_start + timedelta(days=template['planned_start_offset'])
            planned_end = planned_start + timedelta(days=scaled_duration)

            sa.planned_start_date = planned_start
            sa.planned_end_date = planned_end
            sa.planned_duration_hours = scaled_duration * 8.0  # Assuming 8 hours/day
            db.add(sa)

    db.commit()
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
