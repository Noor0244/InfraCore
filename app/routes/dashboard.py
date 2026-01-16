from datetime import date

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.session import get_db
from app.models.project import Project
from app.models.project_user import ProjectUser
from app.services.report_service import get_summary
from app.services.update_alerts_service import AlertConfig, compute_project_update_alerts
from app.services.stretch_dashboard_service import StretchDashboardConfig, compute_stretch_intelligence
from app.services.settings_service import get_int_setting
from app.utils.flash import flash
from app.utils.template_filters import register_template_filters
from app.models.road_stretch import RoadStretch

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    project_id: int | None = None,
    view: str | None = None,
    lookahead_days: int | None = None,
    due_soon_days: int | None = None,
    stretch_id: int | None = None,
    status: str | None = None,
    activity_id: int | None = None,
    material_id: int | None = None,
    db: Session = Depends(get_db)
):
    # =====================================================
    # AUTH CHECK
    # =====================================================
    user = request.session.get("user")
    if user is None:
        flash(request, "Please login to access dashboard", "warning")
        return RedirectResponse("/login", status_code=302)

    user_id = user["id"]

    # =====================================================
    # PROJECT VISIBILITY (CONSISTENT WITH /projects)
    # =====================================================
    if user.get("role") in {"admin", "superadmin"}:
        base_query = db.query(Project)
    else:
        base_query = (
            db.query(Project)
            .outerjoin(ProjectUser, Project.id == ProjectUser.project_id)
            .filter(
                or_(
                    Project.created_by == user_id,
                    ProjectUser.user_id == user_id,
                )
            )
            .distinct()
        )

    # Only list active projects for selection and display
    projects = base_query.filter(Project.is_active == True).order_by(Project.id.desc()).all()
    has_projects = len(projects) > 0

    # =====================================================
    # SAFE PROJECT SELECTION
    # =====================================================
    project = None

    if has_projects:
        # 🔒 Explicit project_id only if allowed
        if project_id:
            project = base_query.filter(Project.id == project_id).first()

        # 🔁 Fallback: active project
        if project is None:
            project = (
                base_query
                .filter(Project.is_active == True)
                .order_by(Project.id.desc())
                .first()
            )

        # 🔁 Final fallback: any project
        if project is None:
            project = base_query.order_by(Project.id.desc()).first()

    # =====================================================
    # PROJECT ROLE RESOLUTION
    # =====================================================
    project_role = "viewer"

    if user["role"] in {"admin", "superadmin"}:
        project_role = "admin"
    elif project:
        pu = (
            db.query(ProjectUser)
            .filter(
                ProjectUser.project_id == project.id,
                ProjectUser.user_id == user_id
            )
            .first()
        )
        if pu:
            project_role = pu.role_in_project

    # =====================================================
    # SUMMARY (SAFE WHEN NO PROJECT)
    # =====================================================
    summary = (
        get_summary(project_id=project.id)
        if project else
        {
            "total_reports": 0,
            "reports_today": 0,
        }
    )

    if project:
        lookahead_days_eff = int(lookahead_days) if lookahead_days is not None else get_int_setting(db, user_id=int(user_id), key="alerts.lookahead_days", default=30)
        due_soon_days_eff = int(due_soon_days) if due_soon_days is not None else get_int_setting(db, user_id=int(user_id), key="alerts.due_soon_days", default=7)
        max_rows = get_int_setting(db, user_id=int(user_id), key="alerts.max_rows", default=30)

        cfg = AlertConfig(
            lookahead_days=int(lookahead_days_eff),
            due_soon_days=int(due_soon_days_eff),
            max_rows=int(max_rows),
        )
        alerts = compute_project_update_alerts(db=db, project_id=int(project.id), cfg=cfg)
    else:
        alerts = None

    # =====================================================
    # STRETCH INTELLIGENCE (Road-only, non-breaking)
    # =====================================================
    dash_view = (view or "project").strip().lower() or "project"
    stretch_intel = None
    has_stretches = False
    stretch_choices: list[RoadStretch] = []

    if project and str(getattr(project, "project_type", "") or "").strip().lower() == "road":
        stretch_choices = (
            db.query(RoadStretch)
            .filter(
                RoadStretch.project_id == int(project.id),
                RoadStretch.is_active == True,  # noqa: E712
            )
            .order_by(RoadStretch.sequence_no.asc())
            .all()
        )
        has_stretches = len(stretch_choices) > 0

        if dash_view == "stretch" and has_stretches:
            # Use same defaults as project alerts unless overridden.
            lookahead_days_eff = int(lookahead_days) if lookahead_days is not None else int(alerts.get("cfg", {}).get("lookahead_days", 30)) if alerts else 30
            due_soon_days_eff = int(due_soon_days) if due_soon_days is not None else int(alerts.get("cfg", {}).get("due_soon_days", 7)) if alerts else 7
            max_rows_eff = int(alerts.get("cfg", {}).get("max_rows", 50)) if alerts else 50

            s_cfg = StretchDashboardConfig(
                lookahead_days=int(lookahead_days_eff),
                due_soon_days=int(due_soon_days_eff),
                max_rows=int(max_rows_eff),
            )
            stretch_intel = compute_stretch_intelligence(
                db=db,
                project_id=int(project.id),
                today=date.today(),
                cfg=s_cfg,
                stretch_id=int(stretch_id) if stretch_id else None,
                status=status,
                activity_id=int(activity_id) if activity_id else None,
                material_id=int(material_id) if material_id else None,
            )
        elif dash_view == "stretch" and not has_stretches:
            # Fallback to project view if no stretches exist.
            dash_view = "project"

    # =====================================================
    # RENDER
    # =====================================================
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "Dashboard",

            # USER CONTEXT
            "user": user,
            "is_admin": user["role"] in {"admin", "superadmin"},

            # PROJECT CONTEXT
            "projects": projects,
            "project": project,
            "project_id": project.id if project else None,
            "has_projects": has_projects,
            "project_role": project_role,

            # KPI / SUMMARY
            "summary": summary,

            # ALERTS / UPDATES
            "alerts": alerts,

            # DASHBOARD MODE
            "dash_view": dash_view,
            "has_stretches": has_stretches,
            "stretch_choices": stretch_choices,
            "stretch_intel": stretch_intel,
        }
    )
