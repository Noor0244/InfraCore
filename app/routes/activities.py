# app/routes/activities.py
# --------------------------------------------------
# Project-Scoped Activity CRUD (FIXED PROPERLY)
# InfraCore
# --------------------------------------------------

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.activity import Activity
from app.models.project import Project
from app.models.project_user import ProjectUser
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
    if user["role"] == "admin":
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
@router.get("/{project_id}/activities", response_class=HTMLResponse)
def list_project_activities(
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

    activities = (
        db.query(Activity)
        .filter(Activity.project_id == project_id)
        .order_by(Activity.id)
        .all()
    )

    return templates.TemplateResponse(
        "project_activities_list.html",
        {
            "request": request,
            "project": project,
            "activities": activities,
            "user": user,
        }
    )


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
