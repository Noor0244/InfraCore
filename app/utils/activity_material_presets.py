from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialDef:
    name: str
    default_unit: str
    allowed_units: list[str]


@dataclass(frozen=True)
class ActivityMaterialLink:
    activity: str
    material: MaterialDef
    consumption_rate: float


def _mat(name: str, default_unit: str, allowed_units: list[str] | None = None) -> MaterialDef:
    allowed = [str(u or "").strip() for u in (allowed_units or []) if str(u or "").strip()]
    if not allowed:
        allowed = [default_unit]
    if default_unit not in allowed:
        allowed.insert(0, default_unit)
    return MaterialDef(name=name, default_unit=default_unit, allowed_units=allowed)


# NOTE: Rates below are best-effort starter defaults.
# They are meant to be edited per project (soil/grade/spec varies).
# Unit basis: "material per 1 unit of activity".

PRESET_LINKS_BY_PROJECT_TYPE: dict[str, list[ActivityMaterialLink]] = {
    "Building": [
        ActivityMaterialLink("Excavation", _mat("Diesel", "liters", ["liters"]), 0.0),
        ActivityMaterialLink("PCC / Blinding", _mat("Cement", "bags", ["bags", "MT"]), 8.0),
        ActivityMaterialLink("PCC / Blinding", _mat("Sand", "m3", ["m3", "MT"]), 0.45),
        ActivityMaterialLink("PCC / Blinding", _mat("Coarse Aggregate", "m3", ["m3", "MT"]), 0.9),
        ActivityMaterialLink("Footings / Foundation", _mat("Cement", "bags", ["bags", "MT"]), 8.0),
        ActivityMaterialLink("Footings / Foundation", _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]), 0.1),
        ActivityMaterialLink("Footings / Foundation", _mat("Sand", "m3", ["m3", "MT"]), 0.45),
        ActivityMaterialLink("Footings / Foundation", _mat("Coarse Aggregate", "m3", ["m3", "MT"]), 0.9),
        ActivityMaterialLink("RCC Columns", _mat("Cement", "bags", ["bags", "MT"]), 8.0),
        ActivityMaterialLink("RCC Columns", _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]), 0.12),
        ActivityMaterialLink("RCC Columns", _mat("Binding Wire", "kg", ["kg", "MT"]), 1.5),
        ActivityMaterialLink("RCC Columns", _mat("Shuttering / Formwork", "sqm", ["sqm"]), 8.0),
        ActivityMaterialLink("RCC Beams", _mat("Cement", "bags", ["bags", "MT"]), 8.0),
        ActivityMaterialLink("RCC Beams", _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]), 0.12),
        ActivityMaterialLink("RCC Beams", _mat("Binding Wire", "kg", ["kg", "MT"]), 1.5),
        ActivityMaterialLink("RCC Beams", _mat("Shuttering / Formwork", "sqm", ["sqm"]), 10.0),
        ActivityMaterialLink("RCC Slab", _mat("Cement", "bags", ["bags", "MT"]), 8.0),
        ActivityMaterialLink("RCC Slab", _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]), 0.1),
        ActivityMaterialLink("RCC Slab", _mat("Binding Wire", "kg", ["kg", "MT"]), 1.2),
        ActivityMaterialLink("RCC Slab", _mat("Shuttering / Formwork", "sqm", ["sqm"]), 12.0),
        ActivityMaterialLink("Masonry (Brick/Block)", _mat("Bricks", "nos", ["nos"]), 50.0),
        ActivityMaterialLink("Masonry (Brick/Block)", _mat("Cement", "bags", ["bags", "MT"]), 0.8),
        ActivityMaterialLink("Masonry (Brick/Block)", _mat("Sand", "m3", ["m3", "MT"]), 0.03),
        ActivityMaterialLink("Plastering", _mat("Cement", "bags", ["bags", "MT"]), 0.3),
        ActivityMaterialLink("Plastering", _mat("Sand", "m3", ["m3", "MT"]), 0.02),
        ActivityMaterialLink("Flooring / Tiling", _mat("Tiles", "sqm", ["sqm"]), 1.0),
        ActivityMaterialLink("Flooring / Tiling", _mat("Cement", "bags", ["bags", "MT"]), 0.05),
        ActivityMaterialLink("Painting", _mat("Putty", "kg", ["kg"]), 0.3),
        ActivityMaterialLink("Painting", _mat("Paint", "liters", ["liters"]), 0.12),
        ActivityMaterialLink("Electrical (Conduits & Wiring)", _mat("Electrical Conduit", "m", ["m"]), 0.0),
        ActivityMaterialLink("Electrical (Conduits & Wiring)", _mat("Electrical Cable", "m", ["m"]), 0.0),
        ActivityMaterialLink("Plumbing (Pipes & Fixtures)", _mat("Plumbing Pipe (UPVC/CPVC)", "m", ["m"]), 0.0),
        ActivityMaterialLink("Plumbing (Pipes & Fixtures)", _mat("Sanitary Fixtures", "nos", ["nos"]), 0.0),
        ActivityMaterialLink("Waterproofing", _mat("Waterproofing Compound", "kg", ["kg"]), 0.15),
    ],
    "Residential": [
        ActivityMaterialLink("Foundation", _mat("Cement", "bags", ["bags", "MT"]), 8.0),
        ActivityMaterialLink("Foundation", _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]), 0.1),
        ActivityMaterialLink("RCC Structure", _mat("Cement", "bags", ["bags", "MT"]), 8.0),
        ActivityMaterialLink("RCC Structure", _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]), 0.1),
        ActivityMaterialLink("Masonry", _mat("Bricks", "nos", ["nos"]), 50.0),
        ActivityMaterialLink("Plastering", _mat("Cement", "bags", ["bags", "MT"]), 0.3),
        ActivityMaterialLink("Painting", _mat("Paint", "liters", ["liters"]), 0.12),
    ],
    "Commercial": [
        ActivityMaterialLink("Foundation", _mat("Cement", "bags", ["bags", "MT"]), 8.0),
        ActivityMaterialLink("RCC Structure", _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]), 0.1),
        ActivityMaterialLink("MEP Rough-in", _mat("Electrical Cable", "m", ["m"]), 0.0),
        ActivityMaterialLink("MEP Rough-in", _mat("Plumbing Pipe (UPVC/CPVC)", "m", ["m"]), 0.0),
        ActivityMaterialLink("False Ceiling", _mat("Gypsum Board", "sheets", ["sheets"]), 0.0),
        ActivityMaterialLink("Painting", _mat("Paint", "liters", ["liters"]), 0.12),
    ],
    "Industrial": [
        ActivityMaterialLink("Foundation (Isolated/Combined/Raft)", _mat("Cement", "bags", ["bags", "MT"]), 8.0),
        ActivityMaterialLink("RCC / Steel Structure", _mat("Structural Steel", "MT", ["MT", "kg"]), 0.0),
        ActivityMaterialLink("Floor Slab (Industrial)", _mat("Concrete (RMC)", "m3", ["m3"]), 1.0),
        ActivityMaterialLink("Cladding / Roofing", _mat("Roofing Sheets", "sqm", ["sqm"]), 0.0),
    ],
    "Bridge": [
        ActivityMaterialLink("Piling", _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]), 0.0),
        ActivityMaterialLink("Piling", _mat("Cement", "bags", ["bags", "MT"]), 0.0),
        ActivityMaterialLink("Pile Cap", _mat("Concrete (RMC)", "m3", ["m3"]), 1.0),
        ActivityMaterialLink("Pile Cap", _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]), 0.12),
        ActivityMaterialLink("Pier / Pier Cap", _mat("Concrete (RMC)", "m3", ["m3"]), 1.0),
        ActivityMaterialLink("Pier / Pier Cap", _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]), 0.12),
        ActivityMaterialLink("Deck Slab", _mat("Concrete (RMC)", "m3", ["m3"]), 1.0),
        ActivityMaterialLink("Deck Slab", _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]), 0.1),
        ActivityMaterialLink("Bearing Installation", _mat("Bearings", "nos", ["nos"]), 0.0),
        ActivityMaterialLink("Expansion Joints", _mat("Expansion Joint", "m", ["m"]), 0.0),
        ActivityMaterialLink("Wearing Coat", _mat("Bitumen", "MT", ["MT", "kg"]), 0.0),
        ActivityMaterialLink("Parapet / Crash Barrier", _mat("Crash Barrier", "m", ["m"]), 0.0),
    ],
    "Flyover": [
        ActivityMaterialLink("Piling", _mat("Reinforcement Steel (Rebar)", "MT", ["MT", "kg"]), 0.0),
        ActivityMaterialLink("Pile Cap", _mat("Concrete (RMC)", "m3", ["m3"]), 1.0),
        ActivityMaterialLink("Deck Slab / Segment Stitching", _mat("Concrete (RMC)", "m3", ["m3"]), 1.0),
        ActivityMaterialLink("Expansion Joints", _mat("Expansion Joint", "m", ["m"]), 0.0),
        ActivityMaterialLink("Wearing Coat", _mat("Bitumen", "MT", ["MT", "kg"]), 0.0),
        ActivityMaterialLink("Lighting & Signage", _mat("Electrical Cable", "m", ["m"]), 0.0),
        ActivityMaterialLink("Lighting & Signage", _mat("Lighting Fixtures", "nos", ["nos"]), 0.0),
        ActivityMaterialLink("Crash Barrier / Parapet", _mat("Crash Barrier", "m", ["m"]), 0.0),
    ],
    "Utility / Pipeline": [
        ActivityMaterialLink("Trenching", _mat("Diesel", "liters", ["liters"]), 0.0),
        ActivityMaterialLink("Pipe Laying", _mat("Pipe (HDPE/DI/CI/MS)", "m", ["m"]), 1.0),
        ActivityMaterialLink("Jointing / Welding", _mat("Welding Rod / Electrode", "kg", ["kg"]), 0.0),
        ActivityMaterialLink("Valve Chamber / Manhole", _mat("Concrete (RMC)", "m3", ["m3"]), 1.0),
        ActivityMaterialLink("Backfilling & Compaction", _mat("Sand", "m3", ["m3", "MT"]), 0.0),
        ActivityMaterialLink("Reinstatement (Road/Footpath)", _mat("Bitumen", "MT", ["MT", "kg"]), 0.0),
    ],
    "Utility": [
        ActivityMaterialLink("Trenching", _mat("Diesel", "liters", ["liters"]), 0.0),
        ActivityMaterialLink("Laying", _mat("Pipe (HDPE/DI)", "m", ["m"]), 1.0),
    ],
    "Other": [
        ActivityMaterialLink("Execution", _mat("Cement", "bags", ["bags", "MT"]), 0.0),
    ],
}


PRESET_LINKS_BY_ENGINEERING_TYPE: dict[str, list[ActivityMaterialLink]] = {
    "Flexible Pavement – New Construction": [
        ActivityMaterialLink("GSB", _mat("Aggregate", "m3", ["m3", "MT"]), 0.0),
        ActivityMaterialLink("WMM", _mat("Aggregate", "m3", ["m3", "MT"]), 0.0),
        ActivityMaterialLink("DBM", _mat("Aggregate", "m3", ["m3", "MT"]), 0.0),
        ActivityMaterialLink("DBM", _mat("Bitumen", "MT", ["MT", "kg"]), 0.0),
        ActivityMaterialLink("BC", _mat("Aggregate", "m3", ["m3", "MT"]), 0.0),
        ActivityMaterialLink("BC", _mat("Bitumen", "MT", ["MT", "kg"]), 0.0),
        ActivityMaterialLink("Drainage", _mat("Concrete (RMC)", "m3", ["m3"]), 0.0),
    ],
    "Rigid Pavement – PQC": [
        ActivityMaterialLink("DLC", _mat("Cement", "bags", ["bags", "MT"]), 0.0),
        ActivityMaterialLink("DLC", _mat("Aggregate", "m3", ["m3", "MT"]), 0.0),
        ActivityMaterialLink("PQC", _mat("Cement", "bags", ["bags", "MT"]), 0.0),
        ActivityMaterialLink("PQC", _mat("Aggregate", "m3", ["m3", "MT"]), 0.0),
        ActivityMaterialLink("PQC", _mat("Steel", "MT", ["MT", "kg"]), 0.0),
    ],
    "Rural / Low Volume – WBM Road": [
        ActivityMaterialLink("WBM", _mat("Aggregate", "m3", ["m3", "MT"]), 0.0),
        ActivityMaterialLink("Surface Dressing", _mat("Bitumen", "MT", ["MT", "kg"]), 0.0),
    ],
}


def get_activity_material_links(project_type: str | None, road_engineering_type: str | None = None) -> list[ActivityMaterialLink]:
    pt = (project_type or "").strip() or ""
    if pt.lower() == "road":
        et = (road_engineering_type or "").strip()
        links = PRESET_LINKS_BY_ENGINEERING_TYPE.get(et)
        return list(links or [])

    links = PRESET_LINKS_BY_PROJECT_TYPE.get(pt)
    if links:
        return list(links)

    # Safe fallback
    return list(PRESET_LINKS_BY_PROJECT_TYPE.get("Building") or [])


def serialize_links(links: list[ActivityMaterialLink]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for link in links:
        activity = (link.activity or "").strip()
        if not activity:
            continue
        m = link.material
        name = (m.name or "").strip()
        if not name:
            continue
        unit = (m.default_unit or "unit").strip() or "unit"
        allowed = [str(u or "").strip() for u in (m.allowed_units or []) if str(u or "").strip()]
        if not allowed:
            allowed = [unit]
        if unit not in allowed:
            allowed.insert(0, unit)
        out.append(
            {
                "activity": activity,
                "material": {"name": name, "default_unit": unit, "allowed_units": allowed},
                "consumption_rate": float(link.consumption_rate or 0),
            }
        )
    return out
