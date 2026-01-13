# Admin Console – Road Preset Management (Road Preset Engine)

This module allows **system admins only** to manage Road Preset Engine presets stored in the database.

Core principle: **Admins can modify presets — but never break engineering logic.**

## Access & Permissions

- Allowed: `user.role == "admin"`
- Blocked: managers/members/viewers (no UI links; route guard rejects)

## UI Flow

1. **Dashboard**: `/admin/presets/road`
   - Table: Preset Name (alias), Road Category, Engineering Type, Construction Type, Status, User Modified, Last Updated, Actions
   - Actions: View, Edit, Clone, Disable/Enable, Reset to Default, Delete (soft)

2. **View preset (read-only)**: `/admin/presets/road/{preset_id}`
   - Shows metadata, ordered activities, materials, and activity↔material mapping.

3. **Edit preset (controlled)**: `/admin/presets/road/{preset_id}/edit`
   - Split layout:
     - Left: Activities (drag-and-drop reorder)
     - Right: Materials
     - Mapping: per-activity material checkboxes
   - Save runs validation; no partial save.

4. **Clone preset**: `/admin/presets/road/{preset_id}/clone`
   - Creates an independent copy with a new `preset_key` (generated).

## Backend Routes (Contract)

### List
- `GET /admin/presets/road?q=&status=`

### View
- `GET /admin/presets/road/{preset_id}`

### Edit form
- `GET /admin/presets/road/{preset_id}/edit`

### Update (transactional)
- `POST /admin/presets/road/{preset_id}/update`
- Form field: `payload_json` (JSON string)

Payload schema:
```json
{
  "title": "NH Flexible – Custom Variant",
  "activities": [
    {"activity_code":"GSB","activity_name":"GSB","sequence_no":1,"is_optional":false,"is_active":true},
    {"activity_code":"CUST_ACT_001","activity_name":"Local drainage","sequence_no":2,"is_optional":true,"is_active":true}
  ],
  "materials": [
    {"material_code":"MAT_GSB","material_name":"GSB","unit":"m3","default_spec":"MORTH","is_active":true}
  ],
  "mappings": [
    {"activity_code":"GSB","material_code":"MAT_GSB"}
  ]
}
```

### Disable/Enable
- `POST /admin/presets/road/{preset_id}/toggle`

### Reset to Default Seed
- `POST /admin/presets/road/{preset_id}/reset`
- Guard: blocked if preset is linked to any active project (`projects.road_preset_key == road_presets.preset_key`).

### Soft Delete
- `POST /admin/presets/road/{preset_id}/delete`
- Guard: blocked if linked to any active project.

## Validation & Guardrails

Enforced on save (server-side, transactional):

- **Not editable**: `preset_key`, `road_category`, `engineering_type`, `construction_type`, activity `category`.
- **Core activities/materials cannot be removed** (tokens: GSB/PQC/DLC/DBM/BC).
- **Sequence gaps auto-corrected**: active activities are renumbered contiguously starting at 1.
- **Removing/disabling an activity clears its mappings** (mapping table is rebuilt).
- **Mapping references validated**: cannot point to unknown codes.
- **Minimum viability**: at least one active activity and one active material.

If validation fails:
- request is rejected
- DB transaction is rolled back

## Audit Logging

All admin actions write entries into `activity_logs` with:
- actor (user_id/username/role)
- action (CREATE/UPDATE/DELETE)
- entity_type = `RoadPreset`
- entity_id
- `old_value`/`new_value` JSON snapshots
