from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.road_preset import RoadPreset
from app.utils.activity_material_presets import ActivityMaterialLink, MaterialDef
from app.utils.road_classification import MaterialPreset


@dataclass(frozen=True)
class RoadPresetResult:
    preset_key: str
    road_category: str
    road_engineering_type: str
    activities: list[str]
    materials: list[MaterialPreset]
    links: list[ActivityMaterialLink]


def _repo_root() -> Path:
    # app/utils/road_preset_engine.py -> app/utils -> app -> repo
    return Path(__file__).resolve().parents[2]


def _seed_dir() -> Path:
    return _repo_root() / "data" / "presets" / "road"


def _norm_dash(value: str | None) -> str:
    """Normalize common dash variants to a plain hyphen.

    This makes preset matching robust against copy/paste differences like
    '-', '–', '—', and '−'.
    """
    if value is None:
        return ""
    return (
        str(value)
        .replace("\u2013", "-")  # en dash
        .replace("\u2014", "-")  # em dash
        .replace("\u2212", "-")  # minus sign
        .strip()
    )


def _canon_engineering_type(value: str | None) -> str:
    v = _norm_dash(value).lower()
    # Allow minor word-order variants
    if v in {
        "flexible pavement - overlay / strengthening",
        "flexible pavement - overlay/strengthening",
        "flexible pavement - strengthening / overlay",
        "flexible pavement - strengthening/overlay",
    }:
        return "flexible pavement - strengthening / overlay"
    return v


def _norm_yesno(value: str | None) -> str:
    v = (value or "").strip().lower()
    if v in {"yes", "y", "true", "1"}:
        return "Yes"
    if v in {"no", "n", "false", "0"}:
        return "No"
    return (value or "").strip()


def _parse_extras(road_extras_json: str | None) -> dict[str, str]:
    if not (road_extras_json or "").strip():
        return {}
    try:
        data = json.loads(road_extras_json)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in list(data.items())[:200]:
        key = str(k or "").strip()
        if not key:
            continue
        out[key] = _norm_yesno(str(v or "").strip())
    return out


def _load_from_db(db: Session, road_category: str, engineering_type: str) -> dict[str, Any] | None:
    # Prefer exact category match, then fall back to presets declared for ALL.
    row = (
        db.query(RoadPreset)
        .filter(
            RoadPreset.is_active == True,  # noqa: E712
            RoadPreset.is_deleted == False,  # noqa: E712
            RoadPreset.road_category == road_category,
            RoadPreset.road_engineering_type == engineering_type,
        )
        .order_by(RoadPreset.id.desc())
        .first()
    )
    if not row and road_category != "ALL":
        row = (
            db.query(RoadPreset)
            .filter(
                RoadPreset.is_active == True,  # noqa: E712
                RoadPreset.is_deleted == False,  # noqa: E712
                RoadPreset.road_category == "ALL",
                RoadPreset.road_engineering_type == engineering_type,
            )
            .order_by(RoadPreset.id.desc())
            .first()
        )
    if not row:
        return None
    try:
        return json.loads(row.preset_json)
    except Exception:
        return None


def _load_from_seed_files(road_category: str, engineering_type: str) -> dict[str, Any] | None:
    seed_dir = _seed_dir()
    if not seed_dir.exists():
        return None

    wanted_cat = (road_category or "").strip()
    wanted_eng = _canon_engineering_type(engineering_type)
    categories_to_try = [wanted_cat]
    if wanted_cat and wanted_cat != "ALL":
        categories_to_try.append("ALL")

    for cat in categories_to_try:
        for path in sorted(seed_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue

            if str(data.get("road_category") or "").strip() != cat:
                continue
            if _canon_engineering_type(str(data.get("road_engineering_type") or "").strip()) != wanted_eng:
                continue
            return data

    return None


def get_road_preset(
    *,
    road_category: str | None,
    road_engineering_type: str | None,
    road_extras_json: str | None = None,
    db: Session | None = None,
) -> RoadPresetResult | None:
    """Return a standards-based Road Preset (data-driven).

    - Prefers DB-loaded presets (admin-editable), falls back to JSON seed files.
    - Applies simple conditional includes using road_extras_json (Yes/No style).

    Returns None when no matching preset exists.
    """
    category = (road_category or "").strip()
    engineering = (road_engineering_type or "").strip()
    if not category or not engineering:
        return None

    # Normalize engineering type for matching, but preserve original display value.
    engineering_for_match = _canon_engineering_type(engineering)
    # Engine functions compare against normalized seed/db values.
    engineering_normalized_display = engineering

    data: dict[str, Any] | None = None
    if db is not None:
        data = _load_from_db(db, category, engineering_normalized_display)
    if data is None:
        data = _load_from_seed_files(category, engineering_for_match)
    if data is None:
        return None

    preset_key = str(data.get("preset_key") or "").strip() or f"in.road.{category}.{engineering}".lower()

    extras = _parse_extras(road_extras_json)

    # Activities (ordered)
    activities_raw = data.get("activities")
    activities: list[str] = []
    activity_by_code: dict[str, str] = {}
    if isinstance(activities_raw, list):
        for item in activities_raw[:1000]:
            if isinstance(item, str):
                name = item.strip()
                if name:
                    activities.append(name)
                continue
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            code = str(item.get("code") or "").strip()

            include_if = item.get("include_if")
            if isinstance(include_if, dict):
                k = str(include_if.get("key") or "").strip()
                expected = _norm_yesno(str(include_if.get("equals") or "").strip())
                actual = extras.get(k)
                if expected and actual != expected:
                    # If condition is defined and not met, skip.
                    continue

            if not name:
                continue
            activities.append(name)
            if code:
                activity_by_code[code] = name

    # Materials
    materials_raw = data.get("materials")
    materials: list[MaterialPreset] = []
    material_by_code: dict[str, MaterialDef] = {}
    if isinstance(materials_raw, list):
        for item in materials_raw[:1000]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            code = str(item.get("code") or "").strip()
            unit = str(item.get("default_unit") or "unit").strip() or "unit"
            allowed_units_raw = item.get("allowed_units")
            allowed: list[str] = []
            if isinstance(allowed_units_raw, list):
                allowed = [str(u or "").strip() for u in allowed_units_raw]
                allowed = [u for u in allowed if u]
            if not allowed:
                allowed = [unit]
            if unit not in allowed:
                allowed.insert(0, unit)

            if not name:
                continue

            materials.append(MaterialPreset(name=name, default_unit=unit, allowed_units=allowed))
            if code:
                material_by_code[code] = MaterialDef(name=name, default_unit=unit, allowed_units=allowed)

    # Links (activity-material mappings)
    links: list[ActivityMaterialLink] = []
    links_raw = data.get("activity_materials")
    if isinstance(links_raw, list):
        for item in links_raw[:5000]:
            if not isinstance(item, dict):
                continue
            act_code = str(item.get("activity_code") or "").strip()
            mat_code = str(item.get("material_code") or "").strip()
            if not act_code or not mat_code:
                continue

            act_name = activity_by_code.get(act_code)
            mat_def = material_by_code.get(mat_code)
            if not act_name or not mat_def:
                continue

            if act_name not in activities:
                continue

            try:
                rate = float(item.get("consumption_rate") or 0)
            except Exception:
                rate = 0.0

            links.append(ActivityMaterialLink(activity=act_name, material=mat_def, consumption_rate=max(rate, 0.0)))

    # If no codes were provided in activities, fallback to matching by string name (best-effort)
    # (not used by current seed format, but allows simpler seeds later)

    return RoadPresetResult(
        preset_key=preset_key,
        road_category=category,
        road_engineering_type=engineering,
        activities=activities,
        materials=materials,
        links=links,
    )


def serialize_material_presets(materials: list[MaterialPreset]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for m in materials:
        name = (m.name or "").strip()
        if not name:
            continue
        unit = (m.default_unit or "unit").strip() or "unit"
        allowed = [str(u or "").strip() for u in (m.allowed_units or []) if str(u or "").strip()]
        if not allowed:
            allowed = [unit]
        if unit not in allowed:
            allowed.insert(0, unit)
        out.append({"name": name, "default_unit": unit, "allowed_units": allowed})
    return out
