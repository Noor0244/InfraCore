from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.road_stretch import RoadStretch
from app.models.road_geometry import RoadGeometry
from app.models.pavement_design import PavementDesign


def _soft_geometry_warnings(stretch: RoadStretch, geometry: RoadGeometry | None) -> list[str]:
    warnings: list[str] = []
    if not geometry:
        return warnings

    if (stretch.road_category or "") == "Expressway":
        if geometry.lanes is not None and geometry.lanes < 4:
            warnings.append("Expressway requires minimum 4 lanes (soft warning).")
        if not (geometry.median_type or "").strip():
            warnings.append("Expressway typically requires a median (soft warning).")
    return warnings


def _pavement_layers_for_design(stretch: RoadStretch, pavement: PavementDesign | None) -> list[dict[str, Any]]:
    if not pavement:
        return []

    engineering = (stretch.engineering_type or "").strip()

    if engineering == "Flexible":
        return [
            {"layer": "GSB", "thickness_mm": pavement.gsb_thickness_mm},
            {"layer": "WMM", "thickness_mm": pavement.wmm_thickness_mm},
            {"layer": "DBM", "thickness_mm": pavement.dbm_thickness_mm},
            {"layer": "BC", "thickness_mm": pavement.bc_thickness_mm},
        ]
    if engineering == "Rigid":
        return [
            {"layer": "PQC Slab", "thickness_mm": pavement.slab_thickness_mm},
            {"layer": "Concrete Grade", "value": pavement.concrete_grade},
            {"layer": "Joint Spacing (m)", "value": pavement.joint_spacing_m},
            {"layer": "Dowel Diameter (mm)", "value": pavement.dowel_diameter_mm},
            {"layer": "Tie Bar Diameter (mm)", "value": pavement.tie_bar_diameter_mm},
            {"layer": "k-value", "value": pavement.k_value},
        ]
    if engineering == "Overlay":
        return [
            {"layer": "Existing Pavement", "value": pavement.existing_pavement_type},
            {"layer": "Overlay Material", "value": pavement.overlay_material},
            {"layer": "Overlay Thickness (mm)", "thickness_mm": pavement.overlay_thickness_mm},
        ]

    return []


def build_dpr_dataset(db: Session, project_id: int) -> dict[str, Any]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError("Project not found")

    stretches = (
        db.query(RoadStretch)
        .filter(RoadStretch.project_id == project_id, RoadStretch.is_active == True)  # noqa: E712
        .order_by(RoadStretch.sequence_no.asc())
        .all()
    )

    stretch_sections: list[dict[str, Any]] = []
    chainage_summary: list[dict[str, Any]] = []
    pavement_tables: list[dict[str, Any]] = []

    for stretch in stretches:
        geometry = (
            db.query(RoadGeometry)
            .filter(RoadGeometry.stretch_id == stretch.id)
            .first()
        )
        pavement = (
            db.query(PavementDesign)
            .filter(PavementDesign.stretch_id == stretch.id)
            .first()
        )

        warnings = _soft_geometry_warnings(stretch, geometry)

        stretch_sections.append(
            {
                "stretch": stretch,
                "geometry": geometry,
                "pavement": pavement,
                "warnings": warnings,
            }
        )

        chainage_summary.append(
            {
                "stretch_id": stretch.id,
                "stretch_name": stretch.stretch_name,
                "start_chainage": stretch.start_chainage,
                "end_chainage": stretch.end_chainage,
                "length_m": stretch.length_m,
                "road_category": stretch.road_category,
                "engineering_type": stretch.engineering_type,
                "lanes": geometry.lanes if geometry else None,
                "carriageway_width_m": geometry.carriageway_width_m if geometry else None,
            }
        )

        pavement_tables.append(
            {
                "stretch_id": stretch.id,
                "stretch_name": stretch.stretch_name,
                "engineering_type": stretch.engineering_type,
                "layers": _pavement_layers_for_design(stretch, pavement),
            }
        )

    return {
        "project": project,
        "stretches": stretch_sections,
        "chainage_summary": chainage_summary,
        "pavement_tables": pavement_tables,
    }
