from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.activity import Activity
from app.models.material import Material
from app.models.material_vendor import MaterialVendor
from app.models.procurement_log import ProcurementLog
from app.models.project import Project
from app.models.project_user import ProjectUser
from app.utils.flash import flash
from app.utils.template_filters import register_template_filters
from app.utils.dates import parse_date_ddmmyyyy_or_iso

router = APIRouter(prefix="/procurement", tags=["Procurement"])
templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)


def _can_procure(user: dict | None) -> bool:
    if not user:
        return False
    return user.get("role") in ["admin", "manager"]


def _visible_projects(db: Session, user: dict) -> list[Project]:
    base = (
        db.query(Project)
        .outerjoin(ProjectUser, Project.id == ProjectUser.project_id)
        .filter(
            Project.is_active == True,  # noqa: E712
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


@router.get("/", response_class=HTMLResponse)
def procurement_project_select(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    if not _can_procure(user):
        return RedirectResponse("/dashboard", status_code=302)

    projects = _visible_projects(db, user)
    if len(projects) == 1:
        return RedirectResponse(f"/procurement/{int(projects[0].id)}", status_code=302)

    return templates.TemplateResponse(
        "procurement_select.html",
        {
            "request": request,
            "user": user,
            "projects": projects,
        },
    )


@router.get("/{project_id}", response_class=HTMLResponse)
def procurement_page(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    if not _can_procure(user):
        return RedirectResponse("/dashboard", status_code=302)

    projects = _visible_projects(db, user)
    if int(project_id) not in {int(p.id) for p in projects}:
        flash(request, "Project not found or access denied", "error")
        return RedirectResponse("/dashboard", status_code=302)

    project = db.query(Project).filter(Project.id == int(project_id)).first()
    if not project:
        return RedirectResponse("/dashboard", status_code=302)

    request.session["last_project_id"] = int(project_id)

    materials = db.query(Material).filter(Material.is_active == True).order_by(Material.name.asc()).all()  # noqa: E712
    vendors = db.query(MaterialVendor).order_by(MaterialVendor.is_active.desc(), MaterialVendor.vendor_name.asc()).all()

    vendors_by_material: dict[str, list[dict[str, object]]] = {}
    for v in vendors:
        vendors_by_material.setdefault(str(int(v.material_id)), []).append(
            {
                "id": int(v.id),
                "vendor_name": str(v.vendor_name or ""),
                "lead_time_days": int(v.lead_time_days or 0),
                "is_active": bool(v.is_active),
            }
        )

    activities = (
        db.query(Activity)
        .filter(Activity.project_id == int(project_id), Activity.is_active == True)  # noqa: E712
        .order_by(Activity.id.asc())
        .all()
    )

    logs = (
        db.query(ProcurementLog, Material, MaterialVendor, Activity)
        .join(Material, Material.id == ProcurementLog.material_id)
        .outerjoin(MaterialVendor, MaterialVendor.id == ProcurementLog.vendor_id)
        .outerjoin(Activity, Activity.id == ProcurementLog.activity_id)
        .filter(ProcurementLog.project_id == int(project_id))
        .order_by(ProcurementLog.order_date.desc(), ProcurementLog.id.desc())
        .limit(300)
        .all()
    )

    return templates.TemplateResponse(
        "procurement.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "projects": projects,
            "materials": materials,
            "activities": activities,
            "vendors_by_material_json": vendors_by_material,
            "logs": logs,
            "today": date.today(),
        },
    )


@router.post("/logs/create")
async def procurement_create(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    if not _can_procure(user):
        return RedirectResponse("/dashboard", status_code=302)

    form = await request.form()

    def _d(name: str) -> date | None:
        raw = str(form.get(name) or "").strip()
        if not raw:
            return None
        try:
            return parse_date_ddmmyyyy_or_iso(raw)
        except Exception:
            return None

    def _i(name: str) -> int | None:
        raw = str(form.get(name) or "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except Exception:
            return None

    def _f(name: str) -> float | None:
        raw = str(form.get(name) or "").strip()
        if not raw:
            return None
        try:
            return float(raw)
        except Exception:
            return None

    project_id = _i("project_id") or 0
    material_id = _i("material_id") or 0
    vendor_id = _i("vendor_id")
    activity_id = _i("activity_id")

    order_date = _d("order_date")
    promised_delivery_date = _d("promised_delivery_date")
    delivered_date = _d("delivered_date")

    qty = _f("quantity")
    unit = str(form.get("unit") or "").strip() or None
    notes = str(form.get("notes") or "").strip() or None

    if project_id <= 0 or material_id <= 0 or not order_date:
        flash(request, "Project, Material, and Order Date are required", "warning")
        return RedirectResponse(f"/procurement/{project_id}" if project_id else "/dashboard", status_code=302)

    promised_lt = ProcurementLog.compute_lead_time_days(order_date, promised_delivery_date)
    actual_lt = ProcurementLog.compute_lead_time_days(order_date, delivered_date)

    row = ProcurementLog(
        project_id=int(project_id),
        material_id=int(material_id),
        vendor_id=int(vendor_id) if vendor_id else None,
        activity_id=int(activity_id) if activity_id else None,
        order_date=order_date,
        promised_delivery_date=promised_delivery_date,
        delivered_date=delivered_date,
        promised_lead_time_days=promised_lt,
        actual_lead_time_days=actual_lt,
        quantity=qty,
        unit=unit,
        notes=notes,
        created_by_user_id=int(user.get("id")) if user.get("id") else None,
    )

    db.add(row)
    db.commit()

    flash(request, "Procurement entry saved", "success")
    return RedirectResponse(f"/procurement/{project_id}", status_code=302)
