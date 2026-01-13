# app/routes/daily_entry.py
# --------------------------------------------------
# Daily Activity Execution (Quantity-Based Progress)
# --------------------------------------------------

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.daily_entry import DailyEntry
from app.models.project_activity import ProjectActivity
from app.models.activity_progress import ActivityProgress
from app.utils.audit_logger import log_action, model_to_dict
from app.utils.dates import parse_date_ddmmyyyy_or_iso

router = APIRouter(
    prefix="/daily-entry",
    tags=["Daily Activity Execution"]
)


# ==================================================
# SAFETY GET HANDLER
# ==================================================
@router.get("/")
def daily_entry_guard():
    return RedirectResponse("/execution", status_code=302)


# ==================================================
# ADD DAILY EXECUTION ENTRY (FORM SAFE)
# ==================================================
@router.post("/")
def add_daily_entry(
    request: Request,
    project_id: int = Form(...),
    activity_id: int = Form(...),
    quantity_done: float = Form(...),
    entry_date: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        entry_date_obj = parse_date_ddmmyyyy_or_iso(entry_date)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format; use DD/MM/YYYY")
    pa = (
        db.query(ProjectActivity)
        .filter(
            ProjectActivity.project_id == project_id,
            ProjectActivity.activity_id == activity_id
        )
        .first()
    )

    if not pa:
        raise HTTPException(status_code=400, detail="Activity not planned")

    entry = DailyEntry(
        project_id=project_id,
        activity_id=activity_id,
        quantity_done=quantity_done,
        entry_date=entry_date_obj
    )
    db.add(entry)
    db.commit()

    entry_snapshot = model_to_dict(entry)

    cumulative_qty = (
        db.query(func.sum(DailyEntry.quantity_done))
        .filter(
            DailyEntry.project_id == project_id,
            DailyEntry.activity_id == activity_id
        )
        .scalar()
        or 0.0
    )

    progress = int(min((cumulative_qty / pa.planned_quantity) * 100, 100))

    ap = (
        db.query(ActivityProgress)
        .filter(
            ActivityProgress.project_id == project_id,
            ActivityProgress.activity_id == activity_id
        )
        .first()
    )

    if not ap:
        raise HTTPException(status_code=400, detail="Progress row missing")

    old_progress = model_to_dict(ap)

    ap.progress_percent = progress

    if progress > 0 and ap.actual_start is None:
        ap.actual_start = entry_date_obj

    if progress == 100:
        ap.actual_end = entry_date_obj
        ap.status = "COMPLETED"
    else:
        ap.status = "DELAYED" if entry_date_obj > ap.planned_end else "IN_PROGRESS"

    db.commit()

    log_action(
        db=db,
        request=request,
        action="CREATE",
        entity_type="Execution",
        entity_id=entry.id,
        description=f"Daily execution entry: project #{project_id}, activity #{activity_id}",
        old_value={"progress": old_progress},
        new_value={"entry": entry_snapshot, "progress": model_to_dict(ap)},
    )

    return RedirectResponse(
        f"/execution/{project_id}",
        status_code=302
    )
