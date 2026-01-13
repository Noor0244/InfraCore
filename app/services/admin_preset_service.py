from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.road_preset import (
    PresetActivity,
    PresetActivityMaterialMap,
    PresetMaterial,
    RoadPreset,
)
from app.services.preset_importer import import_road_presets


CORE_TOKENS = {"GSB", "PQC", "DLC", "DBM", "BC"}


def _tok(s: str | None) -> str:
    return (s or "").upper()


def is_core_activity(a: PresetActivity) -> bool:
    code = _tok(a.activity_code)
    name = _tok(a.activity_name)
    return any(t in code for t in CORE_TOKENS) or any(t in name for t in CORE_TOKENS)


def is_core_material(m: PresetMaterial) -> bool:
    code = _tok(m.material_code)
    name = _tok(m.material_name)
    return any(t in code for t in CORE_TOKENS) or any(t in name for t in CORE_TOKENS)


def preset_is_linked_to_active_projects(db: Session, *, preset_key: str) -> bool:
    q = db.query(Project).filter(Project.road_preset_key == preset_key)
    # If these columns don't exist in an older DB, query will error; treat as linked=False.
    try:
        q = q.filter(Project.is_active == True)  # noqa: E712
        return q.count() > 0
    except Exception:
        return False


def serialize_preset(db: Session, *, preset_id: int) -> dict[str, Any] | None:
    preset = db.query(RoadPreset).filter(RoadPreset.id == preset_id).first()
    if not preset:
        return None

    activities = (
        db.query(PresetActivity)
        .filter(PresetActivity.preset_id == preset.id)
        .order_by(PresetActivity.sequence_no.asc(), PresetActivity.activity_code.asc())
        .all()
    )
    materials = (
        db.query(PresetMaterial)
        .filter(PresetMaterial.preset_id == preset.id)
        .order_by(PresetMaterial.material_name.asc())
        .all()
    )

    activity_ids = [a.id for a in activities]
    maps = []
    if activity_ids:
        maps = (
            db.query(PresetActivityMaterialMap)
            .filter(PresetActivityMaterialMap.preset_activity_id.in_(activity_ids))
            .all()
        )

    act_by_id = {a.id: a for a in activities}
    mat_by_id = {m.id: m for m in materials}

    mappings: list[dict[str, str]] = []
    for mp in maps:
        a = act_by_id.get(mp.preset_activity_id)
        m = mat_by_id.get(mp.preset_material_id)
        if not a or not m:
            continue
        mappings.append({"activity_code": a.activity_code, "material_code": m.material_code})

    return {
        "preset": {
            "id": preset.id,
            "preset_key": preset.preset_key,
            "title": preset.title,
            "road_category": preset.road_category,
            "engineering_type": preset.engineering_type,
            "construction_type": preset.construction_type,
            "road_engineering_type": preset.road_engineering_type,
            "is_active": bool(preset.is_active),
            "is_deleted": bool(getattr(preset, "is_deleted", False)),
            "user_modified": bool(preset.user_modified),
            "updated_at": preset.updated_at,
        },
        "activities": [
            {
                "activity_code": a.activity_code,
                "activity_name": a.activity_name,
                "category": a.category,
                "sequence_no": a.sequence_no,
                "is_optional": bool(a.is_optional),
                "is_active": bool(a.is_active),
                "is_core": is_core_activity(a),
            }
            for a in activities
        ],
        "materials": [
            {
                "material_code": m.material_code,
                "material_name": m.material_name,
                "unit": m.unit,
                "default_spec": m.default_spec,
                "is_active": bool(m.is_active),
                "is_core": is_core_material(m),
            }
            for m in materials
        ],
        "mappings": mappings,
    }


def _generate_code(prefix: str, existing: set[str]) -> str:
    for i in range(1, 10000):
        code = f"{prefix}{i:03d}"
        if code not in existing:
            return code
    raise ValueError("Unable to allocate a new code")


def apply_preset_update(db: Session, *, preset_id: int, payload: dict[str, Any]) -> None:
    preset = db.query(RoadPreset).filter(RoadPreset.id == preset_id).first()
    if not preset or getattr(preset, "is_deleted", False):
        raise ValueError("Preset not found")

    # Enforce non-editable metadata
    for key in ["preset_key", "road_category", "engineering_type", "construction_type"]:
        if key in payload:
            raise ValueError(f"Field not editable: {key}")

    title = payload.get("title")
    if title is not None:
        preset.title = str(title).strip()[:255] or None

    activities_in = payload.get("activities")
    materials_in = payload.get("materials")
    mappings_in = payload.get("mappings")

    if not isinstance(activities_in, list) or not isinstance(materials_in, list) or not isinstance(mappings_in, list):
        raise ValueError("Invalid payload: activities/materials/mappings must be lists")

    # Load existing
    activities = db.query(PresetActivity).filter(PresetActivity.preset_id == preset.id).all()
    materials = db.query(PresetMaterial).filter(PresetMaterial.preset_id == preset.id).all()

    act_by_code = {a.activity_code: a for a in activities}
    mat_by_code = {m.material_code: m for m in materials}

    existing_act_codes = set(act_by_code.keys())
    existing_mat_codes = set(mat_by_code.keys())

    # ---- Activities update ----
    order_codes: list[str] = []
    for item in activities_in:
        if not isinstance(item, dict):
            continue
        code = str(item.get("activity_code") or "").strip()
        name = str(item.get("activity_name") or "").strip()[:255]
        is_optional = bool(item.get("is_optional", False))
        is_active = bool(item.get("is_active", True))

        if not name:
            continue
        if not code:
            code = _generate_code("CUST_ACT_", existing_act_codes)
        if code not in act_by_code:
            act = PresetActivity(
                preset_id=preset.id,
                activity_code=code,
                activity_name=name,
                category="Other",
                sequence_no=9999,
                is_optional=is_optional,
                is_active=is_active,
                user_modified=True,
            )
            db.add(act)
            act_by_code[code] = act
            existing_act_codes.add(code)
        else:
            act = act_by_code[code]
            if is_core_activity(act) and not is_active:
                raise ValueError(f"Core activity cannot be removed: {act.activity_name}")
            act.activity_name = name
            act.is_optional = is_optional
            act.is_active = is_active
            act.user_modified = True
            db.add(act)

        order_codes.append(code)

    # Auto-correct sequence gaps: assign contiguous order to active activities only.
    seq = 1
    for code in order_codes:
        act = act_by_code.get(code)
        if not act or not act.is_active:
            continue
        act.sequence_no = seq
        seq += 1
        db.add(act)

    if seq == 1:
        raise ValueError("Preset must contain at least one active activity")

    # ---- Materials update ----
    for item in materials_in:
        if not isinstance(item, dict):
            continue
        code = str(item.get("material_code") or "").strip()
        name = str(item.get("material_name") or "").strip()[:255]
        unit = str(item.get("unit") or "").strip()[:30] or None
        spec = str(item.get("default_spec") or "").strip()[:80] or None
        is_active = bool(item.get("is_active", True))

        if not name:
            continue
        if not code:
            code = _generate_code("CUST_MAT_", existing_mat_codes)
        if code not in mat_by_code:
            mat = PresetMaterial(
                preset_id=preset.id,
                material_code=code,
                material_name=name,
                unit=unit,
                default_spec=spec,
                is_active=is_active,
                user_modified=True,
            )
            db.add(mat)
            mat_by_code[code] = mat
            existing_mat_codes.add(code)
        else:
            mat = mat_by_code[code]
            if is_core_material(mat) and not is_active:
                raise ValueError(f"Core material cannot be removed: {mat.material_name}")
            mat.material_name = name
            mat.unit = unit
            mat.default_spec = spec
            mat.is_active = is_active
            mat.user_modified = True
            db.add(mat)

    if not any(m.is_active for m in mat_by_code.values()):
        raise ValueError("Preset must contain at least one active material")

    # ---- Mappings (rebuild) ----
    # Build code -> id maps (flush to ensure new rows have ids)
    db.flush()

    all_act_ids = [a.id for a in act_by_code.values()]
    if all_act_ids:
        db.query(PresetActivityMaterialMap).filter(
            PresetActivityMaterialMap.preset_activity_id.in_(all_act_ids)
        ).delete(synchronize_session=False)

    # Insert new mappings; skip disabled items
    seen_pairs: set[tuple[int, int]] = set()
    for item in mappings_in:
        if not isinstance(item, dict):
            continue
        ac = str(item.get("activity_code") or "").strip()
        mc = str(item.get("material_code") or "").strip()
        if not ac or not mc:
            continue
        a = act_by_code.get(ac)
        m = mat_by_code.get(mc)
        if not a or not m:
            raise ValueError(f"Mapping references unknown code: {ac} -> {mc}")
        if not a.is_active or not m.is_active:
            continue
        pair = (a.id, m.id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        db.add(PresetActivityMaterialMap(preset_activity_id=a.id, preset_material_id=m.id))

    preset.user_modified = True
    db.add(preset)


def clone_preset(db: Session, *, preset_id: int, new_title: str | None) -> RoadPreset:
    src = db.query(RoadPreset).filter(RoadPreset.id == preset_id).first()
    if not src or getattr(src, "is_deleted", False):
        raise ValueError("Preset not found")

    base_key = f"{src.preset_key}.clone.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    key = base_key
    i = 1
    while db.query(RoadPreset).filter(RoadPreset.preset_key == key).first():
        i += 1
        key = f"{base_key}.{i}"

    dst = RoadPreset(
        preset_key=key,
        road_category=src.road_category,
        engineering_type=src.engineering_type,
        construction_type=src.construction_type,
        region=src.region,
        standards=src.standards,
        road_engineering_type=src.road_engineering_type,
        title=(str(new_title).strip()[:255] if (new_title or "").strip() else (src.title or f"Clone of {src.preset_key}")),
        detail_level=src.detail_level,
        material_depth=src.material_depth,
        preset_json=src.preset_json,
        is_active=True,
        is_deleted=False,
        user_modified=True,
    )
    db.add(dst)
    db.flush()

    src_acts = db.query(PresetActivity).filter(PresetActivity.preset_id == src.id).all()
    src_mats = db.query(PresetMaterial).filter(PresetMaterial.preset_id == src.id).all()

    act_id_map: dict[int, int] = {}
    mat_id_map: dict[int, int] = {}

    for a in src_acts:
        na = PresetActivity(
            preset_id=dst.id,
            activity_code=a.activity_code,
            activity_name=a.activity_name,
            category=a.category,
            sequence_no=a.sequence_no,
            is_optional=a.is_optional,
            is_active=a.is_active,
            user_modified=True,
        )
        db.add(na)
        db.flush()
        act_id_map[a.id] = na.id

    for m in src_mats:
        nm = PresetMaterial(
            preset_id=dst.id,
            material_code=m.material_code,
            material_name=m.material_name,
            unit=m.unit,
            default_spec=m.default_spec,
            is_expandable=m.is_expandable,
            is_active=m.is_active,
            user_modified=True,
        )
        db.add(nm)
        db.flush()
        mat_id_map[m.id] = nm.id

    src_act_ids = [a.id for a in src_acts]
    if src_act_ids:
        src_maps = db.query(PresetActivityMaterialMap).filter(
            PresetActivityMaterialMap.preset_activity_id.in_(src_act_ids)
        ).all()
        for mp in src_maps:
            naid = act_id_map.get(mp.preset_activity_id)
            nmid = mat_id_map.get(mp.preset_material_id)
            if naid and nmid:
                db.add(PresetActivityMaterialMap(preset_activity_id=naid, preset_material_id=nmid))

    return dst


def reset_preset_to_seed(db: Session, *, preset_key: str) -> None:
    # Safety guard
    if preset_is_linked_to_active_projects(db, preset_key=preset_key):
        raise ValueError("Cannot reset: preset is linked to active projects")

    # Force import only this preset
    import_road_presets(db=db, presets_dir=None, force_import=True, preset_keys={preset_key})


def soft_delete_preset(db: Session, *, preset_id: int) -> None:
    preset = db.query(RoadPreset).filter(RoadPreset.id == preset_id).first()
    if not preset:
        raise ValueError("Preset not found")

    if preset_is_linked_to_active_projects(db, preset_key=preset.preset_key):
        raise ValueError("Cannot delete: preset is linked to active projects")

    preset.is_deleted = True
    preset.is_active = False
    preset.user_modified = True
    db.add(preset)
