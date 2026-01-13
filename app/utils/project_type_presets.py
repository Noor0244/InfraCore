from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialPreset:
    name: str
    default_unit: str
    allowed_units: list[str]


def _mat(name: str, default_unit: str, allowed_units: list[str] | None = None) -> MaterialPreset:
    allowed = list(allowed_units or [])
    if not allowed:
        allowed = [default_unit]
    if default_unit not in allowed:
        allowed.insert(0, default_unit)
    return MaterialPreset(name=name, default_unit=default_unit, allowed_units=allowed)


# NOTE: These are practical, high-coverage starter presets.
# They are intentionally editable in the UI at project creation.
PRESETS_BY_PROJECT_TYPE: dict[str, dict[str, list]] = {
    "Building": {
        "activities": [
            "Survey & Setting Out",
            "Site Clearing",
            "Excavation",
            "PCC / Blinding",
            "Footings / Foundation",
            "Plinth Beam",
            "Backfilling & Compaction",
            "RCC Columns",
            "RCC Beams",
            "RCC Slab",
            "Staircase",
            "Masonry (Brick/Block)",
            "Lintel & Chajja",
            "Plastering",
            "Flooring / Tiling",
            "Waterproofing",
            "Doors & Windows",
            "Painting",
            "Electrical (Conduits & Wiring)",
            "Plumbing (Pipes & Fixtures)",
            "HVAC / Fire Fighting (if applicable)",
            "External Works",
            "Testing & Commissioning",
            "Handover / Snag List",
        ],
        "materials": [
            _mat("Cement", "bags", ["bags", "MT"]),
            _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]),
            _mat("Binding Wire", "kg", ["kg", "MT"]),
            _mat("Sand", "m3", ["m3", "MT"]),
            _mat("Coarse Aggregate", "m3", ["m3", "MT"]),
            _mat("Fine Aggregate (M-Sand)", "m3", ["m3", "MT"]),
            _mat("Bricks", "nos", ["nos"]),
            _mat("AAC Blocks", "nos", ["nos"]),
            _mat("Concrete (RMC)", "m3", ["m3"]),
            _mat("Shuttering / Formwork", "sqm", ["sqm"]),
            _mat("Plywood", "sheets", ["sheets"]),
            _mat("Scaffolding", "sqm", ["sqm"]),
            _mat("Admixture", "liters", ["liters"]),
            _mat("Waterproofing Compound", "kg", ["kg"]),
            _mat("Tiles", "sqm", ["sqm"]),
            _mat("Granite / Stone", "sqm", ["sqm"]),
            _mat("Gypsum / POP", "kg", ["kg", "MT"]),
            _mat("Putty", "kg", ["kg"]),
            _mat("Paint", "liters", ["liters"]),
            _mat("Electrical Cable", "m", ["m"]),
            _mat("Electrical Conduit", "m", ["m"]),
            _mat("Switches & Sockets", "nos", ["nos"]),
            _mat("Plumbing Pipe (UPVC/CPVC)", "m", ["m"]),
            _mat("Plumbing Fittings", "nos", ["nos"]),
            _mat("Sanitary Fixtures", "nos", ["nos"]),
            _mat("MS/SS Railing", "m", ["m"]),
            _mat("Glass / Glazing", "sqm", ["sqm"]),
            _mat("Door Shutters", "nos", ["nos"]),
            _mat("Window Frames", "nos", ["nos"]),
        ],
    },
    "Residential": {
        "activities": [
            "Survey & Setting Out",
            "Excavation",
            "Foundation",
            "RCC Structure",
            "Masonry",
            "Plastering",
            "Flooring",
            "Electrical",
            "Plumbing",
            "Painting",
            "Finishing & Handover",
        ],
        "materials": [
            _mat("Cement", "bags", ["bags", "MT"]),
            _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]),
            _mat("Sand", "m3", ["m3", "MT"]),
            _mat("Coarse Aggregate", "m3", ["m3", "MT"]),
            _mat("Bricks", "nos", ["nos"]),
            _mat("Paint", "liters", ["liters"]),
            _mat("Electrical Cable", "m", ["m"]),
            _mat("Plumbing Pipe (UPVC/CPVC)", "m", ["m"]),
        ],
    },
    "Commercial": {
        "activities": [
            "Survey & Setting Out",
            "Excavation",
            "Foundation",
            "RCC Structure",
            "Masonry / Partition",
            "Plastering",
            "MEP Rough-in",
            "False Ceiling",
            "Flooring",
            "Painting",
            "MEP Fit-out",
            "Testing & Commissioning",
            "Handover",
        ],
        "materials": [
            _mat("Cement", "bags", ["bags", "MT"]),
            _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]),
            _mat("Sand", "m3", ["m3", "MT"]),
            _mat("Coarse Aggregate", "m3", ["m3", "MT"]),
            _mat("Concrete (RMC)", "m3", ["m3"]),
            _mat("Gypsum Board", "sheets", ["sheets"]),
            _mat("Electrical Cable", "m", ["m"]),
            _mat("MEP Accessories", "nos", ["nos"]),
            _mat("Paint", "liters", ["liters"]),
        ],
    },
    "Industrial": {
        "activities": [
            "Survey & Setting Out",
            "Earthwork & Grading",
            "Foundation (Isolated/Combined/Raft)",
            "RCC / Steel Structure",
            "Floor Slab (Industrial)",
            "Cladding / Roofing",
            "Equipment Foundations",
            "Utilities & Services",
            "Electrical & Instrumentation",
            "Testing & Commissioning",
        ],
        "materials": [
            _mat("Cement", "bags", ["bags", "MT"]),
            _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]),
            _mat("Structural Steel", "MT", ["MT", "kg"]),
            _mat("Sand", "m3", ["m3", "MT"]),
            _mat("Coarse Aggregate", "m3", ["m3", "MT"]),
            _mat("Concrete (RMC)", "m3", ["m3"]),
            _mat("Grouting", "kg", ["kg"]),
            _mat("Anchor Bolts", "nos", ["nos"]),
        ],
    },
    "Bridge": {
        "activities": [
            "Survey & Setting Out",
            "Traffic Diversion / Management",
            "Boreholes & Geotechnical",
            "Piling",
            "Pile Cap",
            "Pier / Pier Cap",
            "Abutment",
            "Wing Wall / Return Wall",
            "Bearing Installation",
            "Girder Casting / Fabrication",
            "Girder Launching / Erection",
            "Deck Slab",
            "Parapet / Crash Barrier",
            "Expansion Joints",
            "Wearing Coat",
            "Drainage Spouts",
            "Approach Road Works",
            "Finishing & Safety",
        ],
        "materials": [
            _mat("Cement", "bags", ["bags", "MT"]),
            _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]),
            _mat("Prestressing Strand", "MT", ["MT", "kg"]),
            _mat("Sheathing Duct", "m", ["m"]),
            _mat("Anchor Cone / Wedges", "nos", ["nos"]),
            _mat("Concrete (RMC)", "m3", ["m3"]),
            _mat("Sand", "m3", ["m3", "MT"]),
            _mat("Coarse Aggregate", "m3", ["m3", "MT"]),
            _mat("Shuttering / Formwork", "sqm", ["sqm"]),
            _mat("Admixture", "liters", ["liters"]),
            _mat("Bearings", "nos", ["nos"]),
            _mat("Expansion Joint", "m", ["m"]),
            _mat("Bitumen", "MT", ["MT", "kg"]),
            _mat("Geotextile", "sqm", ["sqm"]),
            _mat("Elastomeric Pads", "nos", ["nos"]),
            _mat("Drainage Spouts", "nos", ["nos"]),
            _mat("Crash Barrier", "m", ["m"]),
            _mat("Epoxy / Grout", "kg", ["kg"]),
        ],
    },
    "Flyover": {
        "activities": [
            "Survey & Setting Out",
            "Traffic Diversion / Management",
            "Utility Shifting",
            "Piling",
            "Pile Cap",
            "Pier / Pier Cap",
            "Segment Casting / Girder Fabrication",
            "Launching / Erection",
            "Deck Slab / Segment Stitching",
            "Crash Barrier / Parapet",
            "Expansion Joints",
            "Wearing Coat",
            "Drainage",
            "Approach Road Works",
            "Lighting & Signage",
            "Finishing & Safety",
        ],
        "materials": [
            _mat("Cement", "bags", ["bags", "MT"]),
            _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]),
            _mat("Prestressing Strand", "MT", ["MT", "kg"]),
            _mat("Sheathing Duct", "m", ["m"]),
            _mat("Concrete (RMC)", "m3", ["m3"]),
            _mat("Sand", "m3", ["m3", "MT"]),
            _mat("Coarse Aggregate", "m3", ["m3", "MT"]),
            _mat("Bearings", "nos", ["nos"]),
            _mat("Expansion Joint", "m", ["m"]),
            _mat("Bitumen", "MT", ["MT", "kg"]),
            _mat("Electrical Cable", "m", ["m"]),
            _mat("Lighting Fixtures", "nos", ["nos"]),
            _mat("Signage", "nos", ["nos"]),
            _mat("Crash Barrier", "m", ["m"]),
        ],
    },
    "Utility / Pipeline": {
        "activities": [
            "Survey & Marking",
            "Trenching",
            "Bedding",
            "Pipe Laying",
            "Jointing / Welding",
            "Valve Chamber / Manhole",
            "Backfilling & Compaction",
            "Pressure Testing",
            "Disinfection / Flushing (if applicable)",
            "Commissioning",
            "Reinstatement (Road/Footpath)",
        ],
        "materials": [
            _mat("Pipe (HDPE/DI/CI/MS)", "m", ["m"]),
            _mat("Fittings", "nos", ["nos"]),
            _mat("Valves", "nos", ["nos"]),
            _mat("Gaskets / Rubber Rings", "nos", ["nos"]),
            _mat("Solvent Cement / Adhesive", "kg", ["kg"]),
            _mat("Welding Rod / Electrode", "kg", ["kg"]),
            _mat("Sand", "m3", ["m3", "MT"]),
            _mat("Aggregate", "m3", ["m3", "MT"]),
            _mat("Concrete (RMC)", "m3", ["m3"]),
            _mat("RCC Covers", "nos", ["nos"]),
            _mat("Warning Tape", "m", ["m"]),
            _mat("Cable (if utility)", "m", ["m"]),
            _mat("Marker Posts", "nos", ["nos"]),
            _mat("HDPE Coupler", "nos", ["nos"]),
        ],
    },
    "Utility": {  # legacy
        "activities": [
            "Survey & Marking",
            "Trenching",
            "Laying",
            "Backfilling",
            "Testing & Commissioning",
        ],
        "materials": [
            _mat("Sand", "m3", ["m3", "MT"]),
            _mat("Aggregate", "m3", ["m3", "MT"]),
            _mat("Pipe (HDPE/DI)", "m", ["m"]),
        ],
    },
}


def suggest_activity_units(project_type: str | None, activity_name: str | None) -> list[str]:
    """Best-effort unit suggestions for activity planning.

    This is intentionally heuristic + editable by the user (unit field remains free-text).
    """
    pt = (project_type or "").strip().lower()
    name = (activity_name or "").strip().lower()
    if not name:
        return []

    units: list[str] = []

    # Road-ish defaults
    if pt == "road":
        if any(k in name for k in ["earthwork", "subgrade", "gsb", "wmm", "dbm", "bc", "pqc", "dlc"]):
            units += ["m3", "sqm", "km"]
        if any(k in name for k in ["mark", "sign", "barrier", "median", "furniture"]):
            units += ["m", "nos", "sqm"]
        if "drain" in name:
            units += ["m"]

    # Generic heuristics
    if any(k in name for k in ["excavat", "earthwork", "pcc", "concrete", "rcc", "deck slab", "slab", "beam", "column", "footing", "foundation", "pile cap", "pier", "abutment", "backfill", "bedding", "grout"]):
        units += ["m3"]

    if any(k in name for k in ["piling", "pipe", "cable", "conduit", "duct", "trench", "laying", "launch", "erection", "joint", "welding"]):
        units += ["m"]

    if any(k in name for k in ["plaster", "paint", "tile", "floor", "false ceiling", "waterproof", "formwork", "shuttering", "cladding", "roof"]):
        units += ["sqm"]

    if any(k in name for k in ["door", "window", "fixture", "bearing", "valve", "manhole", "chamber", "lighting", "signage"]):
        units += ["nos"]

    if any(k in name for k in ["survey", "setting out", "mobilization", "commission", "testing", "handover", "snag", "safety", "traffic"]):
        units += ["nos"]

    # De-dupe while preserving order
    out: list[str] = []
    seen: set[str] = set()
    for u in units:
        u2 = str(u or "").strip()
        if not u2:
            continue
        key = u2.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(u2)

    return out[:10]


def get_presets_for_project_type(project_type: str | None) -> dict[str, list]:
    pt = (project_type or "").strip()
    if not pt:
        return {"activities": [], "materials": []}

    preset = PRESETS_BY_PROJECT_TYPE.get(pt)
    if preset:
        return preset

    # Safe fallbacks for unknown/Other legacy types
    if pt in ("Other",):
        return {
            "activities": ["Survey & Setting Out", "Mobilization", "Execution", "Testing & Handover"],
            "materials": [_mat("Cement", "bags", ["bags", "MT"]), _mat("Steel", "MT", ["MT", "kg"])],
        }

    # Default to Building-like if unknown
    return PRESETS_BY_PROJECT_TYPE["Building"]


def serialize_presets(preset: dict[str, list]) -> dict[str, list]:
    materials = preset.get("materials", [])
    activities = preset.get("activities", [])

    out_materials: list[dict[str, object]] = []
    for m in materials:
        if isinstance(m, MaterialPreset):
            out_materials.append(
                {
                    "name": m.name,
                    "default_unit": m.default_unit,
                    "allowed_units": list(m.allowed_units),
                }
            )
        elif isinstance(m, dict):
            name = str(m.get("name") or "").strip()
            if not name:
                continue
            unit = str(m.get("default_unit") or m.get("unit") or "unit").strip() or "unit"
            allowed = m.get("allowed_units")
            if not isinstance(allowed, list) or not allowed:
                allowed = [unit]
            allowed = [str(u or "").strip() for u in allowed if str(u or "").strip()]
            if unit not in allowed:
                allowed.insert(0, unit)
            out_materials.append({"name": name, "default_unit": unit, "allowed_units": allowed})

    out_activities = [str(a).strip() for a in activities if str(a).strip()]
    return {"activities": out_activities, "materials": out_materials}
