from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.material import Material
from app.models.material_vendor import MaterialVendor
from app.models.activity_material import ActivityMaterial
from app.models.activity import Activity
from app.models.project_activity import ProjectActivity
from app.utils.material_lead_time import (
    compute_expected_delivery_date,
    evaluate_delivery_risk,
    resolve_effective_lead_time_days,
)
from app.utils.audit_logger import log_action, model_to_dict
from app.utils.flash import flash
from app.utils.id_codes import generate_next_code

router = APIRouter(prefix="/material-master", tags=["Material Master"])
templates = Jinja2Templates(directory="app/templates")


def _guard_master_editor(request: Request) -> dict | None:
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return None

    # Lead time + vendor management: Admin/Manager only
    if user.get("role") not in ["admin", "manager"]:
        flash(request, "Admin/Manager access required", "warning")
        return None

    return user


@router.get("/materials", response_class=HTMLResponse)
def material_master_page(request: Request, db: Session = Depends(get_db)):
    user = _guard_master_editor(request)
    if not user:
        return RedirectResponse("/dashboard", status_code=302)

    # Legacy full-page view removed in favor of merged screen
    return RedirectResponse("/activity-material-planning", status_code=302)


@router.post("/materials/update")
async def material_master_update(request: Request, db: Session = Depends(get_db)):
    user = _guard_master_editor(request)
    if not user:
        return RedirectResponse("/dashboard", status_code=302)

    form = await request.form()

    project_id = str(form.get("project_id") or "").strip()

    try:
        material_id = int(form.get("material_id") or 0)
    except Exception:
        material_id = 0

    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        flash(request, "Material not found", "error")
        return RedirectResponse("/activity-material-planning", status_code=302)

    old = model_to_dict(m)

    raw = (form.get("default_lead_time_days") or "").strip()
    default_lt = None
    if raw != "":
        try:
            default_lt = int(float(raw))
        except Exception:
            default_lt = None

    if default_lt is not None and default_lt < 0:
        default_lt = 0

    m.default_lead_time_days = default_lt
    db.add(m)
    db.commit()

    # Recalculate future activity-material rows that inherit from material default (no vendor, no override)
    today = date.today()
    touched = 0
    try:
        rows = (
            db.query(ActivityMaterial, ProjectActivity)
            .join(ProjectActivity, ProjectActivity.activity_id == ActivityMaterial.activity_id)
            .filter(
                ActivityMaterial.material_id == m.id,
                ActivityMaterial.vendor_id.is_(None),
                ActivityMaterial.lead_time_days_override.is_(None),
                ProjectActivity.start_date >= today,
            )
            .all()
        )
        for am, pa in rows:
            effective_lt = resolve_effective_lead_time_days(
                lead_time_days_override=None,
                vendor_lead_time_days=None,
                material_default_lead_time_days=getattr(m, "default_lead_time_days", None),
                material_legacy_lead_time_days=getattr(m, "lead_time_days", None),
            )
            expected = compute_expected_delivery_date(getattr(am, "order_date", None), effective_lt)
            check = evaluate_delivery_risk(
                activity_start_date=getattr(pa, "start_date", None),
                order_date=getattr(am, "order_date", None),
                expected_delivery_date=expected,
                today=today,
            )
            am.lead_time_days = int(effective_lt or 0)
            am.expected_delivery_date = check.expected_delivery_date
            am.is_material_risk = bool(check.is_risk)
            am.updated_at = datetime.utcnow()
            db.add(am)
            touched += 1

        if touched:
            db.commit()
    except Exception:
        db.rollback()

    log_action(
        db=db,
        request=request,
        action="UPDATE",
        entity_type="material",
        entity_id=m.id,
        description=f"Material default lead time updated: material #{m.id}",
        old_value={"material": old},
        new_value={"material": model_to_dict(m)},
    )

    if touched:
        log_action(
            db=db,
            request=request,
            action="UPDATE",
            entity_type="activity_material",
            entity_id=None,
            description=f"Recalculated lead time for future activity-material rows after material default update: material #{m.id}",
            old_value=None,
            new_value={"material_id": m.id, "rows_updated": touched},
        )

    flash(request, "Material updated", "success")
    return RedirectResponse(
        f"/activity-material-planning/{project_id}" if project_id else "/activity-material-planning",
        status_code=302,
    )


@router.post("/materials/create")
async def material_master_create(request: Request, db: Session = Depends(get_db)):
    user = _guard_master_editor(request)
    if not user:
        return RedirectResponse("/dashboard", status_code=302)

    form = await request.form()
    project_id = str(form.get("project_id") or "").strip()

    name = str(form.get("name") or "").strip()
    unit = str(form.get("unit") or "").strip()
    category = str(form.get("category") or "").strip() or None

    raw_lt = str(form.get("default_lead_time_days") or "").strip()
    default_lt: int | None = None
    if raw_lt != "":
        try:
            default_lt = int(float(raw_lt))
        except Exception:
            default_lt = None
    if default_lt is not None and default_lt < 0:
        default_lt = 0

    if not name or not unit:
        flash(request, "Material name and unit are required.", "warning")
        return RedirectResponse(
            f"/activity-material-planning/{project_id}" if project_id else "/activity-material-planning",
            status_code=302,
        )

    # Prevent duplicates (name is unique)
    existing = db.query(Material).filter(func.lower(Material.name) == name.lower()).first()
    if existing:
        # If it exists but is inactive, reactivate it.
        try:
            if getattr(existing, "is_active", True) is False:
                existing.is_active = True
                existing.unit = unit
                existing.category = category
                existing.default_lead_time_days = default_lt
                if default_lt is not None:
                    existing.lead_time_days = int(default_lt)
                db.add(existing)
                db.commit()
                flash(request, "Material re-activated.", "success")
            else:
                flash(request, "Material already exists.", "warning")
        except Exception:
            db.rollback()
            flash(request, "Failed to create material.", "error")
        return RedirectResponse(
            f"/activity-material-planning/{project_id}" if project_id else "/activity-material-planning",
            status_code=302,
        )

    try:
        m = Material(
            name=name,
            unit=unit,
            category=category,
            default_lead_time_days=default_lt,
            lead_time_days=int(default_lt or 0),
            minimum_stock=0,
            is_active=True,
        )
        m.code = generate_next_code(db, Material, code_attr="code", prefix="MAT", width=6)
        db.add(m)
        db.commit()
        db.refresh(m)
        log_action(
            db=db,
            request=request,
            action="CREATE",
            entity_type="Material",
            entity_id=m.id,
            description=f"Material created from merged planning page: {m.name}",
            old_value=None,
            new_value=model_to_dict(m),
        )
        flash(request, "Material added.", "success")
    except Exception:
        db.rollback()
        flash(request, "Failed to create material (duplicate or DB constraint).", "error")

    return RedirectResponse(
        f"/activity-material-planning/{project_id}" if project_id else "/activity-material-planning",
        status_code=302,
    )


@router.post("/materials/{material_id}/archive")
async def material_master_archive(material_id: int, request: Request, db: Session = Depends(get_db)):
    user = _guard_master_editor(request)
    if not user:
        return RedirectResponse("/dashboard", status_code=302)

    form = await request.form()
    project_id_str = str(form.get("project_id") or "").strip()
    try:
        project_id = int(project_id_str) if project_id_str else 0
    except Exception:
        project_id = 0

    m = db.query(Material).filter(Material.id == int(material_id)).first()
    if not m:
        flash(request, "Material not found.", "error")
        return RedirectResponse(
            f"/activity-material-planning/{project_id}" if project_id else "/activity-material-planning",
            status_code=302,
        )

    old = model_to_dict(m)
    unlinked = 0
    try:
        # If called from the merged project page, also remove all activity-material rows
        # for this project so the archived material stops appearing as "in use".
        if project_id > 0:
            activity_ids = [
                int(aid)
                for (aid,) in (
                    db.query(Activity.id)
                    .filter(Activity.project_id == project_id)
                    .all()
                )
            ]

            if activity_ids:
                # Bulk delete mapping rows for those activities.
                unlinked = (
                    db.query(ActivityMaterial)
                    .filter(
                        ActivityMaterial.material_id == int(material_id),
                        ActivityMaterial.activity_id.in_(activity_ids),
                    )
                    .delete(synchronize_session=False)
                )

        m.is_active = False
        db.add(m)
        db.commit()

        if unlinked:
            log_action(
                db=db,
                request=request,
                action="DELETE",
                entity_type="activity_material",
                entity_id=None,
                description=f"Unlinked material from project activities during archive: material #{m.id} project #{project_id}",
                old_value=None,
                new_value={"material_id": int(m.id), "project_id": int(project_id), "rows_deleted": int(unlinked)},
            )

        log_action(
            db=db,
            request=request,
            action="UPDATE",
            entity_type="Material",
            entity_id=m.id,
            description=f"Material archived from merged planning page: {m.name}",
            old_value=old,
            new_value=model_to_dict(m),
        )
        if project_id > 0 and unlinked:
            flash(request, f"Material removed (archived) and unlinked from {unlinked} activity requirement(s).", "success")
        else:
            flash(request, "Material removed (archived).", "success")
    except Exception:
        db.rollback()
        flash(request, "Failed to remove material.", "error")

    return RedirectResponse(
        f"/activity-material-planning/{project_id}" if project_id else "/activity-material-planning",
        status_code=302,
    )


@router.get("/materials/{material_id}/vendors", response_class=HTMLResponse)
def material_vendors_page(material_id: int, request: Request, db: Session = Depends(get_db)):
    user = _guard_master_editor(request)
    if not user:
        return RedirectResponse("/dashboard", status_code=302)

    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        flash(request, "Material not found", "error")
        return RedirectResponse("/activity-material-planning", status_code=302)

    vendors = (
        db.query(MaterialVendor)
        .filter(MaterialVendor.material_id == material_id)
        .order_by(MaterialVendor.is_active.desc(), MaterialVendor.vendor_name.asc())
        .all()
    )

    return templates.TemplateResponse(
        "material_vendors.html",
        {
            "request": request,
            "user": user,
            "material": m,
            "vendors": vendors,
            "today": date.today(),
        },
    )


@router.post("/materials/{material_id}/vendors/add")
async def material_vendor_add(material_id: int, request: Request, db: Session = Depends(get_db)):
    user = _guard_master_editor(request)
    if not user:
        return RedirectResponse("/dashboard", status_code=302)

    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        flash(request, "Material not found", "error")
        return RedirectResponse("/activity-material-planning", status_code=302)

    form = await request.form()

    vendor_name = str(form.get("vendor_name") or "").strip()[:200]
    if not vendor_name:
        flash(request, "Vendor name is required", "error")
        return RedirectResponse(f"/material-master/materials/{material_id}/vendors", status_code=302)

    try:
        lead_time_days = int(float(str(form.get("lead_time_days") or "0").strip() or 0))
    except Exception:
        lead_time_days = 0
    if lead_time_days < 0:
        lead_time_days = 0

    cp = str(form.get("contact_person") or "").strip()[:150] or None
    phone = str(form.get("phone") or "").strip()[:50] or None
    email = str(form.get("email") or "").strip()[:200] or None

    min_order_qty = None
    moq_raw = str(form.get("min_order_qty") or "").strip()
    if moq_raw:
        try:
            min_order_qty = float(moq_raw)
        except Exception:
            min_order_qty = None

    v = MaterialVendor(
        material_id=material_id,
        vendor_name=vendor_name,
        contact_person=cp,
        phone=phone,
        email=email,
        lead_time_days=lead_time_days,
        min_order_qty=min_order_qty,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(v)
    db.commit()
    db.refresh(v)

    log_action(
        db=db,
        request=request,
        action="CREATE",
        entity_type="vendor",
        entity_id=v.id,
        description=f"Vendor added: material #{material_id} vendor #{v.id}",
        old_value=None,
        new_value={"vendor": model_to_dict(v)},
    )

    flash(request, "Vendor added", "success")
    return RedirectResponse(f"/material-master/materials/{material_id}/vendors", status_code=302)


@router.post("/vendors/{vendor_id}/update")
async def material_vendor_update(vendor_id: int, request: Request, db: Session = Depends(get_db)):
    user = _guard_master_editor(request)
    if not user:
        return RedirectResponse("/dashboard", status_code=302)

    v = db.query(MaterialVendor).filter(MaterialVendor.id == vendor_id).first()
    if not v:
        flash(request, "Vendor not found", "error")
        return RedirectResponse("/activity-material-planning", status_code=302)

    old = model_to_dict(v)

    form = await request.form()

    vendor_name = str(form.get("vendor_name") or "").strip()[:200]
    if vendor_name:
        v.vendor_name = vendor_name

    cp = str(form.get("contact_person") or "").strip()[:150]
    v.contact_person = cp or None

    phone = str(form.get("phone") or "").strip()[:50]
    v.phone = phone or None

    email = str(form.get("email") or "").strip()[:200]
    v.email = email or None

    try:
        lead_time_days = int(float(str(form.get("lead_time_days") or "0").strip() or 0))
    except Exception:
        lead_time_days = 0
    if lead_time_days < 0:
        lead_time_days = 0
    v.lead_time_days = lead_time_days

    moq_raw = str(form.get("min_order_qty") or "").strip()
    if moq_raw:
        try:
            v.min_order_qty = float(moq_raw)
        except Exception:
            v.min_order_qty = None
    else:
        v.min_order_qty = None

    v.updated_at = datetime.utcnow()
    db.add(v)
    db.commit()

    # Recalculate future activity-material rows that inherit from this vendor (no override)
    today = date.today()
    touched = 0
    try:
        rows = (
            db.query(ActivityMaterial, ProjectActivity, Material)
            .join(ProjectActivity, ProjectActivity.activity_id == ActivityMaterial.activity_id)
            .join(Material, Material.id == ActivityMaterial.material_id)
            .filter(
                ActivityMaterial.vendor_id == v.id,
                ActivityMaterial.lead_time_days_override.is_(None),
                ProjectActivity.start_date >= today,
            )
            .all()
        )
        for am, pa, mat in rows:
            effective_lt = resolve_effective_lead_time_days(
                lead_time_days_override=None,
                vendor_lead_time_days=int(v.lead_time_days or 0),
                material_default_lead_time_days=getattr(mat, "default_lead_time_days", None),
                material_legacy_lead_time_days=getattr(mat, "lead_time_days", None),
            )
            expected = compute_expected_delivery_date(getattr(am, "order_date", None), effective_lt)
            check = evaluate_delivery_risk(
                activity_start_date=getattr(pa, "start_date", None),
                order_date=getattr(am, "order_date", None),
                expected_delivery_date=expected,
                today=today,
            )
            am.lead_time_days = int(effective_lt or 0)
            am.expected_delivery_date = check.expected_delivery_date
            am.is_material_risk = bool(check.is_risk)
            am.updated_at = datetime.utcnow()
            db.add(am)
            touched += 1

        if touched:
            db.commit()
    except Exception:
        db.rollback()

    log_action(
        db=db,
        request=request,
        action="UPDATE",
        entity_type="vendor",
        entity_id=v.id,
        description=f"Vendor updated: vendor #{v.id}",
        old_value={"vendor": old},
        new_value={"vendor": model_to_dict(v)},
    )

    if touched:
        log_action(
            db=db,
            request=request,
            action="UPDATE",
            entity_type="activity_material",
            entity_id=None,
            description=f"Recalculated lead time for future activity-material rows after vendor update: vendor #{v.id}",
            old_value=None,
            new_value={"vendor_id": v.id, "rows_updated": touched},
        )

    flash(request, "Vendor updated", "success")
    return RedirectResponse(f"/material-master/materials/{int(v.material_id)}/vendors", status_code=302)


@router.post("/vendors/{vendor_id}/toggle")
async def material_vendor_toggle(vendor_id: int, request: Request, db: Session = Depends(get_db)):
    user = _guard_master_editor(request)
    if not user:
        return RedirectResponse("/dashboard", status_code=302)

    v = db.query(MaterialVendor).filter(MaterialVendor.id == vendor_id).first()
    if not v:
        flash(request, "Vendor not found", "error")
        return RedirectResponse("/activity-material-planning", status_code=302)

    old = model_to_dict(v)
    v.is_active = not bool(v.is_active)
    v.updated_at = datetime.utcnow()

    db.add(v)
    db.commit()

    log_action(
        db=db,
        request=request,
        action="UPDATE",
        entity_type="vendor",
        entity_id=v.id,
        description=f"Vendor {'enabled' if v.is_active else 'disabled'}: vendor #{v.id}",
        old_value={"vendor": old},
        new_value={"vendor": model_to_dict(v)},
    )

    flash(request, "Vendor status updated", "success")
    return RedirectResponse(f"/material-master/materials/{int(v.material_id)}/vendors", status_code=302)



# --- AJAX endpoint for adding vendor from procurement (returns JSON) ---
from fastapi.responses import JSONResponse

@router.post("/materials/add-vendor-from-procurement")
async def add_vendor_from_procurement(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user or user.get("role") not in ["admin", "manager", "superadmin"]:
        return JSONResponse({"error": "Admin/Manager access required"}, status_code=403)

    form = await request.form()
    material_id = int(form.get("material_id") or 0)
    vendor_name = str(form.get("vendor_name") or "").strip()[:200]
    lead_time_days = int(form.get("lead_time_days") or 0)
    contact_person = str(form.get("contact_person") or "").strip()[:150] or None
    phone = str(form.get("phone") or "").strip()[:50] or None
    email = str(form.get("email") or "").strip()[:200] or None
    min_order_qty = form.get("min_order_qty")
    min_order_qty = float(min_order_qty) if min_order_qty else None

    if not material_id or not vendor_name:
        return JSONResponse({"error": "Material and Vendor Name are required"}, status_code=400)

    v = MaterialVendor(
        material_id=material_id,
        vendor_name=vendor_name,
        contact_person=contact_person,
        phone=phone,
        email=email,
        lead_time_days=lead_time_days,
        min_order_qty=min_order_qty,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return JSONResponse({"success": True, "vendor_id": v.id})
