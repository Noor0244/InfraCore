# app/routes/project_activity_plan.py
# --------------------------------------------------
# Project Activity Planning (Schedule + Quantity)
# --------------------------------------------------

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from datetime import date  # ✅ FIX

from app.db.session import get_db
from app.models.project import Project
from app.models.activity import Activity
from app.models.project_activity import ProjectActivity
from app.models.activity_progress import ActivityProgress
from app.models.project_user import ProjectUser
from app.utils.project_type_presets import suggest_activity_units
from app.utils.activity_units import hours_to_display, normalize_display_unit, normalize_hours_per_day
from app.utils.audit_logger import log_action, model_to_dict
from app.utils.template_filters import register_template_filters
from app.utils.dates import parse_date_ddmmyyyy_or_iso

router = APIRouter(
    prefix="/project-activity-plan",
    tags=["Project Activity Planning"]
)

templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)


def _can_plan(user: dict | None) -> bool:
    if not user:
        return False
    return user.get("role") in ["admin", "manager"]


def _visible_projects(db: Session, user: dict) -> list[Project]:
    base = (
        db.query(Project)
        .outerjoin(ProjectUser, Project.id == ProjectUser.project_id)
        .filter(
            Project.is_active == True,
            Project.status == "active",
            Project.completed_at.is_(None),
            ~func.lower(Project.name).like("%preset%"),
            ~func.lower(Project.name).like("%test%"),
        )
    )

    if user.get("role") == "admin":
        return base.distinct().order_by(Project.created_at.desc()).all()

    return (
        base.filter(
            or_(
                Project.created_by == user.get("id"),
                ProjectUser.user_id == user.get("id"),
            )
        )
        .distinct()
        .order_by(Project.created_at.desc())
        .all()
    )


# --------------------------------------------------
# VIEW PLANNING PAGE
# --------------------------------------------------
@router.get("/", response_class=HTMLResponse)
def activity_plan_project_select(
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=302)

    if not _can_plan(user):
        return RedirectResponse("/dashboard", status_code=302)

    projects = _visible_projects(db, user)

    # Legacy page removed in favor of merged screen
    return RedirectResponse("/activity-material-planning", status_code=302)


@router.get("/{project_id}", response_class=HTMLResponse)
def plan_activities_page(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=302)

    if not _can_plan(user):
        return RedirectResponse("/dashboard", status_code=302)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return RedirectResponse("/dashboard", status_code=302)

    # Legacy page removed in favor of merged screen
    return RedirectResponse(f"/activity-material-planning/{project_id}", status_code=302)

    activities = (
        db.query(Activity)
        .filter(Activity.project_id == project_id)
        .order_by(Activity.id)
        .all()
    )

    planned = (
        db.query(ProjectActivity)
        .filter(ProjectActivity.project_id == project_id)
        .all()
    )

    planned_map = {p.activity_id: p for p in planned}

    unit_suggestions_by_activity_id: dict[int, list[str]] = {}
    project_type = (project.project_type or "").strip() or "Building"
    for a in activities:
        try:
            unit_suggestions_by_activity_id[int(a.id)] = suggest_activity_units(project_type, a.name)
        except Exception:
            unit_suggestions_by_activity_id[int(a.id)] = []

    # Fetch user's projects for the selector dropdown
    user_projects = _visible_projects(db, user)

    # Time planning maps (no conversion math in templates)
    time_plan_hours_by_activity_id: dict[int, float] = {}
    time_plan_display_by_activity_id: dict[int, float] = {}
    time_display_unit_by_activity_id: dict[int, str] = {}
    time_hours_per_day_by_activity_id: dict[int, float] = {}

    for a in activities:
        aid = int(a.id)
        hpd = normalize_hours_per_day(getattr(a, "hours_per_day", None), default=8.0)
        du = normalize_display_unit(getattr(a, "display_unit", None))
        base_hours = float(getattr(a, "planned_quantity_hours", 0.0) or 0.0)

        time_plan_hours_by_activity_id[aid] = base_hours
        time_display_unit_by_activity_id[aid] = du
        time_hours_per_day_by_activity_id[aid] = hpd
        time_plan_display_by_activity_id[aid] = round(hours_to_display(base_hours, du, hpd), 3)

    return templates.TemplateResponse(
        "project_activity_plan.html",
        {
            "request": request,
            "project": project,
            "activities": activities,
            "planned_map": planned_map,
            "unit_suggestions_by_activity_id": unit_suggestions_by_activity_id,
            "time_plan_hours_by_activity_id": time_plan_hours_by_activity_id,
            "time_plan_display_by_activity_id": time_plan_display_by_activity_id,
            "time_display_unit_by_activity_id": time_display_unit_by_activity_id,
            "time_hours_per_day_by_activity_id": time_hours_per_day_by_activity_id,
            "user": user,
            "projects": user_projects,
        }
    )


# --------------------------------------------------
# SAVE / UPDATE PLAN (✅ DATE FIXED)
# --------------------------------------------------
@router.post("/save")
def save_activity_plan(
    request: Request,
    project_id: int = Form(...),
    activity_id: int = Form(...),
    planned_quantity: float = Form(...),
    unit: str = Form(...),
    # Time planning (display input + hidden hours is preferred)
    planned_time_display: float = Form(...),
    planned_quantity_hours: float = Form(...),
    display_unit: str = Form("hours"),
    hours_per_day: float = Form(8.0),
    start_date: str = Form(...),
    end_date: str = Form(...),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=302)

    if not _can_plan(user):
        return RedirectResponse("/dashboard", status_code=302)

    # ✅ CONVERT STRING → date
    start_date_obj = parse_date_ddmmyyyy_or_iso(start_date)
    end_date_obj = parse_date_ddmmyyyy_or_iso(end_date)

    # ---------------- Time plan validation ----------------
    du = normalize_display_unit(display_unit)
    hpd = normalize_hours_per_day(hours_per_day, default=8.0)

    try:
        planned_time_display_f = float(planned_time_display or 0)
    except Exception:
        planned_time_display_f = 0.0

    try:
        planned_hours_f = float(planned_quantity_hours or 0)
    except Exception:
        planned_hours_f = 0.0

    # Prefer hidden base-hours if provided; fall back to display value.
    # (JS keeps hours in sync, but backend re-validates.)
    if planned_hours_f <= 0 and planned_time_display_f > 0:
        from app.utils.activity_units import display_to_hours
        planned_hours_f = float(display_to_hours(planned_time_display_f, du, hpd) or 0)

    if planned_time_display_f < 0 or planned_hours_f < 0:
        planned_time_display_f = 0.0
        planned_hours_f = 0.0

    if planned_hours_f <= 0:
        # Enforce planned quantity > 0 per requirements.
        return RedirectResponse(f"/activity-material-planning/{project_id}", status_code=302)

    act = db.query(Activity).filter(Activity.id == activity_id, Activity.project_id == project_id).first()
    if act:
        old_snapshot = model_to_dict(act)
        old_unit = getattr(act, "display_unit", "hours")

        act.planned_quantity_hours = float(planned_hours_f)
        act.display_unit = du
        act.hours_per_day = float(hpd)

        db.commit()

        # Audit: planned updated / unit changed
        if str(old_unit) != str(du):
            log_action(
                db=db,
                request=request,
                action="UPDATE",
                entity_type="Activity",
                entity_id=act.id,
                description=f"Activity display unit changed: activity #{act.id} {old_unit} -> {du}",
                old_value={"activity_id": act.id, "old_unit": old_unit, "old_value_hours": old_snapshot.get("planned_quantity_hours")},
                new_value={"activity_id": act.id, "new_unit": du, "new_value_hours": act.planned_quantity_hours},
            )

        log_action(
            db=db,
            request=request,
            action="UPDATE",
            entity_type="Activity",
            entity_id=act.id,
            description=f"Activity planned time updated (hours base): activity #{act.id}",
            old_value={"activity_id": act.id, "old_value_hours": old_snapshot.get("planned_quantity_hours")},
            new_value={"activity_id": act.id, "new_value_hours": act.planned_quantity_hours, "display_unit": du, "hours_per_day": hpd},
        )

    pa = (
        db.query(ProjectActivity)
        .filter(
            ProjectActivity.project_id == project_id,
            ProjectActivity.activity_id == activity_id
        )
        .first()
    )

    if pa:
        pa.planned_quantity = planned_quantity
        pa.unit = unit
        pa.start_date = start_date_obj
        pa.end_date = end_date_obj
    else:
        pa = ProjectActivity(
            project_id=project_id,
            activity_id=activity_id,
            planned_quantity=planned_quantity,
            unit=unit,
            start_date=start_date_obj,
            end_date=end_date_obj,
        )
        db.add(pa)

        # 🔑 Auto-create ActivityProgress (FIXED)
        db.add(
            ActivityProgress(
                project_id=project_id,
                activity_id=activity_id,
                planned_start=start_date_obj,
                planned_end=end_date_obj,
                progress_percent=0,
                status="NOT_STARTED"
            )
        )

    db.commit()

    return RedirectResponse(
        f"/activity-material-planning/{project_id}",
        status_code=302
    )
