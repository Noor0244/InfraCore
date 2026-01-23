from datetime import timedelta
from sqlalchemy.orm import Session
from app.models.stretch import Stretch
from app.models.stretch_activity import StretchActivity

def auto_align_stretches(db: Session, project_id: int, reference_stretch_id: int):
    """
    Auto-align and optimize all stretches' activity schedules based on reference stretch (usually Stretch 1).
    Scales activity durations by stretch length and aligns start/end dates.
    Skips stretches/activities with manual overrides.
    """
    stretches = db.query(Stretch).filter(Stretch.project_id == project_id).order_by(Stretch.sequence_no).all()
    if not stretches or len(stretches) < 2:
        return
    ref_stretch = next((s for s in stretches if s.id == reference_stretch_id), None)
    if not ref_stretch:
        return
    ref_activities = db.query(StretchActivity).filter(StretchActivity.stretch_id == ref_stretch.id).order_by(StretchActivity.id).all()
    if not ref_activities:
        return
    ref_length = ref_stretch.length_m or 1
    ref_activity_templates = []
    for act in ref_activities:
        if not act.planned_start_date or not act.planned_end_date:
            continue
        duration_days = (act.planned_end_date - act.planned_start_date).days or 1
        ref_activity_templates.append({
            'name': act.name,
            'duration_days': duration_days,
            'planned_start_offset': 0,  # Will be calculated below
        })
    running_offset = 0
    for template in ref_activity_templates:
        template['planned_start_offset'] = running_offset
        running_offset += template['duration_days']
    for stretch in stretches:
        if stretch.id == reference_stretch_id or stretch.manual_override:
            continue
        scale = (stretch.length_m or 1) / ref_length
        stretch_start = stretch.planned_start_date or ref_stretch.planned_start_date
        if not stretch_start:
            continue
        for template in ref_activity_templates:
            sa = db.query(StretchActivity).filter(
                StretchActivity.stretch_id == stretch.id,
                StretchActivity.name == template['name']
            ).first()
            if not sa or sa.manual_override:
                continue
            scaled_duration = max(1, int(round(template['duration_days'] * scale)))
            planned_start = stretch_start + timedelta(days=template['planned_start_offset'])
            planned_end = planned_start + timedelta(days=scaled_duration)
            sa.planned_start_date = planned_start
            sa.planned_end_date = planned_end
            sa.planned_duration_days = scaled_duration
            db.add(sa)
    db.commit()
