from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.road_preset import PresetActivity, PresetActivityMaterialMap, PresetMaterial, RoadPreset
from app.services.project_wizard_service import create_wizard, get_state, update_state, deactivate
from app.utils.flash import flash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/wizard", tags=["Project Wizard"])
templates = Jinja2Templates(directory="app/templates")


def _require_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise PermissionError("login")
    return user


def _redirect_login(request: Request) -> RedirectResponse:
    flash(request, "Please login to continue", "warning")
    return RedirectResponse("/login", status_code=302)


def _wizard_or_redirect(request: Request, db: Session, wizard_id: int, user_id: int):
    state = get_state(db, wizard_id=wizard_id, user_id=user_id)
    if not state:
        flash(request, "Wizard session expired. Please start again.", "warning")
        return None
    return state


def _display_preset_name(p: RoadPreset) -> str:
    cat = (p.road_category or "").strip() or "Road"
    eng = (p.engineering_type or "").strip() or (p.road_engineering_type or "").split("–")[0].strip() or "Engineering"
    con = (p.construction_type or "").strip() or ""
    tail = f" – {con}" if con else ""
    return f"{cat} – {eng}{tail}"


@router.get("/start", response_class=HTMLResponse)
def wizard_step0_get(request: Request, wid: int | None = None, db: Session = Depends(get_db)):
    try:
        user = _require_user(request)
    except PermissionError:
        return _redirect_login(request)

    state = None
    if wid:
        state = _wizard_or_redirect(request, db, wid, int(user["id"]))

    data = state.data if state else {}
    return templates.TemplateResponse(
        "projects/wizard/step0_basic.html",
        {"request": request, "user": user, "wid": wid, "data": data},
    )


@router.post("/start")
def wizard_step0_post(
    request: Request,
    name: str = Form(...),
    project_code: str | None = Form(None),
    client_authority: str | None = Form(None),
    contractor: str | None = Form(None),
    consultant_pmc: str | None = Form(None),
    country: str = Form("India"),
    state: str | None = Form(None),
    city: str = Form(...),
    planned_start_date: str = Form(...),
    planned_end_date: str = Form(...),
    wid: int | None = Form(None),
    db: Session = Depends(get_db),
):
    try:
        user = _require_user(request)
    except PermissionError:
        return _redirect_login(request)

    if wid:
        state = _wizard_or_redirect(request, db, wid, int(user["id"]))
        if not state:
            wid = None

    if not wid:
        row = create_wizard(db, user_id=int(user["id"]))
        wid = row.id

    patch = {
        "name": name.strip(),
        "project_code": (project_code or "").strip() or None,
        "client_authority": (client_authority or "").strip() or None,
        "contractor": (contractor or "").strip() or None,
        "consultant_pmc": (consultant_pmc or "").strip() or None,
        "country": (country or "India").strip() or "India",
        "state": (state or "").strip() or None,
        "city": (city or "").strip(),
        "planned_start_date": (planned_start_date or "").strip(),
        "planned_end_date": (planned_end_date or "").strip(),
    }

    update_state(db, wizard_id=wid, user_id=int(user["id"]), patch=patch, current_step=0)
    db.commit()
    return RedirectResponse(f"/projects/wizard/type?wid={wid}", status_code=302)


@router.get("/type", response_class=HTMLResponse)
def wizard_step1_get(request: Request, wid: int, db: Session = Depends(get_db)):
    try:
        user = _require_user(request)
    except PermissionError:
        return _redirect_login(request)

    state = _wizard_or_redirect(request, db, wid, int(user["id"]))
    if not state:
        return RedirectResponse("/projects/wizard/start", status_code=302)

    data = state.data
    return templates.TemplateResponse(
        "projects/wizard/step1_type.html",
        {"request": request, "user": user, "wid": wid, "data": data},
    )


@router.post("/type")
def wizard_step1_post(
    request: Request,
    wid: int = Form(...),
    project_type: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        user = _require_user(request)
    except PermissionError:
        return _redirect_login(request)

    state = _wizard_or_redirect(request, db, wid, int(user["id"]))
    if not state:
        return RedirectResponse("/projects/wizard/start", status_code=302)

    pt = (project_type or "").strip()
    if not pt:
        flash(request, "Please select a project type.", "error")
        return RedirectResponse(f"/projects/wizard/type?wid={wid}", status_code=302)

    update_state(db, wizard_id=wid, user_id=int(user["id"]), patch={"project_type": pt}, current_step=1)
    db.commit()

    if pt.lower() == "road":
        return RedirectResponse(f"/projects/wizard/road-classification?wid={wid}", status_code=302)

    # Non-road projects can preview generic presets later.
    return RedirectResponse(f"/projects/wizard/preview?wid={wid}", status_code=302)


@router.get("/road-classification", response_class=HTMLResponse)
def wizard_step2_get(request: Request, wid: int, db: Session = Depends(get_db)):
    try:
        user = _require_user(request)
    except PermissionError:
        return _redirect_login(request)

    state = _wizard_or_redirect(request, db, wid, int(user["id"]))
    if not state:
        return RedirectResponse("/projects/wizard/start", status_code=302)

    if (state.data.get("project_type") or "").lower() != "road":
        return RedirectResponse(f"/projects/wizard/type?wid={wid}", status_code=302)

    categories = ["Expressway", "NH", "SH", "MDR", "ODR", "Village", "Urban"]
    contexts = ["", "Access-controlled", "Urban", "Rural", "Industrial"]

    return templates.TemplateResponse(
        "projects/wizard/step2_road_classification.html",
        {"request": request, "user": user, "wid": wid, "data": state.data, "categories": categories, "contexts": contexts},
    )


@router.post("/road-classification")
def wizard_step2_post(
    request: Request,
    wid: int = Form(...),
    road_category: str = Form(...),
    road_context: str | None = Form(None),
    db: Session = Depends(get_db),
):
    try:
        user = _require_user(request)
    except PermissionError:
        return _redirect_login(request)

    state = _wizard_or_redirect(request, db, wid, int(user["id"]))
    if not state:
        return RedirectResponse("/projects/wizard/start", status_code=302)

    cat = (road_category or "").strip()
    if not cat:
        flash(request, "Please select a road category.", "error")
        return RedirectResponse(f"/projects/wizard/road-classification?wid={wid}", status_code=302)

    patch = {
        "road_category": cat,
        "road_context": (road_context or "").strip() or None,
    }
    update_state(db, wizard_id=wid, user_id=int(user["id"]), patch=patch, current_step=2)
    db.commit()
    return RedirectResponse(f"/projects/wizard/engineering?wid={wid}", status_code=302)


@router.get("/engineering", response_class=HTMLResponse)
def wizard_step3_get(request: Request, wid: int, db: Session = Depends(get_db)):
    try:
        user = _require_user(request)
    except PermissionError:
        return _redirect_login(request)

    state = _wizard_or_redirect(request, db, wid, int(user["id"]))
    if not state:
        return RedirectResponse("/projects/wizard/start", status_code=302)

    data = state.data
    if (data.get("project_type") or "").lower() != "road":
        return RedirectResponse(f"/projects/wizard/type?wid={wid}", status_code=302)

    cat = str(data.get("road_category") or "").strip()
    if not cat:
        return RedirectResponse(f"/projects/wizard/road-classification?wid={wid}", status_code=302)

    pavement_types = ["Flexible", "Rigid", "Composite"]
    construction_types = ["New Construction", "Overlay / Strengthening", "Rehabilitation"]

    chosen_pavement = str(data.get("pavement_type") or "").strip()
    chosen_construction = str(data.get("construction_type") or "").strip()

    presets: list[RoadPreset] = []
    if chosen_pavement and chosen_construction:
        presets = (
            db.query(RoadPreset)
            .filter(
                RoadPreset.is_active == True,  # noqa: E712
                RoadPreset.is_deleted == False,  # noqa: E712
                RoadPreset.road_category.in_([cat, "ALL"]),
                RoadPreset.engineering_type == chosen_pavement,
                RoadPreset.construction_type == chosen_construction,
            )
            .order_by(RoadPreset.road_category.desc(), RoadPreset.preset_key.asc())
            .all()
        )

    preset_options = [
        {"preset_key": p.preset_key, "title": _display_preset_name(p)}
        for p in presets
    ]

    is_admin = (user.get("role") in ["admin", "manager"])
    admin_all_presets: list[dict[str, str]] = []
    if is_admin:
        allp = (
            db.query(RoadPreset)
            .filter(RoadPreset.is_active == True, RoadPreset.is_deleted == False)  # noqa: E712
            .order_by(RoadPreset.preset_key.asc())
            .all()
        )
        admin_all_presets = [{"preset_key": p.preset_key, "title": _display_preset_name(p)} for p in allp]

    return templates.TemplateResponse(
        "projects/wizard/step3_engineering.html",
        {
            "request": request,
            "user": user,
            "wid": wid,
            "data": data,
            "pavement_types": pavement_types,
            "construction_types": construction_types,
            "preset_options": preset_options,
            "admin_all_presets": admin_all_presets,
        },
    )


@router.post("/engineering")
def wizard_step3_post(
    request: Request,
    wid: int = Form(...),
    pavement_type: str = Form(...),
    construction_type: str = Form(...),
    preset_key: str | None = Form(None),
    admin_preset_key: str | None = Form(None),
    db: Session = Depends(get_db),
):
    try:
        user = _require_user(request)
    except PermissionError:
        return _redirect_login(request)

    state = _wizard_or_redirect(request, db, wid, int(user["id"]))
    if not state:
        return RedirectResponse("/projects/wizard/start", status_code=302)

    pv = (pavement_type or "").strip()
    ct = (construction_type or "").strip()

    chosen_key = (admin_preset_key or preset_key or "").strip() or None

    patch: dict[str, Any] = {"pavement_type": pv, "construction_type": ct}
    if chosen_key:
        patch["preset_key"] = chosen_key

    update_state(db, wizard_id=wid, user_id=int(user["id"]), patch=patch, current_step=3)
    db.commit()

    # If we already have a concrete preset selection, go to preview.
    return RedirectResponse(f"/projects/wizard/preview?wid={wid}", status_code=302)


@router.get("/preview", response_class=HTMLResponse)
def wizard_step4_get(request: Request, wid: int, db: Session = Depends(get_db)):
    try:
        user = _require_user(request)
    except PermissionError:
        return _redirect_login(request)

    state = _wizard_or_redirect(request, db, wid, int(user["id"]))
    if not state:
        return RedirectResponse("/projects/wizard/start", status_code=302)

    data = state.data
    pt = str(data.get("project_type") or "").strip()

    preset = None
    activities: list[PresetActivity] = []
    materials: list[PresetMaterial] = []
    mapping_by_activity_code: dict[str, set[str]] = {}

    if pt.lower() == "road":
        preset_key = str(data.get("preset_key") or "").strip()
        if not preset_key:
            flash(request, "Select pavement + construction type and a preset first.", "warning")
            return RedirectResponse(f"/projects/wizard/engineering?wid={wid}", status_code=302)

        preset = db.query(RoadPreset).filter(RoadPreset.preset_key == preset_key, RoadPreset.is_deleted == False).first()
        if not preset or not preset.is_active:
            flash(request, "Selected preset is not available.", "error")
            return RedirectResponse(f"/projects/wizard/engineering?wid={wid}", status_code=302)

        activities = (
            db.query(PresetActivity)
            .filter(PresetActivity.preset_id == preset.id, PresetActivity.is_active == True)  # noqa: E712
            .order_by(PresetActivity.sequence_no.asc())
            .all()
        )
        materials = (
            db.query(PresetMaterial)
            .filter(PresetMaterial.preset_id == preset.id, PresetMaterial.is_active == True)  # noqa: E712
            .order_by(PresetMaterial.material_name.asc())
            .all()
        )

        # Load mapping pairs for preview/edit (by activity_code/material_code)
        act_by_id = {a.id: a for a in activities}
        mat_by_id = {m.id: m for m in materials}
        if act_by_id:
            maps = (
                db.query(PresetActivityMaterialMap)
                .filter(PresetActivityMaterialMap.preset_activity_id.in_(list(act_by_id.keys())))
                .all()
            )
            for mp in maps:
                a = act_by_id.get(mp.preset_activity_id)
                m = mat_by_id.get(mp.preset_material_id)
                if not a or not m:
                    continue
                mapping_by_activity_code.setdefault(a.activity_code, set()).add(m.material_code)

    # Group activities by category for collapsible UI.
    grouped: dict[str, list[PresetActivity]] = defaultdict(list)
    for a in activities:
        grouped[(a.category or "Other").strip()].append(a)

    return templates.TemplateResponse(
        "projects/wizard/step4_preview.html",
        {
            "request": request,
            "user": user,
            "wid": wid,
            "data": data,
            "preset": preset,
            "preset_title": _display_preset_name(preset) if preset else None,
            "grouped_activities": dict(grouped),
            "materials": materials,
            "mapping_by_activity_code": {k: sorted(list(v)) for k, v in mapping_by_activity_code.items()},
        },
    )


@router.post("/preview")
def wizard_step4_post(
    request: Request,
    wid: int = Form(...),
    enabled_activity_codes: list[str] | None = Form(None),
    selected_mappings: list[str] | None = Form(None),
    custom_activity: str | None = Form(None),
    db: Session = Depends(get_db),
):
    try:
        user = _require_user(request)
    except PermissionError:
        return _redirect_login(request)

    state = _wizard_or_redirect(request, db, wid, int(user["id"]))
    if not state:
        return RedirectResponse("/projects/wizard/start", status_code=302)

    data = state.data
    if (str(data.get("project_type") or "").lower() != "road"):
        flash(request, "Preview customization for non-road projects is not enabled yet.", "warning")
        return RedirectResponse(f"/projects/wizard/type?wid={wid}", status_code=302)

    preset_key = str(data.get("preset_key") or "").strip()
    preset = db.query(RoadPreset).filter(RoadPreset.preset_key == preset_key, RoadPreset.is_deleted == False).first()
    if not preset:
        return RedirectResponse(f"/projects/wizard/engineering?wid={wid}", status_code=302)

    activities = (
        db.query(PresetActivity)
        .filter(PresetActivity.preset_id == preset.id, PresetActivity.is_active == True)  # noqa: E712
        .order_by(PresetActivity.sequence_no.asc())
        .all()
    )
    materials = (
        db.query(PresetMaterial)
        .filter(PresetMaterial.preset_id == preset.id, PresetMaterial.is_active == True)  # noqa: E712
        .order_by(PresetMaterial.material_name.asc())
        .all()
    )

    enabled_set = {str(x or "").strip() for x in (enabled_activity_codes or []) if str(x or "").strip()}

    # Parse mapping selections like "ACT_CODE|MAT_CODE"
    parsed_pairs: list[dict[str, str]] = []
    selected_material_codes_by_activity: dict[str, set[str]] = {}
    for raw in (selected_mappings or []):
        s = str(raw or "").strip()
        if "|" not in s:
            continue
        ac, mc = s.split("|", 1)
        ac = ac.strip()
        mc = mc.strip()
        if not ac or not mc:
            continue
        parsed_pairs.append({"activity_code": ac, "material_code": mc})
        selected_material_codes_by_activity.setdefault(ac, set()).add(mc)

    # Build activity defs payload consumed by /projects/create
    activity_defs: list[dict[str, Any]] = []
    disabled_critical: list[str] = []
    for a in activities:
        enabled = (a.activity_code in enabled_set) if enabled_set else True
        if (not enabled) and (not a.is_optional):
            disabled_critical.append(a.activity_name)
        activity_defs.append({"name": a.activity_name, "enabled": enabled})

    if disabled_critical:
        flash(
            request,
            "Warning: You disabled critical activities: " + ", ".join(disabled_critical[:6]) + ("..." if len(disabled_critical) > 6 else ""),
            "warning",
        )

    custom = (custom_activity or "").strip()
    if custom:
        activity_defs.append({"name": custom[:150], "enabled": True})

    # Determine included materials.
    # If mapping was edited, include only the union of mapped materials for enabled activities.
    mat_by_code = {m.material_code: m for m in materials}
    included_material_codes: set[str] = set()
    if parsed_pairs:
        for a in activities:
            if enabled_set and a.activity_code not in enabled_set:
                continue
            included_material_codes.update(selected_material_codes_by_activity.get(a.activity_code, set()))

    material_defs: list[dict[str, Any]] = []
    for m in materials:
        if included_material_codes and m.material_code not in included_material_codes:
            continue
        unit = (m.unit or "unit").strip() or "unit"
        material_defs.append({"name": m.material_name, "default_unit": unit, "allowed_units": [unit]})

    update_state(
        db,
        wizard_id=wid,
        user_id=int(user["id"]),
        patch={
            "preset_key": preset_key,
            "activity_material_map": parsed_pairs,
            "activity_preset_defs_json": json.dumps(activity_defs, ensure_ascii=False),
            "material_preset_defs_json": json.dumps(material_defs, ensure_ascii=False),
        },
        current_step=4,
    )
    db.commit()

    return RedirectResponse(f"/projects/wizard/confirm?wid={wid}", status_code=302)


@router.get("/confirm", response_class=HTMLResponse)
def wizard_step5_get(request: Request, wid: int, db: Session = Depends(get_db)):
    try:
        user = _require_user(request)
    except PermissionError:
        return _redirect_login(request)

    state = _wizard_or_redirect(request, db, wid, int(user["id"]))
    if not state:
        return RedirectResponse("/projects/wizard/start", status_code=302)

    data = state.data

    preset = None
    if (str(data.get("project_type") or "").lower() == "road"):
        preset_key = str(data.get("preset_key") or "").strip()
        if preset_key:
            preset = db.query(RoadPreset).filter(RoadPreset.preset_key == preset_key, RoadPreset.is_deleted == False).first()

    return templates.TemplateResponse(
        "projects/wizard/step5_confirm.html",
        {
            "request": request,
            "user": user,
            "wid": wid,
            "data": data,
            "preset": preset,
            "preset_title": _display_preset_name(preset) if preset else None,
        },
    )


@router.post("/finish")
def wizard_finish_post(request: Request, wid: int = Form(...), db: Session = Depends(get_db)):
    """Deactivates wizard after /projects/create succeeds (best-effort)."""
    try:
        user = _require_user(request)
    except PermissionError:
        return _redirect_login(request)

    deactivate(db, wizard_id=wid, user_id=int(user["id"]))
    db.commit()
    return RedirectResponse("/projects", status_code=302)
