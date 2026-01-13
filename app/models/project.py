from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean, Text
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    # ---------- BASIC INFO ----------
    name = Column(String(255), nullable=False)

    project_code = Column(String(100), nullable=True)
    client_authority = Column(String(255), nullable=True)
    contractor = Column(String(255), nullable=True)
    consultant_pmc = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    status = Column(String(20), default="active", nullable=False)

    # ---------- ROAD TYPE ----------
    road_type = Column(String(100), nullable=False)
    lanes = Column(Integer, nullable=False)
    road_width = Column(Float, nullable=False)
    road_length_km = Column(Float, nullable=False)

    carriageway_width = Column(Float, nullable=True)
    shoulder_type = Column(String(100), nullable=True)
    median_type = Column(String(100), nullable=True)

    # ---------- NEW: PROJECT TYPE & ROAD CONSTRUCTION ----------
    # Top-level project type (e.g., Residential, Commercial, Road, ...)
    project_type = Column(String(50), nullable=False, server_default="")

    # ---------- ROAD METADATA (Road projects only; optional / backward-compatible) ----------
    # Road Name / Package No is already supported via `project_code`.
    road_name = Column(String(255), nullable=True)
    # Lane configuration (2L / 4L / 6L). Keep `lanes` for backward compatibility.
    lane_configuration = Column(String(10), nullable=True)
    # Flexible / Rigid (road mode). Concrete-specific inputs are stored separately.
    road_pavement_type = Column(String(20), nullable=True)
    # Plain / Rolling / Hilly
    terrain_type = Column(String(20), nullable=True)

    # Concrete-specific capture (reserved; do not affect flexible projects)
    concrete_pavement_type = Column(String(20), nullable=True)  # PQC/RCC
    slab_thickness_mm = Column(Integer, nullable=True)
    grade_of_concrete = Column(String(20), nullable=True)
    joint_spacing_m = Column(Float, nullable=True)
    dowel_diameter_mm = Column(Integer, nullable=True)
    tie_bar_diameter_mm = Column(Integer, nullable=True)

    # When project_type == 'Road', this optional field captures the
    # specific road construction type (Earthen, Gravel, Bituminous, ...)
    road_construction_type = Column(String(100), nullable=True)

    # ---------- ROAD CLASSIFICATION (Industry-correct; immutable after create) ----------
    # Road Category (functional class): NH/SH/MDR/Urban/etc.
    road_category = Column(String(100), nullable=True)
    # Road Engineering Type (preset driver): Flexible/Rigid/Urban variants
    road_engineering_type = Column(String(150), nullable=True)

    # Preset key used at project creation time (if any). Presets are not linked after creation,
    # but this supports admin safety checks (reset/delete constraints).
    road_preset_key = Column(String(200), nullable=True)

    # Saved selections/extras from Create Project (explicit storage requirement)
    road_extras_json = Column(Text, nullable=True)
    preset_activities_json = Column(Text, nullable=True)
    preset_materials_json = Column(Text, nullable=True)

    # ---------- LOCATION ----------
    country = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    city = Column(String(100), nullable=False)

    chainage_start = Column(String(50), nullable=True)
    chainage_end = Column(String(50), nullable=True)

    # ---------- PLANNED TIMELINE ----------
    planned_start_date = Column(Date, nullable=False)
    planned_end_date = Column(Date, nullable=False)

    # ---------- OWNERSHIP ----------
    created_by = Column(Integer, nullable=False)

    # ---------- META ----------
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    completed_at = Column(DateTime, nullable=True)

    # ================= RELATIONSHIPS =================

    # Project → Activities (definition)
    activities = relationship(
        "Activity",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    # 🔥 Project → ProjectActivity (planning + execution)
    project_activities = relationship(
        "ProjectActivity",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    planned_materials = relationship(
        "PlannedMaterial",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    material_usage_daily = relationship(
        "MaterialUsageDaily",
        back_populates="project",
        cascade="all, delete-orphan"
    )
