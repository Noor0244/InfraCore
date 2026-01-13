from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import schedule_service


router = APIRouter(
    prefix="/schedule",
    tags=["Schedule"]
)

# ============================================================
# REQUEST SCHEMAS (ROUTE LAYER ONLY)
# ============================================================

class SchedulePlanCreate(BaseModel):
    project_id: int
    activity_id: int
    planned_start: date
    planned_end: date


# ============================================================
# ROUTES
# ============================================================

@router.post("/plan")
def set_planned_schedule(
    payload: SchedulePlanCreate,
    db: Session = Depends(get_db)
):
    """
    Create / update planned schedule baseline
    """
    try:
        return schedule_service.set_planned_schedule(
            db=db,
            project_id=payload.project_id,
            activity_id=payload.activity_id,
            planned_start=payload.planned_start,
            planned_end=payload.planned_end
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 🔒 MANUAL PROGRESS UPDATE — DISABLED (INTENTIONAL)
# ============================================================

@router.put("/progress")
def update_activity_progress():
    """
    ❌ MANUAL PROGRESS UPDATE DISABLED

    Progress is now **quantity-driven only**
    via `/daily-entry`.

    This endpoint is intentionally blocked
    to prevent fake or manual progress.
    """
    raise HTTPException(
        status_code=403,
        detail="Manual progress updates are disabled. Use daily execution entries."
    )


# ============================================================
# FETCH PROJECT SCHEDULE
# ============================================================

@router.get("/project/{project_id}")
def get_project_schedule(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Read-only schedule + delay analytics
    """
    return schedule_service.get_project_schedule(
        db=db,
        project_id=project_id
    )
