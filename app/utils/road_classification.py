from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialPreset:
    name: str
    default_unit: str
    allowed_units: list[str]


# -----------------------------------------------------------------------------
# PROJECT TYPE (top level)
# -----------------------------------------------------------------------------
PROJECT_TYPES: list[str] = [
    "Road",
    "Bridge",
    "Flyover",
    "Building",
    "Utility / Pipeline",
]

# Keep legacy types supported by backend (do not break existing projects)
LEGACY_PROJECT_TYPES: list[str] = [
    "Residential",
    "Commercial",
    "Industrial",
    "Utility",
    "Other",
]


# -----------------------------------------------------------------------------
# ROAD CATEGORY (functional class)
# -----------------------------------------------------------------------------
ROAD_CATEGORIES: list[str] = [
    "Expressway",
    "National Highway (NH)",
    "State Highway (SH)",
    "Major District Road (MDR)",
    "Other District Road (ODR)",
    "Village / Rural Road (VR)",
    "Urban Road",
    "Service Road",
]


# -----------------------------------------------------------------------------
# ROAD ENGINEERING TYPES (preset drivers) grouped by road category
# (Some are broadly applicable, but UI shows the relevant set per category.)
# -----------------------------------------------------------------------------
FLEXIBLE_TYPES = [
    "Flexible Pavement – New Construction",
    "Flexible Pavement – Strengthening / Overlay",
    "Flexible Pavement – Widening",
]

RIGID_TYPES = [
    "Rigid Pavement – PQC",
    "Rigid Pavement – DLC + PQC",
    "Rigid Pavement – White Topping",
]

COMPOSITE_TYPES = [
    "Composite Pavement – Bituminous over Concrete",
]

RURAL_LOW_VOLUME_TYPES = [
    "Rural / Low Volume – WBM Road",
    "Rural / Low Volume – Gravel Road",
    "Rural / Low Volume – PMGSY Rural Road",
]

URBAN_TYPES = [
    "Urban Roads – Urban Arterial Road",
    "Urban Roads – Urban Collector Road",
    "Urban Roads – Urban Local Street",
]


ENGINEERING_TYPES_BY_CATEGORY: dict[str, list[str]] = {
    "Expressway": FLEXIBLE_TYPES + RIGID_TYPES + COMPOSITE_TYPES,
    "National Highway (NH)": FLEXIBLE_TYPES + RIGID_TYPES + COMPOSITE_TYPES,
    "State Highway (SH)": FLEXIBLE_TYPES + RIGID_TYPES + COMPOSITE_TYPES,
    "Major District Road (MDR)": FLEXIBLE_TYPES + RIGID_TYPES + COMPOSITE_TYPES,
    "Other District Road (ODR)": FLEXIBLE_TYPES + RIGID_TYPES + COMPOSITE_TYPES,
    "Village / Rural Road (VR)": RURAL_LOW_VOLUME_TYPES + FLEXIBLE_TYPES,
    "Urban Road": URBAN_TYPES + FLEXIBLE_TYPES + RIGID_TYPES,
    "Service Road": FLEXIBLE_TYPES + RIGID_TYPES,
}


# -----------------------------------------------------------------------------
# Conditional questions (smart UX) by Road Category
# Returned to UI, stored as JSON blob on Project.
# -----------------------------------------------------------------------------
CONDITIONAL_QUESTIONS_BY_CATEGORY: dict[str, list[dict[str, str]]] = {
    "Expressway": [
        {"key": "access_controlled", "label": "Access Controlled?", "type": "yesno"},
        {"key": "service_roads_required", "label": "Service Roads Required?", "type": "yesno"},
        {"key": "utility_shifting_required", "label": "Utility Shifting Required?", "type": "yesno"},
        {"key": "median_type", "label": "Median Type", "type": "text"},
    ],
    "Major District Road (MDR)": [
        {"key": "utility_shifting_required", "label": "Utility Shifting Required?", "type": "yesno"},
    ],
    "Urban Road": [
        {"key": "footpath_required", "label": "Footpath Required?", "type": "yesno"},
        {"key": "utility_ducts", "label": "Utility Ducts?", "type": "yesno"},
        {"key": "storm_water_drain", "label": "Storm Water Drain?", "type": "yesno"},
        {"key": "street_lighting", "label": "Street Lighting?", "type": "yesno"},
    ],
}


# -----------------------------------------------------------------------------
# Presets by Road Engineering Type
# Materials include default_unit + allowed_units to drive the global auto-unit
# system (Material.standard_unit + Material.allowed_units).
# -----------------------------------------------------------------------------
PRESETS_BY_ENGINEERING_TYPE: dict[str, dict[str, list]] = {
    "Flexible Pavement – New Construction": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "DBM",
            "BC",
            "Drainage",
            "Median / Barrier",
            "Road Furniture",
            "Road Marking",
            "Signage & Safety",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
            MaterialPreset("Bitumen", "MT", ["MT", "kg"]),
            MaterialPreset("Cement", "bags", ["bags", "MT"]),
            MaterialPreset("Sand", "m3", ["m3", "MT"]),
            MaterialPreset("Steel", "MT", ["MT", "kg"]),
        ],
    },
    "Flexible Pavement – Strengthening / Overlay": {
        "activities": [
            "Surface Preparation",
            "Tack Coat",
            "DBM",
            "BC",
            "Road Marking",
            "Signage & Safety",
        ],
        "materials": [
            MaterialPreset("Bitumen", "MT", ["MT", "kg"]),
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
        ],
    },
    "Flexible Pavement – Widening": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "DBM",
            "BC",
            "Shoulder works",
            "Drainage",
            "Road Marking",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
            MaterialPreset("Bitumen", "MT", ["MT", "kg"]),
            MaterialPreset("Cement", "bags", ["bags", "MT"]),
        ],
    },
    "Rigid Pavement – PQC": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "DLC",
            "PQC",
            "Joints & Curing",
            "Drainage",
            "Road Marking",
            "Signage & Safety",
        ],
        "materials": [
            MaterialPreset("Cement", "bags", ["bags", "MT"]),
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
            MaterialPreset("Sand", "m3", ["m3", "MT"]),
            MaterialPreset("Steel", "MT", ["MT", "kg"]),
        ],
    },
    "Rigid Pavement – DLC + PQC": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "DLC",
            "PQC",
            "Joints & Curing",
            "Drainage",
        ],
        "materials": [
            MaterialPreset("Cement", "bags", ["bags", "MT"]),
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
            MaterialPreset("Steel", "MT", ["MT", "kg"]),
        ],
    },
    "Rigid Pavement – White Topping": {
        "activities": [
            "Surface Preparation",
            "Bond Coat",
            "PQC (White Topping)",
            "Joints & Curing",
            "Road Marking",
        ],
        "materials": [
            MaterialPreset("Cement", "bags", ["bags", "MT"]),
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
            MaterialPreset("Steel", "MT", ["MT", "kg"]),
        ],
    },
    "Composite Pavement – Bituminous over Concrete": {
        "activities": [
            "Surface Preparation",
            "Tack Coat",
            "DBM",
            "BC",
            "Road Marking",
        ],
        "materials": [
            MaterialPreset("Bitumen", "MT", ["MT", "kg"]),
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
        ],
    },
    "Rural / Low Volume – WBM Road": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "WBM",
            "Surface Dressing",
            "Drainage",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
            MaterialPreset("Sand", "m3", ["m3", "MT"]),
        ],
    },
    "Rural / Low Volume – Gravel Road": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "Gravel Layer",
            "Compaction",
            "Drainage",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
        ],
    },
    "Rural / Low Volume – PMGSY Rural Road": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WBM/WMM",
            "Surface Dressing",
            "Drainage",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
            MaterialPreset("Cement", "bags", ["bags", "MT"]),
            MaterialPreset("Sand", "m3", ["m3", "MT"]),
        ],
    },
    "Urban Roads – Urban Arterial Road": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "DBM",
            "BC",
            "Kerb / Footpath",
            "Storm Water Drain",
            "Road Marking",
            "Street Lighting",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
            MaterialPreset("Bitumen", "MT", ["MT", "kg"]),
            MaterialPreset("Cement", "bags", ["bags", "MT"]),
            MaterialPreset("Steel", "MT", ["MT", "kg"]),
            MaterialPreset("Sand", "m3", ["m3", "MT"]),
        ],
    },
    "Urban Roads – Urban Collector Road": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "DBM",
            "BC",
            "Kerb / Footpath",
            "Storm Water Drain",
            "Road Marking",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
            MaterialPreset("Bitumen", "MT", ["MT", "kg"]),
            MaterialPreset("Cement", "bags", ["bags", "MT"]),
            MaterialPreset("Sand", "m3", ["m3", "MT"]),
        ],
    },
    "Urban Roads – Urban Local Street": {
        "activities": [
            "Earthwork",
            "Subgrade",
            "GSB",
            "WMM",
            "BC",
            "Kerb / Footpath",
            "Storm Water Drain",
        ],
        "materials": [
            MaterialPreset("Aggregate", "m3", ["m3", "MT"]),
            MaterialPreset("Bitumen", "MT", ["MT", "kg"]),
            MaterialPreset("Cement", "bags", ["bags", "MT"]),
            MaterialPreset("Sand", "m3", ["m3", "MT"]),
        ],
    },
}


def get_classification_metadata() -> dict:
    return {
        "project_types": PROJECT_TYPES,
        "legacy_project_types": LEGACY_PROJECT_TYPES,
        "road_categories": ROAD_CATEGORIES,
        "engineering_types_by_category": ENGINEERING_TYPES_BY_CATEGORY,
        "conditional_questions_by_category": CONDITIONAL_QUESTIONS_BY_CATEGORY,
    }


def get_presets_for_engineering_type(engineering_type: str | None) -> dict[str, list]:
    engineering_type = (engineering_type or "").strip()
    preset = PRESETS_BY_ENGINEERING_TYPE.get(engineering_type)
    if preset:
        return preset

    # Safe default
    return PRESETS_BY_ENGINEERING_TYPE["Flexible Pavement – New Construction"]
