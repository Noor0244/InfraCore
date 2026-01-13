from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import hashlib

from app.db.session import get_db
from app.models.user import User
from app.models.user_session import UserSession
from app.utils.flash import flash
from app.utils.template_filters import register_template_filters
from app.utils.audit_logger import log_action, model_to_dict
from app.utils.dates import parse_date_ddmmyyyy_or_iso

# 🔹 ADDED (DO NOT REMOVE EXISTING IMPORTS)
from app.models.project import Project
from app.models.project_user import ProjectUser

from datetime import datetime, date, time

from app.models.activity_log import ActivityLog

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)


def admin_guard(request: Request):
    user = request.session.get("user")
    if not user or user["role"] != "admin":
        flash(request, "Admin access required", "warning")
        return None
    return user


def hash_password(p: str):
    return hashlib.sha256(p.encode()).hexdigest()


# ================= ADMIN: AUDIT LOGS =================
@router.get("/logs", response_class=HTMLResponse)
def audit_logs_page(
    request: Request,
    page: int = 1,
    action: str | None = None,
    entity_type: str | None = None,
    user_id: int | None = None,
    username: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    admin = admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    page_size = 50
    page = max(page, 1)

    q = db.query(ActivityLog)

    if action:
        q = q.filter(ActivityLog.action == action)
    if entity_type:
        q = q.filter(ActivityLog.entity_type == entity_type)
    if user_id is not None:
        q = q.filter(ActivityLog.user_id == user_id)
    if username:
        q = q.filter(ActivityLog.username.ilike(f"%{username.strip()}%"))

    # Date range parsing (DD/MM/YYYY or YYYY-MM-DD)
    def _parse_d(s: str | None) -> date | None:
        if not s:
            return None
        try:
            return parse_date_ddmmyyyy_or_iso(str(s))
        except Exception:
            return None

    sd = _parse_d(start_date)
    ed = _parse_d(end_date)
    if sd:
        q = q.filter(ActivityLog.created_at >= datetime.combine(sd, time.min))
    if ed:
        q = q.filter(ActivityLog.created_at <= datetime.combine(ed, time.max))

    total = q.count()
    logs = (
        q.order_by(ActivityLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Filter dropdown options (lightweight)
    actions = [r[0] for r in db.query(ActivityLog.action).distinct().order_by(ActivityLog.action).all() if r and r[0]]
    entity_types = [r[0] for r in db.query(ActivityLog.entity_type).distinct().order_by(ActivityLog.entity_type).all() if r and r[0]]
    users = (
        db.query(ActivityLog.user_id, ActivityLog.username)
        .filter(ActivityLog.user_id.isnot(None))
        .distinct()
        .order_by(ActivityLog.username.asc())
        .all()
    )

    return templates.TemplateResponse(
        "admin/logs.html",
        {
            "request": request,
            "user": admin,
            "logs": logs,
            "page": page,
            "page_size": page_size,
            "total": total,
            "actions": actions,
            "entity_types": entity_types,
            "users": users,
            "filters": {
                "action": action or "",
                "entity_type": entity_type or "",
                "user_id": user_id if user_id is not None else "",
                "username": username or "",
                "start_date": start_date or "",
                "end_date": end_date or "",
            },
        },
    )


# ================= ADMIN: USER LIST =================
@router.get("/users", response_class=HTMLResponse)
def users_list(request: Request, db: Session = Depends(get_db)):

    admin = admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    users = db.query(User).order_by(User.id.desc()).all()

    html = templates.get_template("admin/users_list.html").render(
        request=request,
        title="User Management",
        users=users,
        user=admin,
    )

    return HTMLResponse(content=html)


# ================= ADMIN: CREATE USER =================
@router.get("/users/new", response_class=HTMLResponse)
def new_user_page(request: Request):

    admin = admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    html = templates.get_template("admin/user_form.html").render(
        request=request,
        title="Create User",
        user_data=None,
        project_users=[],
        all_projects=[],
        user=admin,
    )

    return HTMLResponse(content=html)


@router.post("/users/create")
def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
):

    admin = admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        flash(request, "Username already exists.", "error")
        return RedirectResponse("/admin/users", status_code=302)

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        is_active=True
    )

    db.add(user)
    db.commit()

    flash(request, "User created successfully.", "success")
    return RedirectResponse("/admin/users", status_code=302)


# ================= ADMIN: EDIT USER =================
@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
def edit_user_page(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):

    admin = admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        return RedirectResponse("/admin/users", status_code=302)

    # 🔹 ADDED: ALL PROJECTS
    all_projects = (
        db.query(Project)
        .order_by(Project.name.asc())
        .all()
    )

    # 🔹 ADDED: PROJECT ASSIGNMENTS FOR USER
    project_users = (
        db.query(ProjectUser)
        .filter(ProjectUser.user_id == user_id)
        .all()
    )

    html = templates.get_template("admin/user_form.html").render(
        request=request,
        title="Edit User",
        user_data=user_obj,
        project_users=project_users,
        all_projects=all_projects,
        user=admin,
    )

    return HTMLResponse(content=html)


@router.post("/users/{user_id}/update")
def update_user(
    user_id: int,
    request: Request,
    role: str = Form(...),
    password: str | None = Form(None),
    db: Session = Depends(get_db),
):

    admin = admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        return RedirectResponse("/admin/users", status_code=302)

    user_obj.role = role

    if password:
        user_obj.password_hash = hash_password(password)

    db.commit()

    flash(request, "User updated successfully.", "success")
    return RedirectResponse("/admin/users", status_code=302)


# ================= ADMIN: ENABLE / DISABLE USER =================
@router.post("/users/{user_id}/toggle")
def toggle_user_status(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):

    admin = admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    if admin["id"] == user_id:
        return RedirectResponse("/admin/users", status_code=302)

    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        return RedirectResponse("/admin/users", status_code=302)

    old = model_to_dict(user_obj)
    user_obj.is_active = not user_obj.is_active
    db.commit()

    log_action(
        db=db,
        request=request,
        action="UPDATE",
        entity_type="User",
        entity_id=user_obj.id,
        description=f"User {'enabled' if user_obj.is_active else 'disabled'}",
        old_value=old,
        new_value=model_to_dict(user_obj),
    )

    if user_obj.is_active:
        flash(request, "User enabled.", "success")
    else:
        flash(request, "User disabled.", "warning")

    return RedirectResponse("/admin/users", status_code=302)


# ================= ADMIN: USER LOGIN HISTORY =================
@router.get("/users/{user_id}/sessions", response_class=HTMLResponse)
def user_login_history(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):

    admin = admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        return RedirectResponse("/admin/users", status_code=302)

    sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id)
        .order_by(UserSession.login_time.desc())
        .all()
    )

    total_logged_in_seconds = sum(
        s.session_duration or 0 for s in sessions
    )

    html = templates.get_template("admin/user_sessions.html").render(
        request=request,
        title=f"Login History – {user_obj.username}",
        user_obj=user_obj,
        sessions=sessions,
        total_logged_in_seconds=total_logged_in_seconds,
        user=admin,
    )

    return HTMLResponse(content=html)


# ================= ADMIN: DELETE USER =================
@router.post("/users/{user_id}/delete")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):

    admin = admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    # Prevent self-deletion
    if admin["id"] == user_id:
        flash(request, "You cannot delete your own account.", "error")
        return RedirectResponse("/admin/users", status_code=302)

    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        flash(request, "User not found.", "error")
        return RedirectResponse("/admin/users", status_code=302)

    # Prevent deleting the last active admin
    if user_obj.role == "admin":
        active_admins = db.query(User).filter(User.role == "admin", User.is_active == True).count()
        if active_admins <= 1:
            flash(request, "Cannot delete the last active admin.", "error")
            return RedirectResponse("/admin/users", status_code=302)

    # Delete dependent sessions first to avoid FK issues
    db.query(UserSession).filter(UserSession.user_id == user_id).delete(synchronize_session=False)

    # Also delete any project-user mappings referencing this user (safe)
    try:
        from app.models.project_user import ProjectUser
        db.query(ProjectUser).filter(ProjectUser.user_id == user_id).delete(synchronize_session=False)
    except Exception:
        # if the model isn't present for some reason, continue
        pass

    # Finally delete the user
    db.delete(user_obj)
    db.commit()

    flash(request, "User deleted successfully.", "success")
    return RedirectResponse("/admin/users", status_code=302)
