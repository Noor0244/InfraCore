from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.road_preset import RoadPreset
from app.services.admin_preset_service import (
    apply_preset_update,
    clone_preset,
    preset_is_linked_to_active_projects,
    reset_preset_to_seed,
    serialize_preset,
    soft_delete_preset,
)
from app.utils.audit_logger import log_action
from app.utils.flash import flash

router = APIRouter(prefix="/admin/presets", tags=["Admin Presets"])
templates = Jinja2Templates(directory="app/templates")


def _admin_guard(request: Request):
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        flash(request, "Admin access required", "warning")
        return None
    return user


@router.get("/road", response_class=HTMLResponse)
def road_presets_dashboard(
    request: Request,
    q: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    admin = _admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    query = db.query(RoadPreset).filter(getattr(RoadPreset, "is_deleted", False) == False)  # noqa: E712

    if status == "active":
        query = query.filter(RoadPreset.is_active == True)  # noqa: E712
    elif status == "disabled":
        query = query.filter(RoadPreset.is_active == False)  # noqa: E712

    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            (RoadPreset.preset_key.ilike(term))
            | (RoadPreset.title.ilike(term))
            | (RoadPreset.road_category.ilike(term))
            | (RoadPreset.road_engineering_type.ilike(term))
        )

    presets = query.order_by(RoadPreset.updated_at.desc()).all()

    return templates.TemplateResponse(
        "admin/road_presets_list.html",
        {"request": request, "user": admin, "presets": presets, "filters": {"q": q or "", "status": status or ""}},
    )


@router.get("/road/{preset_id}", response_class=HTMLResponse)
def road_preset_view(preset_id: int, request: Request, db: Session = Depends(get_db)):
    admin = _admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    data = serialize_preset(db, preset_id=preset_id)
    if not data:
        flash(request, "Preset not found", "error")
        return RedirectResponse("/admin/presets/road", status_code=302)

    linked = preset_is_linked_to_active_projects(db, preset_key=str(data["preset"]["preset_key"]))

    return templates.TemplateResponse(
        "admin/road_preset_view.html",
        {"request": request, "user": admin, "data": data, "linked": linked},
    )


@router.get("/road/{preset_id}/edit", response_class=HTMLResponse)
def road_preset_edit(preset_id: int, request: Request, db: Session = Depends(get_db)):
    admin = _admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    data = serialize_preset(db, preset_id=preset_id)
    if not data:
        flash(request, "Preset not found", "error")
        return RedirectResponse("/admin/presets/road", status_code=302)

    return templates.TemplateResponse(
        "admin/road_preset_edit.html",
        {"request": request, "user": admin, "data": data},
    )


@router.post("/road/{preset_id}/update")
def road_preset_update(
    preset_id: int,
    request: Request,
    payload_json: str = Form(...),
    db: Session = Depends(get_db),
):
    admin = _admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    before = serialize_preset(db, preset_id=preset_id)
    if not before:
        flash(request, "Preset not found", "error")
        return RedirectResponse("/admin/presets/road", status_code=302)

    try:
        payload = json.loads(payload_json)
        if not isinstance(payload, dict):
            raise ValueError("Invalid payload")

        apply_preset_update(db, preset_id=preset_id, payload=payload)
        db.commit()

        after = serialize_preset(db, preset_id=preset_id)
        log_action(
            db=db,
            request=request,
            action="UPDATE",
            entity_type="RoadPreset",
            entity_id=preset_id,
            description=f"Updated road preset {before['preset']['preset_key']}",
            old_value=before,
            new_value=after,
        )

        flash(request, "Preset updated successfully", "success")
        return RedirectResponse(f"/admin/presets/road/{preset_id}", status_code=302)

    except Exception as exc:
        db.rollback()
        flash(request, f"Update failed: {exc}", "error")
        return RedirectResponse(f"/admin/presets/road/{preset_id}/edit", status_code=302)


@router.post("/road/{preset_id}/toggle")
def road_preset_toggle(preset_id: int, request: Request, db: Session = Depends(get_db)):
    admin = _admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    preset = db.query(RoadPreset).filter(RoadPreset.id == preset_id).first()
    if not preset or getattr(preset, "is_deleted", False):
        flash(request, "Preset not found", "error")
        return RedirectResponse("/admin/presets/road", status_code=302)

    before = {"is_active": bool(preset.is_active)}
    preset.is_active = not bool(preset.is_active)
    db.add(preset)
    db.commit()

    log_action(
        db=db,
        request=request,
        action="UPDATE",
        entity_type="RoadPreset",
        entity_id=preset_id,
        description=f"Preset {'enabled' if preset.is_active else 'disabled'}: {preset.preset_key}",
        old_value=before,
        new_value={"is_active": bool(preset.is_active)},
    )

    flash(request, f"Preset {'enabled' if preset.is_active else 'disabled'}", "success")
    return RedirectResponse("/admin/presets/road", status_code=302)


@router.get("/road/{preset_id}/clone", response_class=HTMLResponse)
def road_preset_clone_form(preset_id: int, request: Request, db: Session = Depends(get_db)):
    admin = _admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    data = serialize_preset(db, preset_id=preset_id)
    if not data:
        flash(request, "Preset not found", "error")
        return RedirectResponse("/admin/presets/road", status_code=302)

    return templates.TemplateResponse(
        "admin/road_preset_clone.html",
        {"request": request, "user": admin, "data": data},
    )


@router.post("/road/{preset_id}/clone")
def road_preset_clone_do(
    preset_id: int,
    request: Request,
    new_title: str | None = Form(None),
    db: Session = Depends(get_db),
):
    admin = _admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    before = serialize_preset(db, preset_id=preset_id)
    if not before:
        flash(request, "Preset not found", "error")
        return RedirectResponse("/admin/presets/road", status_code=302)

    try:
        cloned = clone_preset(db, preset_id=preset_id, new_title=new_title)
        db.commit()

        log_action(
            db=db,
            request=request,
            action="CREATE",
            entity_type="RoadPreset",
            entity_id=cloned.id,
            description=f"Cloned preset {before['preset']['preset_key']} -> {cloned.preset_key}",
            old_value=before,
            new_value={"preset_key": cloned.preset_key, "id": cloned.id},
        )

        flash(request, "Preset cloned successfully", "success")
        return RedirectResponse(f"/admin/presets/road/{cloned.id}", status_code=302)

    except Exception as exc:
        db.rollback()
        flash(request, f"Clone failed: {exc}", "error")
        return RedirectResponse(f"/admin/presets/road/{preset_id}", status_code=302)


@router.post("/road/{preset_id}/reset")
def road_preset_reset(preset_id: int, request: Request, db: Session = Depends(get_db)):
    admin = _admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    data = serialize_preset(db, preset_id=preset_id)
    if not data:
        flash(request, "Preset not found", "error")
        return RedirectResponse("/admin/presets/road", status_code=302)

    preset_key = str(data["preset"]["preset_key"])

    try:
        before = data
        reset_preset_to_seed(db, preset_key=preset_key)
        db.commit()
        after = serialize_preset(db, preset_id=preset_id)

        log_action(
            db=db,
            request=request,
            action="UPDATE",
            entity_type="RoadPreset",
            entity_id=preset_id,
            description=f"Reset preset to default seed: {preset_key}",
            old_value=before,
            new_value=after,
        )

        flash(request, "Preset reset to default seed", "success")
        return RedirectResponse(f"/admin/presets/road/{preset_id}", status_code=302)

    except Exception as exc:
        db.rollback()
        flash(request, f"Reset failed: {exc}", "error")
        return RedirectResponse(f"/admin/presets/road/{preset_id}", status_code=302)


@router.post("/road/{preset_id}/delete")
def road_preset_delete(preset_id: int, request: Request, db: Session = Depends(get_db)):
    admin = _admin_guard(request)
    if not admin:
        return RedirectResponse("/dashboard", status_code=302)

    before = serialize_preset(db, preset_id=preset_id)
    if not before:
        flash(request, "Preset not found", "error")
        return RedirectResponse("/admin/presets/road", status_code=302)

    try:
        soft_delete_preset(db, preset_id=preset_id)
        db.commit()

        log_action(
            db=db,
            request=request,
            action="DELETE",
            entity_type="RoadPreset",
            entity_id=preset_id,
            description=f"Soft-deleted preset {before['preset']['preset_key']}",
            old_value=before,
            new_value={"is_deleted": True, "is_active": False},
        )

        flash(request, "Preset deleted (soft)", "success")
        return RedirectResponse("/admin/presets/road", status_code=302)

    except Exception as exc:
        db.rollback()
        flash(request, f"Delete failed: {exc}", "error")
        return RedirectResponse(f"/admin/presets/road/{preset_id}", status_code=302)
