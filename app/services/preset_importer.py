from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.models.road_preset import (
    PresetActivity,
    PresetActivityMaterialMap,
    PresetMaterial,
    RoadPreset,
)

logger = logging.getLogger(__name__)


@dataclass
class ImportSummary:
    scanned_files: int = 0
    imported_presets: int = 0
    skipped_user_modified: int = 0
    updated_presets: int = 0
    created_presets: int = 0
    errors: int = 0


def _repo_root() -> Path:
    # app/services/preset_importer.py -> app/services -> app -> repo
    return Path(__file__).resolve().parents[2]


def _default_presets_dir() -> Path:
    return _repo_root() / "presets"


def _derive_road_engineering_type(engineering_type: str | None, construction_type: str | None) -> str:
    eng = (engineering_type or "").strip()
    cons = (construction_type or "").strip()

    eng_l = eng.lower()
    if "flex" in eng_l:
        base = "Flexible Pavement"
    elif "rigid" in eng_l:
        base = "Rigid Pavement"
    elif "composite" in eng_l:
        base = "Composite Pavement"
    elif "overlay" in eng_l:
        base = "Flexible Pavement"
    else:
        base = eng or "Road"

    cons_l = cons.lower()
    if "strength" in cons_l or "overlay" in cons_l:
        suffix = "Strengthening / Overlay"
    elif "new" in cons_l:
        suffix = "New Construction"
    elif "rehab" in cons_l:
        suffix = "Rehabilitation"
    else:
        suffix = cons or "Construction"

    # Use an en dash to match the existing seed convention.
    return f"{base} – {suffix}"


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _validate_preset_json(data: dict[str, Any], *, preset_key: str) -> None:
    activity_list = data.get("activity_preset")
    material_list = data.get("material_preset")
    map_list = data.get("activity_material_map")

    if not isinstance(activity_list, list) or not activity_list:
        raise ValueError(f"{preset_key}: Missing or empty activity_preset")
    if not isinstance(material_list, list) or not material_list:
        raise ValueError(f"{preset_key}: Missing or empty material_preset")
    if map_list is None:
        raise ValueError(f"{preset_key}: Missing activity_material_map")
    if not isinstance(map_list, list):
        raise ValueError(f"{preset_key}: activity_material_map must be a list")

    codes: set[str] = set()
    seqs: set[int] = set()
    for item in activity_list:
        if not isinstance(item, dict):
            raise ValueError(f"{preset_key}: activity_preset entries must be objects")
        code = str(item.get("activity_code") or "").strip()
        name = str(item.get("activity_name") or "").strip()
        if not code or not name:
            raise ValueError(f"{preset_key}: activity_preset missing activity_code/activity_name")
        if code in codes:
            raise ValueError(f"{preset_key}: duplicate activity_code {code}")
        codes.add(code)
        try:
            seq = int(item.get("sequence"))
        except Exception:
            raise ValueError(f"{preset_key}: invalid sequence for {code}")
        if seq in seqs:
            raise ValueError(f"{preset_key}: duplicate sequence {seq}")
        seqs.add(seq)

    mat_codes: set[str] = set()
    for item in material_list:
        if not isinstance(item, dict):
            raise ValueError(f"{preset_key}: material_preset entries must be objects")
        code = str(item.get("material_code") or "").strip()
        name = str(item.get("material_name") or "").strip()
        if not code or not name:
            raise ValueError(f"{preset_key}: material_preset missing material_code/material_name")
        if code in mat_codes:
            raise ValueError(f"{preset_key}: duplicate material_code {code}")
        mat_codes.add(code)

    # Validate map references
    for item in map_list:
        if not isinstance(item, dict):
            raise ValueError(f"{preset_key}: activity_material_map entries must be objects")
        a = str(item.get("activity_code") or "").strip()
        m = str(item.get("material_code") or "").strip()
        if not a or not m:
            raise ValueError(f"{preset_key}: activity_material_map missing activity_code/material_code")
        if a not in codes:
            raise ValueError(f"{preset_key}: map references unknown activity_code {a}")
        if m not in mat_codes:
            raise ValueError(f"{preset_key}: map references unknown material_code {m}")


def _ensure_schema(db: Session) -> None:
    """Create new tables and add missing columns for legacy road_presets table (SQLite-safe)."""

    # Ensure SQLAlchemy has imported all models before mapper configuration.
    # This avoids relationship resolution errors in ad-hoc scripts.
    import app.db.models  # noqa: F401

    # Create any new tables.
    Base.metadata.create_all(bind=engine)

    # Add missing columns to road_presets (SQLite: ALTER TABLE ADD COLUMN).
    # This keeps old deployments working without a full migration framework.
    required_cols: list[tuple[str, str]] = [
        ("engineering_type", "TEXT"),
        ("construction_type", "TEXT"),
        ("standards", "TEXT"),
        ("user_modified", "BOOLEAN NOT NULL DEFAULT 0"),
        ("is_deleted", "BOOLEAN NOT NULL DEFAULT 0"),
    ]

    existing = {
        row[1]
        for row in db.execute(text("PRAGMA table_info('road_presets')")).fetchall()
    }

    for col, ddl in required_cols:
        if col in existing:
            continue
        logger.info("Adding missing column road_presets.%s", col)
        db.execute(text(f"ALTER TABLE road_presets ADD COLUMN {col} {ddl}"))


def _upsert_preset(
    db: Session,
    *,
    preset_key: str,
    road_category: str,
    engineering_type: str | None,
    construction_type: str | None,
    region: str | None,
    standards: Any,
    force_import: bool,
) -> tuple[RoadPreset, bool, bool]:
    """Return (preset, created, updated)."""

    preset = db.query(RoadPreset).filter(RoadPreset.preset_key == preset_key).first()
    if preset is None:
        preset = RoadPreset(
            preset_key=preset_key,
            road_category=road_category,
            engineering_type=(engineering_type or None),
            construction_type=(construction_type or None),
            region=(region or "India"),
            standards=_json_dumps(standards) if standards is not None else None,
            road_engineering_type=_derive_road_engineering_type(engineering_type, construction_type),
            preset_json="{}",
            is_active=True,
            is_deleted=False,
            user_modified=False,
        )
        db.add(preset)
        db.flush()
        return preset, True, False

    if preset.user_modified and not force_import:
        return preset, False, False

    # Update top-level metadata (force_import can be used as an admin reset).
    preset.road_category = road_category
    preset.engineering_type = (engineering_type or None)
    preset.construction_type = (construction_type or None)
    preset.region = (region or preset.region or "India")
    preset.standards = _json_dumps(standards) if standards is not None else preset.standards
    preset.road_engineering_type = _derive_road_engineering_type(engineering_type, construction_type)
    preset.is_active = True
    preset.is_deleted = False
    if force_import:
        preset.user_modified = False

    db.flush()
    return preset, False, True


def _sync_activities(
    db: Session,
    *,
    preset: RoadPreset,
    activities: Iterable[dict[str, Any]],
    force_import: bool,
) -> dict[str, PresetActivity]:
    existing = (
        db.query(PresetActivity)
        .filter(PresetActivity.preset_id == preset.id)
        .all()
    )
    by_code = {a.activity_code: a for a in existing}

    seen: set[str] = set()
    for item in activities:
        code = str(item.get("activity_code") or "").strip()
        name = str(item.get("activity_name") or "").strip()
        category = str(item.get("category") or "").strip() or None
        seq = int(item.get("sequence"))
        is_optional = bool(item.get("is_optional") is True)

        seen.add(code)

        row = by_code.get(code)
        if row is None:
            row = PresetActivity(
                preset_id=preset.id,
                activity_code=code,
                activity_name=name,
                category=category,
                sequence_no=seq,
                is_optional=is_optional,
                is_active=True,
                user_modified=False,
            )
            db.add(row)
            db.flush()
            by_code[code] = row
            continue

        if row.user_modified and not force_import:
            # Keep user modifications.
            continue

        row.activity_name = name
        row.category = category
        row.sequence_no = seq
        row.is_optional = is_optional
        row.is_active = True

    # Deactivate missing activities (only if not user_modified unless force_import).
    for code, row in by_code.items():
        if code in seen:
            continue
        if row.user_modified and not force_import:
            continue
        row.is_active = False

    db.flush()
    return by_code


def _sync_materials(
    db: Session,
    *,
    preset: RoadPreset,
    materials: Iterable[dict[str, Any]],
    force_import: bool,
) -> dict[str, PresetMaterial]:
    existing = (
        db.query(PresetMaterial)
        .filter(PresetMaterial.preset_id == preset.id)
        .all()
    )
    by_code = {m.material_code: m for m in existing}

    seen: set[str] = set()
    for item in materials:
        code = str(item.get("material_code") or "").strip()
        name = str(item.get("material_name") or "").strip()
        unit = str(item.get("unit") or "").strip() or None
        default_spec = str(item.get("default_spec") or "").strip() or None
        is_expandable = bool(item.get("is_expandable") is True)

        seen.add(code)

        row = by_code.get(code)
        if row is None:
            row = PresetMaterial(
                preset_id=preset.id,
                material_code=code,
                material_name=name,
                unit=unit,
                default_spec=default_spec,
                is_expandable=is_expandable,
                is_active=True,
                user_modified=False,
            )
            db.add(row)
            db.flush()
            by_code[code] = row
            continue

        if row.user_modified and not force_import:
            continue

        row.material_name = name
        row.unit = unit
        row.default_spec = default_spec
        row.is_expandable = is_expandable
        row.is_active = True

    for code, row in by_code.items():
        if code in seen:
            continue
        if row.user_modified and not force_import:
            continue
        row.is_active = False

    db.flush()
    return by_code


def _sync_mappings(
    db: Session,
    *,
    activity_by_code: dict[str, PresetActivity],
    material_by_code: dict[str, PresetMaterial],
    mapping_items: Iterable[dict[str, Any]],
    force_import: bool,
) -> None:
    desired_pairs: set[tuple[int, int]] = set()
    for item in mapping_items:
        a_code = str(item.get("activity_code") or "").strip()
        m_code = str(item.get("material_code") or "").strip()
        a = activity_by_code.get(a_code)
        m = material_by_code.get(m_code)
        if a is None or m is None:
            # Validation should have caught this, but keep it explicit.
            raise ValueError(f"Broken mapping reference: {a_code} -> {m_code}")
        desired_pairs.add((a.id, m.id))

    act_ids = [a.id for a in activity_by_code.values()]
    if not act_ids:
        return

    existing_maps = (
        db.query(PresetActivityMaterialMap)
        .filter(PresetActivityMaterialMap.preset_activity_id.in_(act_ids))
        .all()
    )
    existing_pairs = {(r.preset_activity_id, r.preset_material_id): r for r in existing_maps}

    # Add missing
    for pair in desired_pairs:
        if pair in existing_pairs:
            continue
        db.add(PresetActivityMaterialMap(preset_activity_id=pair[0], preset_material_id=pair[1]))

    # Remove stale (unless affected by user-modified activity/material, unless force_import)
    activity_by_id = {a.id: a for a in activity_by_code.values()}
    material_by_id = {m.id: m for m in material_by_code.values()}

    for pair, row in existing_pairs.items():
        if pair in desired_pairs:
            continue
        if force_import:
            db.delete(row)
            continue
        a = activity_by_id.get(pair[0])
        m = material_by_id.get(pair[1])
        if (a and a.user_modified) or (m and m.user_modified):
            continue
        db.delete(row)

    db.flush()


def _build_legacy_preset_json(
    *,
    preset_key: str,
    road_category: str,
    road_engineering_type: str,
    data: dict[str, Any],
) -> str:
    activities = []
    for a in data.get("activity_preset") or []:
        if not isinstance(a, dict):
            continue
        activities.append(
            {
                "code": str(a.get("activity_code") or "").strip(),
                "name": str(a.get("activity_name") or "").strip(),
            }
        )

    materials = []
    for m in data.get("material_preset") or []:
        if not isinstance(m, dict):
            continue
        unit = str(m.get("unit") or "unit").strip() or "unit"
        materials.append(
            {
                "code": str(m.get("material_code") or "").strip(),
                "name": str(m.get("material_name") or "").strip(),
                "default_unit": unit,
                "allowed_units": [unit],
            }
        )

    links = []
    for item in data.get("activity_material_map") or []:
        if not isinstance(item, dict):
            continue
        links.append(
            {
                "activity_code": str(item.get("activity_code") or "").strip(),
                "material_code": str(item.get("material_code") or "").strip(),
                "consumption_rate": 0,
            }
        )

    legacy = {
        "preset_key": preset_key,
        "road_category": road_category,
        "road_engineering_type": road_engineering_type,
        "activities": activities,
        "materials": materials,
        "activity_materials": links,
    }
    return json.dumps(legacy, ensure_ascii=False)


def import_road_presets(
    *,
    db: Session,
    presets_dir: str | Path | None = None,
    force_import: bool = False,
    preset_keys: set[str] | None = None,
) -> ImportSummary:
    """Import preset JSON files from /presets into DB.

    Safety rules:
    - If road_presets.user_modified is true: skip unless force_import.
    - For child rows: do not overwrite user_modified activity/material rows unless force_import.

    The import is idempotent and transactional.
    """

    summary = ImportSummary()

    _ensure_schema(db)

    directory = Path(presets_dir) if presets_dir is not None else _default_presets_dir()
    if not directory.exists():
        raise FileNotFoundError(f"Presets directory not found: {directory}")

    files = sorted([p for p in directory.glob("*.json") if p.is_file()])
    if preset_keys:
        wanted = {str(k or "").strip() for k in preset_keys if str(k or "").strip()}
        files = [p for p in files if p.stem.strip() in wanted]
    summary.scanned_files = len(files)

    # If we're already inside a transaction (common in FastAPI), use a SAVEPOINT.
    txn_ctx = db.begin_nested() if db.in_transaction() else db.begin()
    with txn_ctx:
        for path in files:
            preset_key = path.stem.strip()
            if not preset_key:
                continue

            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("Preset JSON must be an object")

                _validate_preset_json(data, preset_key=preset_key)

                road_category = str(data.get("road_category") or "").strip()
                engineering_type = str(data.get("engineering_type") or "").strip() or None
                construction_type = str(data.get("construction_type") or "").strip() or None
                region = str(data.get("region") or "").strip() or None
                standards = data.get("standards")

                if not road_category:
                    raise ValueError(f"{preset_key}: Missing road_category")

                preset, created, updated = _upsert_preset(
                    db,
                    preset_key=preset_key,
                    road_category=road_category,
                    engineering_type=engineering_type,
                    construction_type=construction_type,
                    region=region,
                    standards=standards,
                    force_import=force_import,
                )

                if not (created or updated) and preset.user_modified and not force_import:
                    summary.skipped_user_modified += 1
                    logger.info("Skipped user-modified preset: %s", preset_key)
                    continue

                activity_by_code = _sync_activities(
                    db,
                    preset=preset,
                    activities=data.get("activity_preset") or [],
                    force_import=force_import,
                )
                material_by_code = _sync_materials(
                    db,
                    preset=preset,
                    materials=data.get("material_preset") or [],
                    force_import=force_import,
                )
                _sync_mappings(
                    db,
                    activity_by_code=activity_by_code,
                    material_by_code=material_by_code,
                    mapping_items=data.get("activity_material_map") or [],
                    force_import=force_import,
                )

                # Maintain a legacy snapshot for the existing road_preset_engine DB loader.
                preset.road_engineering_type = _derive_road_engineering_type(engineering_type, construction_type)
                preset.preset_json = _build_legacy_preset_json(
                    preset_key=preset_key,
                    road_category=road_category,
                    road_engineering_type=preset.road_engineering_type or "",
                    data=data,
                )

                summary.imported_presets += 1
                if created:
                    summary.created_presets += 1
                elif updated:
                    summary.updated_presets += 1

                logger.info(
                    "Imported preset=%s created=%s updated=%s activities=%s materials=%s",
                    preset_key,
                    created,
                    updated,
                    len(activity_by_code),
                    len(material_by_code),
                )

            except Exception as exc:
                summary.errors += 1
                logger.exception("Failed importing preset %s from %s: %s", preset_key, path, exc)
                raise

    return summary
