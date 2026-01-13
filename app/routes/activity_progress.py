# app/routes/activity_progress.py
# --------------------------------------------------
# Project Activity Progress (Role-Protected)
# InfraCore
# --------------------------------------------------

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.models.project_activity import ProjectActivity
from app.models.activity_progress import ActivityProgress
from app.models.project_user import ProjectUser

router = APIRouter(prefix="/projects", tags=["Activity Progress"])


# ==================================================
# HELPERS
# ==================================================

def get_project_role(db: Session, user: dict, project_id: int):
    """
    Returns:
    - 'admin' if system admin
    - role_in_project if assigned
    - None if no access
    """
    if user["role"] == "admin":
        return "admin"

    pu = (
        db.query(ProjectUser)
        .filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == user["id"]
        )
        .first()
    )

    return pu.role_in_project if pu else None


def require_progress_update_permission(role: str):
    """
    Admin / Manager / Member can update progress.
    Viewer cannot.
    """
    if role not in ("admin", "manager", "member"):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update progress"
        )


# ==================================================
# UPDATE ACTIVITY PROGRESS
# ==================================================
@router.post("/{project_id}/activities/{project_activity_id}/progress")
def update_activity_progress(
    project_id: int,
    project_activity_id: int,
    request: Request,
    progress_percent: float = Form(...),
    remarks: str | None = Form(None),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=302)

    # ---------- PROJECT ROLE ----------
    role = get_project_role(db, user, project_id)
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this project")

    require_progress_update_permission(role)

    # ---------- VALIDATE PROJECT ACTIVITY ----------
    pa = (
        db.query(ProjectActivity)
        .filter(
            ProjectActivity.id == project_activity_id,
            ProjectActivity.project_id == project_id
        )
        .first()
    )

    if not pa:
        raise HTTPException(status_code=404, detail="Project activity not found")

    # ---------- CREATE PROGRESS ENTRY ----------
    progress = ActivityProgress(
        project_activity_id=project_activity_id,
        progress_percent=progress_percent,
        remarks=remarks,
        updated_at=datetime.utcnow(),
    )

    db.add(progress)
    db.commit()

    return RedirectResponse(
        f"/projects/{project_id}/activities",
        status_code=302
    )
