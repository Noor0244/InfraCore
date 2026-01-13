from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.models.project_user import ProjectUser


router = APIRouter(
    prefix="/admin/projects",
    tags=["Project Users"]
)

templates = Jinja2Templates(directory="app/templates")


# --------------------------------------------------
# GUARD: ADMIN / MANAGER ONLY
# --------------------------------------------------
def project_admin_guard(request: Request):
    user = request.session.get("user")
    if not user:
        return None

    if user["role"] not in ["admin", "manager"]:
        return None

    return user


# --------------------------------------------------
# VIEW & MANAGE USERS OF A PROJECT
# --------------------------------------------------
@router.get("/{project_id}/users", response_class=HTMLResponse)
def project_users_page(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = project_admin_guard(request)
    if not current_user:
        return RedirectResponse("/dashboard", status_code=302)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return RedirectResponse("/projects/manage", status_code=302)

    # Assigned users
    project_users = (
        db.query(ProjectUser)
        .filter(ProjectUser.project_id == project_id)
        .all()
    )

    assigned_user_ids = [pu.user_id for pu in project_users]

    # Available users (active + not assigned)
    available_users = (
        db.query(User)
        .filter(User.is_active == True)
        .filter(~User.id.in_(assigned_user_ids))
        .all()
    )

    return templates.TemplateResponse(
        "admin/project_users.html",
        {
            "request": request,
            "title": f"Project Users – {project.name}",
            "project": project,
            "project_users": project_users,
            "available_users": available_users,
            "user": current_user,
        }
    )


# --------------------------------------------------
# ADD USER TO PROJECT
# --------------------------------------------------
@router.post("/{project_id}/users/add")
def add_user_to_project(
    project_id: int,
    request: Request,
    user_id: int = Form(...),
    role_in_project: str = Form(...),
    db: Session = Depends(get_db),
):
    current_user = project_admin_guard(request)
    if not current_user:
        return RedirectResponse("/dashboard", status_code=302)

    exists = (
        db.query(ProjectUser)
        .filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == user_id,
        )
        .first()
    )

    if not exists:
        db.add(
            ProjectUser(
                project_id=project_id,
                user_id=user_id,
                role_in_project=role_in_project,
            )
        )
        db.commit()

    return RedirectResponse(
        f"/admin/projects/{project_id}/users",
        status_code=302
    )


# --------------------------------------------------
# REMOVE USER FROM PROJECT
# --------------------------------------------------
@router.post("/{project_id}/users/{user_id}/remove")
def remove_user_from_project(
    project_id: int,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = project_admin_guard(request)
    if not current_user:
        return RedirectResponse("/dashboard", status_code=302)

    project_user = (
        db.query(ProjectUser)
        .filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == user_id,
        )
        .first()
    )

    if project_user:
        db.delete(project_user)
        db.commit()

    return RedirectResponse(
        f"/admin/projects/{project_id}/users",
        status_code=302
    )
# --------------------------------------------------
# ASSIGN USER TO PROJECT (FROM USER PAGE)
# --------------------------------------------------
@router.post("/assign-user")
def assign_user_to_project(
    request: Request,
    user_id: int = Form(...),
    project_id: int = Form(...),
    role_in_project: str = Form(...),
    db: Session = Depends(get_db),
):
    current_user = project_admin_guard(request)
    if not current_user:
        return RedirectResponse("/dashboard", status_code=302)

    exists = (
        db.query(ProjectUser)
        .filter(
            ProjectUser.user_id == user_id,
            ProjectUser.project_id == project_id
        )
        .first()
    )

    if not exists:
        db.add(
            ProjectUser(
                user_id=user_id,
                project_id=project_id,
                role_in_project=role_in_project
            )
        )
        db.commit()

    return RedirectResponse(
        f"/admin/users/{user_id}/edit",
        status_code=302
    )
