from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialPreset:
    name: str
    unit: str


# -----------------------------------------------------------------------------
# Road-type specific standard presets
#
# Notes:
# - Keys match the Road Type values used in `app/templates/new_project.html`.
# - Activities are project-scoped (created into `activities` for the new project).
# - Materials are global (created into `materials` if missing) and linked to the
#   project via `planned_materials`.
# -----------------------------------------------------------------------------
ROAD_TYPE_PRESETS: dict[str, dict[str, list]] = {
    "National Highway (NH)": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "Prime Coat",
            "DBM",
            "BC",
            "Drainage",
            "Road furniture",
            "Road marking",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3"),
            MaterialPreset("Bitumen", "MT"),
            MaterialPreset("Cement", "bags"),
            MaterialPreset("Steel", "MT"),
            MaterialPreset("Sand", "m3"),
        ],
    },
    "State Highway (SH)": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "DBM",
            "BC",
            "Drainage",
            "Shoulder works",
            "Road furniture",
            "Road marking",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3"),
            MaterialPreset("Bitumen", "MT"),
            MaterialPreset("Cement", "bags"),
            MaterialPreset("Steel", "MT"),
            MaterialPreset("Sand", "m3"),
        ],
    },
    "Major District Road (MDR)": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "DBM",
            "BC",
            "Drainage",
            "Shoulder works",
            "Road marking",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3"),
            MaterialPreset("Bitumen", "MT"),
            MaterialPreset("Cement", "bags"),
            MaterialPreset("Sand", "m3"),
        ],
    },
    "Other District Road (ODR)": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "Surface course",
            "Drainage",
            "Shoulder works",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3"),
            MaterialPreset("Bitumen", "MT"),
            MaterialPreset("Cement", "bags"),
            MaterialPreset("Sand", "m3"),
        ],
    },
    "Village Road (VR)": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WBM/WMM",
            "Surface dressing",
            "Drainage",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3"),
            MaterialPreset("Cement", "bags"),
            MaterialPreset("Sand", "m3"),
        ],
    },
    "Urban Road": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "DBM",
            "BC",
            "Kerb / Footpath",
            "Drainage",
            "Road marking",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3"),
            MaterialPreset("Bitumen", "MT"),
            MaterialPreset("Cement", "bags"),
            MaterialPreset("Sand", "m3"),
            MaterialPreset("Steel", "MT"),
        ],
    },
    "Expressway": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "DBM",
            "BC",
            "Drainage",
            "Median / Barrier",
            "Signage & safety",
            "Road marking",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3"),
            MaterialPreset("Bitumen", "MT"),
            MaterialPreset("Cement", "bags"),
            MaterialPreset("Steel", "MT"),
            MaterialPreset("Sand", "m3"),
        ],
    },
    "Service Road": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "DBM",
            "BC",
            "Drainage",
            "Road marking",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3"),
            MaterialPreset("Bitumen", "MT"),
            MaterialPreset("Cement", "bags"),
            MaterialPreset("Sand", "m3"),
        ],
    },
}


def get_road_type_preset(road_type: str | None) -> dict[str, list]:
    road_type = (road_type or "").strip()
    preset = ROAD_TYPE_PRESETS.get(road_type)
    if preset:
        return preset

    # Safe fallback
    return {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "DBM",
            "BC",
            "Drainage",
            "Shoulder works",
            "Road furniture",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3"),
            MaterialPreset("Bitumen", "MT"),
            MaterialPreset("Cement", "bags"),
            MaterialPreset("Steel", "MT"),
            MaterialPreset("Sand", "m3"),
        ],
    }
