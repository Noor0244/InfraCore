# app/routes/activities.py
# --------------------------------------------------
# Project-Scoped Activity CRUD (FIXED PROPERLY)
# InfraCore
# --------------------------------------------------

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.models.activity import Activity
from app.models.project import Project
from app.models.project_user import ProjectUser
from app.models.project_activity import ProjectActivity
from app.utils.audit_logger import log_action, model_to_dict
from app.utils.id_codes import generate_next_activity_code

router = APIRouter(
    prefix="/projects",
    tags=["Project Activities"]
)

templates = Jinja2Templates(directory="app/templates")


# ==================================================
# ACCESS GUARD
# ==================================================
def require_project_access(db: Session, user: dict, project_id: int):
    if user["role"] in {"admin", "superadmin"}:
        return True

    project = db.query(Project).filter(Project.id == project_id).first()
    if project and project.created_by == user["id"]:
        return True

    pu = (
        db.query(ProjectUser)
        .filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == user["id"]
        )
        .first()
    )

    if pu and pu.role_in_project in ("owner", "admin", "manager"):
        return True

    return False


# ==================================================
# LIST ACTIVITIES (PER PROJECT)
# ==================================================
## Project Activities page disabled by request


# ==================================================
# ADD ACTIVITY PAGE
# ==================================================
@router.get("/{project_id}/activities/new", response_class=HTMLResponse)
def new_activity_page(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=302)

    if not require_project_access(db, user, project_id):
        return RedirectResponse("/dashboard", status_code=302)

    project = db.query(Project).filter(Project.id == project_id).first()

    return templates.TemplateResponse(
        "activity_form.html",
        {
            "request": request,
            "project": project,
            "user": user,
        }
    )


# ==================================================
# CREATE ACTIVITY (PROJECT-SCOPED)
# ==================================================
@router.post("/{project_id}/activities/create")
def create_activity(
    project_id: int,
    request: Request,
    name: str = Form(...),
    is_standard: bool = Form(False),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=302)

    if not require_project_access(db, user, project_id):
        return RedirectResponse("/dashboard", status_code=302)

    # Prevent duplicate activity in same project
    existing = (
        db.query(Activity)
        .filter(
            Activity.project_id == project_id,
            Activity.name == name
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Activity already exists for this project"
        )

    activity = Activity(
        name=name,
        is_standard=is_standard,
        project_id=project_id,
    )

    # Assign human-friendly project-scoped code
    activity.code = generate_next_activity_code(db, Activity, project_id=project_id, code_attr="code", width=6, project_width=6)

    db.add(activity)
    db.commit()

    log_action(
        db=db,
        request=request,
        action="CREATE",
        entity_type="Activity",
        entity_id=activity.id,
        description=f"Activity created in project #{project_id}",
        old_value=None,
        new_value=model_to_dict(activity),
    )

    return RedirectResponse(
        f"/activity-material-planning/{project_id}",
        status_code=302
    )


# ==================================================
# UPDATE ACTIVITY END DATE
# ==================================================
@router.post("/api/activities/{activity_id}/update-end-date")
async def update_activity_end_date(
    activity_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"success": False, "error": "Unauthorized"}, status_code=401)

    # Get the request body
    try:
        body = await request.json()
    except:
        return JSONResponse({"success": False, "error": "Invalid JSON"}, status_code=400)

    project_id = body.get("project_id")
    new_end_date_str = body.get("new_end_date")
    reason = body.get("reason", "")
    remarks = body.get("remarks", "")

    if not project_id or not new_end_date_str:
        return JSONResponse({"success": False, "error": "Missing project_id or new_end_date"}, status_code=400)

    # Parse the date
    try:
        new_end_date = datetime.strptime(new_end_date_str, "%Y-%m-%d").date()
    except:
        return JSONResponse({"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}, status_code=400)

    # Check access
    if not require_project_access(db, user, project_id):
        return JSONResponse({"success": False, "error": "Access denied"}, status_code=403)

    # Update ProjectActivity
    project_activity = (
        db.query(ProjectActivity)
        .filter(
            ProjectActivity.activity_id == activity_id,
            ProjectActivity.project_id == project_id
        )
        .first()
    )

    if not project_activity:
        return JSONResponse({"success": False, "error": "Activity not found in this project"}, status_code=404)

    # Store old value for audit
    old_end_date = project_activity.end_date

    # Update the end date
    project_activity.end_date = new_end_date

    db.commit()

    # Log the action
    log_action(
        db=db,
        request=request,
        action="UPDATE",
        entity_type="ProjectActivity",
        entity_id=project_activity.id,
        description=f"Activity end date updated from {old_end_date} to {new_end_date}. Reason: {reason}",
        old_value={"end_date": str(old_end_date)},
        new_value={"end_date": str(new_end_date), "reason": reason, "remarks": remarks},
    )

    return JSONResponse({
        "success": True,
        "message": "Activity end date updated successfully",
        "new_end_date": str(new_end_date),
        "old_end_date": str(old_end_date)
    })
