from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.stretch import Stretch
from app.models.stretch_activity import StretchActivity
from app.services.stretch_scheduler_service import auto_align_stretches

router = APIRouter(prefix="/stretches", tags=["Stretches"])

@router.post("/auto-align/{project_id}/{reference_stretch_id}")
def auto_align_stretch_activities(project_id: int, reference_stretch_id: int, db: Session = Depends(get_db)):
    auto_align_stretches(db, project_id, reference_stretch_id)
    return {"status": "success", "message": "Stretches auto-aligned and optimized."}

@router.get("/project/{project_id}")
def get_stretches_for_project(project_id: int, db: Session = Depends(get_db)):
    stretches = db.query(Stretch).filter(Stretch.project_id == project_id).order_by(Stretch.sequence_no).all()
    result = []
    for s in stretches:
        activities = db.query(StretchActivity).filter(StretchActivity.stretch_id == s.id).all()
        result.append({
            "id": s.id,
            "sequence_no": s.sequence_no,
            "name": s.name,
            "code": s.code,
            "length_m": s.length_m,
            "planned_start_date": s.planned_start_date,
            "planned_end_date": s.planned_end_date,
            "manual_override": s.manual_override,
            "activities": [
                {
                    "id": a.id,
                    "name": a.name,
                    "planned_start_date": a.planned_start_date,
                    "planned_end_date": a.planned_end_date,
                    "planned_duration_days": a.planned_duration_days,
                    "manual_override": a.manual_override
                } for a in activities
            ]
        })
    return result
