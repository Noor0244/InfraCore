from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.stretch_activity import StretchActivity

router = APIRouter(prefix="/stretch-activity", tags=["StretchActivity"])

@router.patch("/{activity_id}")
def update_stretch_activity(activity_id: int, data: dict, db: Session = Depends(get_db)):
    sa = db.query(StretchActivity).filter(StretchActivity.id == activity_id).first()
    if not sa:
        raise HTTPException(status_code=404, detail="StretchActivity not found")
    # Update fields from data
    for key, value in data.items():
        if hasattr(sa, key):
            setattr(sa, key, value)
    # Always set manual_override to True on edit
    sa.manual_override = True
    db.add(sa)
    db.commit()
    db.refresh(sa)
    return {"status": "success", "activity": {
        "id": sa.id,
        "name": sa.name,
        "planned_start_date": sa.planned_start_date,
        "planned_end_date": sa.planned_end_date,
        "planned_duration_days": sa.planned_duration_days,
        "manual_override": sa.manual_override
    }}
