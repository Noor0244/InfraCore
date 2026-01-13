# Road Preset Seed Schema (Deliverable)

This document defines the standardized JSON structure for Road Preset Engine seed exports stored in `/presets`.

## Top-level object

Required keys:

- `preset_id` (string) — globally unique identifier, e.g. `in.road.nh.flexible.new`
- `road_category` (string) — one of:
  - `Expressway | NH | SH | MDR | ODR | Village | Urban | ALL`
  - Use `ALL` for cross-category presets (overlay/strengthening, rigid/composite templates).
- `engineering_type` (string) — e.g. `Flexible | Rigid | Composite`
- `construction_type` (string) — e.g. `New Construction | Strengthening / Overlay | Overlay | Rehabilitation`
- `region` (string) — e.g. `India`
- `standards` (array of strings) — e.g. `["MoRTH", "IRC"]`
- `activity_preset` (array) — ordered activity list
- `material_preset` (array) — material master list
- `activity_material_map` (array) — many-to-many map between activity codes and material codes
- `ui_rules` (object) — UI behaviors

## `activity_preset[]`

Each entry:

- `sequence` (int) — 1-based, strictly increasing
- `activity_code` (string) — unique within file (recommended format `ACT-###`)
- `activity_name` (string)
- `category` (string) — free-text grouping used by UI (e.g. `Pavement`, `Drainage`)
- `is_optional` (bool)

Rules:

- No duplicate `activity_code`.
- `sequence` must be contiguous and stable; ordering is the primary meaning.

## `material_preset[]`

Each entry:

- `material_code` (string) — unique within file (recommended `MAT-###`)
- `material_name` (string)
- `unit` (string) — recommended: `m³`, `m²`, `m`, `MT`, `Bags`, `Nos`, `kg`, `litres`
- `default_spec` (string) — e.g. `MoRTH`, `IRC:58`, `State SOR`
- `is_expandable` (bool) — true if users commonly split into sub-materials (e.g. grades/sources)

Rules:

- No duplicate `material_code`.
- Prefer consistent units across presets for the same material.

## `activity_material_map[]`

Each entry:

- `activity_code` (string)
- `material_code` (string)

Rules (integrity checks):

- Every `activity_code` referenced must exist in `activity_preset`.
- Every `material_code` referenced must exist in `material_preset`.
- Duplicate pairs should be avoided.

Notes:

- It is OK for some activities to have no materials mapped (e.g. approvals, inspections) and for some materials to be unmapped (optional stock items).

## `ui_rules`

Suggested keys (all booleans):

- `auto_load`
- `allow_reorder`
- `allow_remove`
- `highlight_critical`

(Importer/UI can ignore unknown keys to keep schema forward-compatible.)

## Cloning guidelines

1. Copy the closest existing preset in `/presets`.
2. Update `preset_id`, `road_category`, and (if needed) `engineering_type` / `construction_type`.
3. Edit `activity_preset`:
   - Keep sequences contiguous and unique.
   - Mark optional items with `is_optional: true` (utilities, medians, junction works, SAMI, etc.).
4. Edit `material_preset`:
   - Reuse existing material names/units where possible.
   - Set `is_expandable: true` for things like aggregates, bitumen grades, steel.
5. Update `activity_material_map`:
   - Add links only where you genuinely expect material tracking.
   - Run a simple validation step: no missing codes and no duplicates.

## Recommended validation (non-runtime)

At minimum, validate per file:

- `sequence` is 1..N without gaps
- `activity_code` set is unique
- `material_code` set is unique
- all map references resolve

(We can wire an automated validator/importer later once you confirm the target DB model.)
