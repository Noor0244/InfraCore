from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.activity import Activity
from app.models.activity_material import ActivityMaterial
from app.models.activity_progress import ActivityProgress
from app.models.material import Material
from app.models.material_stock import MaterialStock
from app.models.material_vendor import MaterialVendor
from app.models.project import Project
from app.models.project_activity import ProjectActivity
from app.models.project_user import ProjectUser
from app.utils.activity_units import (
    display_to_hours,
    normalize_display_unit,
    normalize_hours_per_day,
)
from app.utils.dates import format_date_ddmmyyyy, parse_date_ddmmyyyy_or_iso
from app.utils.audit_logger import log_action, model_to_dict
from app.utils.flash import flash
from app.utils.template_filters import register_template_filters
from app.utils.material_lead_time import (
    compute_expected_delivery_date,
    compute_reorder_suggestion,
    normalize_lead_time_days,
    resolve_effective_lead_time_days,
)

router = APIRouter(prefix="/activity-material-planning", tags=["Activity Planning & Material Management"])
templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)


def _can_plan(user: dict | None) -> bool:
    if not user:
        return False
    return user.get("role") in ["admin", "manager"]


def _is_admin(user: dict | None) -> bool:
    return bool(user and user.get("role") == "admin")


def _activity_progress_percent(db: Session, project_id: int, activity_id: int) -> int:
    row = (
        db.query(ActivityProgress)
        .filter(
            ActivityProgress.project_id == int(project_id),
            ActivityProgress.activity_id == int(activity_id),
        )
        .first()
    )
    try:
        return int(getattr(row, "progress_percent", 0) or 0) if row else 0
    except Exception:
        return 0


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


def _wants_json(request: Request) -> bool:
    accept = (request.headers.get("accept") or "").lower()
    return "application/json" in accept or request.headers.get("x-requested-with") == "XMLHttpRequest"


def _compute_order_date(activity_start: date | None, lead_time_days: int | None) -> date | None:
    if not activity_start:
        return None
    ltd = normalize_lead_time_days(lead_time_days, default=0)
    return activity_start - timedelta(days=ltd)


def _order_status(order_date: date | None, today: date) -> dict[str, object]:
    if not order_date:
        return {"kind": "UNKNOWN", "label": "—"}

    if order_date < today:
        days = max((today - order_date).days, 0)
        return {"kind": "LATE", "label": f"⚠ Late Order ({days}d)"}

    if order_date == today:
        return {"kind": "TODAY", "label": "✔ Order Today"}

    return {"kind": "UPCOMING", "label": f"⏳ Order on {format_date_ddmmyyyy(order_date)}"}


@router.get("/", response_class=HTMLResponse)
def amp_project_select(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    if not _can_plan(user):
        return RedirectResponse("/dashboard", status_code=302)

    projects = _visible_projects(db, user)
    return templates.TemplateResponse(
        "activity_material_planning_select.html",
        {
            "request": request,
            "user": user,
            "projects": projects,
        },
    )


@router.get("/{project_id}", response_class=HTMLResponse)
def amp_page(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    if not _can_plan(user):
        return RedirectResponse("/dashboard", status_code=302)

    project_ids = {int(p.id) for p in _visible_projects(db, user)}
    if int(project_id) not in project_ids:
        flash(request, "Project not found or access denied", "error")
        return RedirectResponse("/dashboard", status_code=302)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return RedirectResponse("/dashboard", status_code=302)

    activities = (
        db.query(Activity)
        .filter(
            Activity.project_id == project_id,
            Activity.is_active == True,  # noqa: E712
        )
        .order_by(Activity.id)
        .all()
    )

    pa_rows = db.query(ProjectActivity).filter(ProjectActivity.project_id == project_id).all()
    planned_map = {int(pa.activity_id): pa for pa in pa_rows}

    progress_rows = (
        db.query(ActivityProgress)
        .filter(ActivityProgress.project_id == int(project_id))
        .all()
    )
    progress_by_activity_id = {int(p.activity_id): int(p.progress_percent or 0) for p in progress_rows}

    materials_active = (
        db.query(Material)
        .filter(Material.is_active == True)  # noqa: E712
        .order_by(Material.name.asc())
        .all()
    )

    vendor_counts = {
        int(mid): int(cnt)
        for (mid, cnt) in (
            db.query(MaterialVendor.material_id, func.count(MaterialVendor.id))
            .filter(MaterialVendor.is_active == True)  # noqa: E712
            .group_by(MaterialVendor.material_id)
            .all()
        )
    }

    vendor_rows = db.query(MaterialVendor).order_by(MaterialVendor.is_active.desc(), MaterialVendor.vendor_name.asc()).all()
    vendors_by_material_json: dict[str, list[dict[str, object]]] = {}
    for v in vendor_rows:
        vendors_by_material_json.setdefault(str(int(v.material_id)), []).append(
            {
                "id": int(v.id),
                "vendor_name": str(v.vendor_name or ""),
                "lead_time_days": int(v.lead_time_days or 0),
                "is_active": bool(v.is_active),
            }
        )

    # Material stock per project
    stock_rows = db.query(MaterialStock).filter(MaterialStock.project_id == project_id).all()
    stock_by_material_id = {int(s.material_id): s for s in stock_rows}

    # Existing activity-material mappings
    mappings = (
        db.query(ActivityMaterial, Activity, Material, MaterialVendor)
        .join(Activity, Activity.id == ActivityMaterial.activity_id)
        .join(Material, Material.id == ActivityMaterial.material_id)
        .outerjoin(MaterialVendor, MaterialVendor.id == ActivityMaterial.vendor_id)
        .filter(
            Activity.project_id == project_id,
            Activity.is_active == True,  # noqa: E712
        )
        .order_by(Activity.id.asc(), Material.name.asc())
        .all()
    )

    today = date.today()
    planned_qty_by_activity_id = {int(pa.activity_id): float(pa.planned_quantity or 0.0) for pa in pa_rows}

    activity_material_rows_by_activity_id: dict[int, list[dict[str, object]]] = {}
    for am, act, mat, vendor in mappings:
        activity_start = getattr(planned_map.get(int(act.id)), "start_date", None)

        vendor_lead = int(getattr(vendor, "lead_time_days", 0) or 0) if vendor else None
        effective_lead = resolve_effective_lead_time_days(
            lead_time_days_override=getattr(am, "lead_time_days_override", None),
            vendor_lead_time_days=vendor_lead,
            material_default_lead_time_days=getattr(mat, "default_lead_time_days", None),
            material_legacy_lead_time_days=getattr(mat, "lead_time_days", None),
        )

        planned_qty = float(planned_qty_by_activity_id.get(int(act.id), 0.0) or 0.0)
        required_qty = planned_qty * float(getattr(am, "consumption_rate", 0.0) or 0.0)

        stock = stock_by_material_id.get(int(mat.id))
        available = float(getattr(stock, "quantity_available", 0.0) or 0.0) if stock else 0.0
        reorder_hint = compute_reorder_suggestion(
            available_qty=available,
            required_qty=required_qty,
            unit_label=(mat.unit or None),
        )

        order_date_suggested = _compute_order_date(activity_start, effective_lead)
        order_status = _order_status(order_date_suggested, today=today)

        activity_material_rows_by_activity_id.setdefault(int(act.id), []).append(
            {
                "id": int(am.id),
                "material_id": int(mat.id),
                "material": str(mat.name or ""),
                "unit": str(mat.unit or ""),
                "vendor_id": int(getattr(am, "vendor_id", 0) or 0) or None,
                "vendor_name": getattr(vendor, "vendor_name", None) if vendor else None,
                "lead_time_days": int(effective_lead or 0),
                "required_qty": float(required_qty or 0.0),
                "available_qty": float(available or 0.0),
                "reorder_hint": reorder_hint,
                "order_date_suggested": order_date_suggested,
                "order_status": order_status,
            }
        )

    # Materials shown in UI dropdown + JSON:
    # - active materials
    # - plus any archived materials already linked to this project (so existing plans remain viewable/editable)
    materials_for_ui_by_id: dict[int, Material] = {int(m.id): m for m in materials_active}
    for _am, _act, mat, _vendor in mappings:
        materials_for_ui_by_id.setdefault(int(mat.id), mat)
    materials_for_ui = sorted(
        materials_for_ui_by_id.values(),
        key=lambda m: (str(getattr(m, "name", "") or "").lower(), int(getattr(m, "id", 0) or 0)),
    )

    # Time planning baseline (hours stored, days/hours displayed)
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

        if du == "days":
            display_val = round((base_hours / hpd) if hpd else 0.0, 3)
        else:
            display_val = round(base_hours, 3)
        time_plan_display_by_activity_id[aid] = display_val

    # JSON maps for Configure panel (UI-only helpers)
    materials_by_id_json: dict[str, dict[str, object]] = {}
    for m in materials_for_ui:
        default_lt = getattr(m, "default_lead_time_days", None)
        if default_lt is None:
            default_lt = getattr(m, "lead_time_days", None)
        materials_by_id_json[str(int(m.id))] = {
            "id": int(m.id),
            "code": str(getattr(m, "code", "") or ""),
            "name": str(getattr(m, "name", "") or ""),
            "unit": str(getattr(m, "unit", "") or ""),
            "default_lead_time_days": int(default_lt or 0),
            "is_active": bool(getattr(m, "is_active", True)),
        }

    activity_data_by_id_json: dict[str, dict[str, object]] = {}
    for a in activities:
        aid = int(a.id)
        pa = planned_map.get(aid)
        progress_pct = int(progress_by_activity_id.get(aid, 0) or 0)
        planning_locked = progress_pct > 0
        activity_data_by_id_json[str(aid)] = {
            "id": aid,
            "code": str(getattr(a, "code", "") or ""),
            "name": str(getattr(a, "name", "") or ""),
            "start_date": (pa.start_date.isoformat() if pa and getattr(pa, "start_date", None) else ""),
            "end_date": (pa.end_date.isoformat() if pa and getattr(pa, "end_date", None) else ""),
            "planned_quantity": (float(pa.planned_quantity) if pa and getattr(pa, "planned_quantity", None) is not None else ""),
            "unit": (str(pa.unit or "") if pa else ""),
            "planned_time_display": float(time_plan_display_by_activity_id.get(aid, 0.0) or 0.0),
            "planned_quantity_hours": float(time_plan_hours_by_activity_id.get(aid, 0.0) or 0.0),
            "display_unit": str(time_display_unit_by_activity_id.get(aid, "hours") or "hours"),
            "hours_per_day": float(time_hours_per_day_by_activity_id.get(aid, 8.0) or 8.0),
            "progress_percent": progress_pct,
            "planning_locked": bool(planning_locked),
        }

    projects = _visible_projects(db, user)

    return templates.TemplateResponse(
        "activity_material_planning.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "projects": projects,
            "activities": activities,
            "planned_map": planned_map,
            "materials_active": materials_active,
            "materials_for_ui": materials_for_ui,
            "vendor_counts": vendor_counts,
            "vendors_by_material_json": vendors_by_material_json,
            "materials_by_id_json": materials_by_id_json,
            "activity_data_by_id_json": activity_data_by_id_json,
            "activity_material_rows_by_activity_id": activity_material_rows_by_activity_id,
            "time_plan_hours_by_activity_id": time_plan_hours_by_activity_id,
            "time_plan_display_by_activity_id": time_plan_display_by_activity_id,
            "time_display_unit_by_activity_id": time_display_unit_by_activity_id,
            "time_hours_per_day_by_activity_id": time_hours_per_day_by_activity_id,
            "today": today,
        },
    )


@router.post("/activities/{activity_id}/archive")
async def amp_activity_archive(activity_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    if not _can_plan(user):
        return RedirectResponse("/dashboard", status_code=302)

    form = await request.form()
    try:
        project_id = int(form.get("project_id") or 0)
    except Exception:
        project_id = 0

    act = db.query(Activity).filter(Activity.id == int(activity_id)).first()
    if not act:
        flash(request, "Activity not found", "error")
        return RedirectResponse(f"/activity-material-planning/{project_id}" if project_id else "/activity-material-planning", status_code=302)

    if project_id and int(getattr(act, "project_id", 0) or 0) != int(project_id):
        flash(request, "Activity does not belong to this project", "error")
        return RedirectResponse(f"/activity-material-planning/{project_id}", status_code=302)

    old = model_to_dict(act)
    unlinked = 0
    try:
        # Remove all material requirement rows for this activity (project-scoped by activity_id)
        unlinked = (
            db.query(ActivityMaterial)
            .filter(ActivityMaterial.activity_id == int(activity_id))
            .delete(synchronize_session=False)
        )

        act.is_active = False
        db.add(act)
        db.commit()

        if unlinked:
            log_action(
                db=db,
                request=request,
                action="DELETE",
                entity_type="activity_material",
                entity_id=None,
                description=f"Unlinked materials from activity during archive: activity #{act.id}",
                old_value=None,
                new_value={"activity_id": int(act.id), "rows_deleted": int(unlinked)},
            )

        log_action(
            db=db,
            request=request,
            action="UPDATE",
            entity_type="activity",
            entity_id=int(act.id),
            description=f"Activity archived from merged planning page: activity #{act.id}",
            old_value={"activity": old},
            new_value={"activity": model_to_dict(act)},
        )
        if unlinked:
            flash(request, f"Activity removed (archived) and unlinked {unlinked} material requirement(s).", "success")
        else:
            flash(request, "Activity removed (archived)", "success")
    except Exception:
        db.rollback()
        flash(request, "Failed to remove activity", "error")

    return RedirectResponse(f"/activity-material-planning/{project_id}" if project_id else "/activity-material-planning", status_code=302)


@router.post("/save")
async def amp_save(
    request: Request,
    project_id: int = Form(...),
    activity_id: int = Form(...),
    planned_quantity: float = Form(...),
    unit: str = Form(...),
    planned_time_display: float = Form(...),
    planned_quantity_hours: float = Form(...),
    display_unit: str = Form("hours"),
    hours_per_day: float = Form(8.0),
    start_date: str = Form(...),
    end_date: str = Form(...),
    material_id: int | None = Form(None),
    required_qty: float | None = Form(None),
    vendor_id: int | None = Form(None),
    unlock_override: str | None = Form(None),
    unlock_reason: str | None = Form(None),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    if not _can_plan(user):
        return RedirectResponse("/dashboard", status_code=302)

    try:
        start_date_obj = parse_date_ddmmyyyy_or_iso(start_date)
        end_date_obj = parse_date_ddmmyyyy_or_iso(end_date)
    except Exception:
        flash(request, "Invalid start/end date", "error")
        return RedirectResponse(f"/activity-material-planning/{project_id}", status_code=302)

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

    if planned_hours_f <= 0 and planned_time_display_f > 0:
        planned_hours_f = float(display_to_hours(planned_time_display_f, du, hpd) or 0)

    if planned_hours_f <= 0:
        flash(request, "Planned time must be > 0", "warning")
        return RedirectResponse(f"/activity-material-planning/{project_id}", status_code=302)

    # --- Save time plan on Activity ---
    act = (
        db.query(Activity)
        .filter(
            Activity.id == activity_id,
            Activity.project_id == project_id,
        )
        .first()
    )
    if not act:
        flash(request, "Activity not found", "error")
        return RedirectResponse(f"/activity-material-planning/{project_id}", status_code=302)

    if getattr(act, "is_active", True) is False:
        flash(request, "This activity is archived and cannot be edited", "warning")
        return RedirectResponse(f"/activity-material-planning/{project_id}", status_code=302)

    progress_pct = _activity_progress_percent(db, project_id=int(project_id), activity_id=int(activity_id))
    planning_locked = progress_pct > 0
    is_admin = _is_admin(user)
    override_requested = str(unlock_override or "").strip() == "1"
    reason = str(unlock_reason or "").strip()

    if planning_locked and not is_admin:
        msg = "Planning is locked because execution has started (progress > 0). Only Admin can unlock."
        if _wants_json(request):
            return JSONResponse({"ok": False, "error": msg}, status_code=403)
        flash(request, msg, "warning")
        return RedirectResponse(f"/activity-material-planning/{project_id}", status_code=302)

    if planning_locked and is_admin:
        if not override_requested:
            msg = "Planning is locked (progress > 0). Use Admin unlock + reason to edit."
            if _wants_json(request):
                return JSONResponse({"ok": False, "error": msg}, status_code=400)
            flash(request, msg, "warning")
            return RedirectResponse(f"/activity-material-planning/{project_id}", status_code=302)

        if not reason:
            msg = "Unlock reason is required for baseline changes once execution has started."
            if _wants_json(request):
                return JSONResponse({"ok": False, "error": msg}, status_code=400)
            flash(request, msg, "warning")
            return RedirectResponse(f"/activity-material-planning/{project_id}", status_code=302)

        log_action(
            db=db,
            request=request,
            action="UNLOCK",
            entity_type="activity_plan",
            entity_id=int(activity_id),
            description=f"Admin unlocked planning for activity #{activity_id} (progress={progress_pct}%)",
            old_value={"progress_percent": int(progress_pct)},
            new_value={"unlock_reason": reason},
        )

    old_act = model_to_dict(act)

    act.planned_quantity_hours = float(planned_hours_f)
    act.display_unit = du
    act.hours_per_day = float(hpd)
    db.add(act)

    # --- Save schedule + quantity on ProjectActivity ---
    pa = (
        db.query(ProjectActivity)
        .filter(ProjectActivity.project_id == project_id, ProjectActivity.activity_id == activity_id)
        .first()
    )

    if pa:
        old_pa = model_to_dict(pa)
        pa.planned_quantity = float(planned_quantity)
        pa.unit = str(unit or "").strip()
        pa.start_date = start_date_obj
        pa.end_date = end_date_obj
        db.add(pa)
    else:
        old_pa = None
        pa = ProjectActivity(
            project_id=project_id,
            activity_id=activity_id,
            planned_quantity=float(planned_quantity),
            unit=str(unit or "").strip(),
            start_date=start_date_obj,
            end_date=end_date_obj,
        )
        db.add(pa)

    # --- Optional: material requirement upsert ---
    saved_mapping_id: int | None = None
    order = None
    order_status = None
    reorder_hint = None

    if material_id and (required_qty is not None):
        # Compute consumption_rate from required_qty / planned_quantity
        pq = float(planned_quantity or 0.0)
        rq = float(required_qty or 0.0)
        if pq <= 0:
            flash(request, "Planned quantity must be > 0 before adding material requirement", "warning")
        else:
            rate = max(rq / pq, 0.0)

            material = db.query(Material).filter(Material.id == int(material_id)).first()
            if material:
                vendor = None
                if vendor_id:
                    vendor = (
                        db.query(MaterialVendor)
                        .filter(MaterialVendor.id == int(vendor_id), MaterialVendor.material_id == int(material_id))
                        .first()
                    )
                    if not vendor:
                        vendor_id = None

                effective_lt = resolve_effective_lead_time_days(
                    lead_time_days_override=None,
                    vendor_lead_time_days=(vendor.lead_time_days if vendor else None),
                    material_default_lead_time_days=getattr(material, "default_lead_time_days", None),
                    material_legacy_lead_time_days=getattr(material, "lead_time_days", None),
                )

                order_date_suggested = _compute_order_date(start_date_obj, effective_lt)
                expected = compute_expected_delivery_date(order_date_suggested, effective_lt)

                # Upsert mapping by (activity_id, material_id)
                mapping = (
                    db.query(ActivityMaterial)
                    .filter(ActivityMaterial.activity_id == activity_id, ActivityMaterial.material_id == int(material_id))
                    .first()
                )

                if mapping:
                    old_map = model_to_dict(mapping)
                    mapping.consumption_rate = float(rate)
                    mapping.vendor_id = int(vendor_id) if vendor_id else None
                    mapping.lead_time_days_override = None
                    # Preserve manual order_date if already set, else use suggestion.
                    mapping.order_date = mapping.order_date or order_date_suggested
                    mapping.lead_time_days = int(effective_lt or 0)
                    mapping.expected_delivery_date = expected
                    mapping.is_material_risk = False
                    mapping.updated_at = datetime.utcnow()
                    db.add(mapping)
                    log_action(
                        db=db,
                        request=request,
                        action="UPDATE",
                        entity_type="activity_material",
                        entity_id=mapping.id,
                        description=f"Activity-material updated from unified planning page: mapping #{mapping.id}",
                        old_value={"mapping": old_map},
                        new_value={"mapping": model_to_dict(mapping)},
                    )
                else:
                    mapping = ActivityMaterial(
                        activity_id=activity_id,
                        material_id=int(material_id),
                        consumption_rate=float(rate),
                        vendor_id=int(vendor_id) if vendor_id else None,
                        order_date=order_date_suggested,
                        lead_time_days_override=None,
                        lead_time_days=int(effective_lt or 0),
                        expected_delivery_date=expected,
                        is_material_risk=False,
                        updated_at=datetime.utcnow(),
                        created_at=datetime.utcnow(),
                    )
                    db.add(mapping)

                saved_mapping_id = int(getattr(mapping, "id", 0) or 0) or None

                # Stock / reorder hint
                stock = (
                    db.query(MaterialStock)
                    .filter(MaterialStock.project_id == project_id, MaterialStock.material_id == int(material_id))
                    .first()
                )
                available = float(getattr(stock, "quantity_available", 0.0) or 0.0) if stock else 0.0
                reorder_hint = compute_reorder_suggestion(
                    available_qty=available,
                    required_qty=rq,
                    unit_label=(material.unit or None),
                )

                order = order_date_suggested
                order_status = _order_status(order_date_suggested, today=date.today())

    db.commit()

    log_action(
        db=db,
        request=request,
        action="UPDATE",
        entity_type="ProjectActivity",
        entity_id=getattr(pa, "id", None),
        description=f"Activity plan saved from unified planning page: activity #{activity_id}",
        old_value={"activity": old_act, "project_activity": old_pa},
        new_value={"activity": model_to_dict(act), "project_activity": model_to_dict(pa)},
    )

    if _wants_json(request):
        return JSONResponse(
            {
                "ok": True,
                "project_id": int(project_id),
                "activity_id": int(activity_id),
                "mapping_id": saved_mapping_id,
                "order_date": format_date_ddmmyyyy(order) if order else None,
                "order_status": order_status,
                "reorder_hint": reorder_hint,
            }
        )

    flash(request, "Saved", "success")
    return RedirectResponse(f"/activity-material-planning/{project_id}", status_code=302)
