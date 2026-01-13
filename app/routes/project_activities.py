# app/routes/project_activities.py
# --------------------------------------------------
# Project Activities (Project-Scoped with Role Guard)
# InfraCore
# --------------------------------------------------

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.models.activity import Activity
from app.models.project_activity import ProjectActivity
from app.models.project_user import ProjectUser
from app.utils.audit_logger import log_action, model_to_dict
from app.utils.road_classification import get_presets_for_engineering_type
from app.utils.project_type_presets import get_presets_for_project_type
from app.utils.id_codes import generate_next_activity_code
from app.utils.template_filters import register_template_filters

router = APIRouter(prefix="/projects", tags=["Project Activities"])
templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)


# ==================================================
# HELPERS
# ==================================================

def get_project_role(db: Session, user: dict, project_id: int):
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


def require_project_access(db, user, project_id):
    role = get_project_role(db, user, project_id)
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this project")
    return role


# ==================================================
# VIEW PROJECT ACTIVITIES
# ==================================================
@router.get("/{project_id}/activities", response_class=HTMLResponse)
def view_project_activities(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=302)

    role = require_project_access(db, user, project_id)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return RedirectResponse("/projects/manage", status_code=302)

    activities = (
        db.query(Activity)
        .filter(Activity.project_id == project_id)
        .order_by(Activity.id)
        .all()
    )

    return templates.TemplateResponse(
        "project_activities.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "activities": activities,
            "project_role": role,
        }
    )


# ==================================================
# NEW ACTIVITY FORM
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

    role = require_project_access(db, user, project_id)
    if role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Permission denied")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return RedirectResponse("/projects/manage", status_code=302)

    project_type = (project.project_type or "").strip() or "Building"
    suggested: list[str] = []
    if project_type.lower() == "road":
        preset = get_presets_for_engineering_type(getattr(project, "road_engineering_type", None))
        suggested = [str(a).strip() for a in (preset.get("activities") or []) if str(a).strip()]
    else:
        preset = get_presets_for_project_type(project_type)
        suggested = [str(a).strip() for a in (preset.get("activities") or []) if str(a).strip()]

    # De-dupe while preserving order
    seen = set()
    suggested_activities: list[str] = []
    for s in suggested:
        k = s.lower()
        if k in seen:
            continue
        seen.add(k)
        suggested_activities.append(s)

    return templates.TemplateResponse(
        "activity_form.html",
        {
            "request": request,
            "project": project,
            "user": user,
            "suggested_activities": suggested_activities,
        }
    )


# ==================================================
# CREATE ACTIVITY (PROJECT-SCOPED) ✅ FIXED
# ==================================================
@router.post("/{project_id}/activities/create")
def create_activity_for_project(
    project_id: int,
    request: Request,
    name: str = Form(...),
    is_standard: str = Form("false"),  # 👈 FIXED (string)
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=302)

    role = require_project_access(db, user, project_id)
    if role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Permission denied")

    exists = (
        db.query(Activity)
        .filter(
            Activity.project_id == project_id,
            Activity.name == name
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Activity already exists")

    activity = Activity(
        name=name,
        is_standard=(is_standard == "true"),  # 👈 FIXED
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
