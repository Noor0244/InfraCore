from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.road_preset import RoadPreset


def _repo_root() -> Path:
    # app/db/seed_road_presets.py -> app/db -> app -> repo
    return Path(__file__).resolve().parents[2]


def _seed_dir() -> Path:
    return _repo_root() / "data" / "presets" / "road"


def seed_road_presets(db: Session) -> int:
    """Load JSON seed files into DB (upsert by preset_key).

    Source of truth remains JSON files; DB copy enables admin editing later.
    """
    seed_dir = _seed_dir()
    if not seed_dir.exists():
        return 0

    count = 0
    for path in sorted(seed_dir.glob("*.json")):
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception:
            continue

        preset_key = str(data.get("preset_key") or "").strip()
        road_category = str(data.get("road_category") or "").strip()
        engineering_type = str(data.get("road_engineering_type") or "").strip()
        if not preset_key or not road_category or not engineering_type:
            continue

        region = str(data.get("region") or "India").strip() or "India"
        title = str(data.get("title") or "").strip() or None
        standards = data.get("standards")
        if isinstance(standards, list):
            standards_text = ", ".join([str(x).strip() for x in standards if str(x).strip()]) or None
        else:
            standards_text = str(standards).strip() if standards else None

        detail_level = str(data.get("detail_level") or "").strip() or None
        material_depth = str(data.get("material_depth") or "").strip() or None

        existing = db.query(RoadPreset).filter(RoadPreset.preset_key == preset_key).first()
        if existing:
            # Never overwrite admin-edited or soft-deleted presets.
            if getattr(existing, "is_deleted", False):
                continue
            if getattr(existing, "user_modified", False):
                continue
            existing.region = region
            existing.road_category = road_category
            existing.road_engineering_type = engineering_type
            existing.title = title
            existing.standards = standards_text
            existing.detail_level = detail_level
            existing.material_depth = material_depth
            existing.preset_json = raw
            existing.is_active = True
            db.add(existing)
        else:
            db.add(
                RoadPreset(
                    preset_key=preset_key,
                    region=region,
                    road_category=road_category,
                    road_engineering_type=engineering_type,
                    title=title,
                    standards=standards_text,
                    detail_level=detail_level,
                    material_depth=material_depth,
                    preset_json=raw,
                    is_active=True,
                )
            )

        count += 1

    if count:
        db.commit()

    return count
