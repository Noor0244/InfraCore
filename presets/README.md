# InfraCore Road Preset Seeds (Deliverable Schema)

This folder contains **export-style JSON preset files** in the new standardized schema requested for the Road Preset Engine.

## Files

- `expressway_flexible_new.json` — Expressway, Flexible, New Construction
- `nh_flexible_new.json` — NH, Flexible, New Construction
- `sh_flexible_new.json` — SH, Flexible, New Construction
- `mdr_flexible_new.json` — MDR, Flexible, New Construction
- `odr_flexible_new.json` — ODR, Flexible, New Construction
- `village_flexible_new.json` — Village/PMGSY-type, Flexible, New Construction
- `urban_flexible_new.json` — Urban, Flexible, New Construction
- `overlay_flexible.json` — Flexible, Strengthening/Overlay (cross-category)
- `rigid_dlc_pqc.json` — Rigid, DLC+PQC (new construction)
- `rigid_pqc_only.json` — Rigid, PQC-only (new construction)
- `rigid_white_topping.json` — Rigid, White topping (rehabilitation)
- `composite_bituminous_over_concrete.json` — Composite, Bituminous over concrete overlay

## Conventions

- `preset_id` is globally unique and stable (reverse-DNS style).
- `activity_code` and `material_code` must be unique within a file.
- `activity_material_map` must reference codes that exist in the same JSON.
- Use `road_category: "ALL"` for cross-category presets to avoid duplication.

Schema details and cloning rules are documented in `docs/road_preset_seed_schema.md`.
