from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db.base import Base


class RoadPreset(Base):
    __tablename__ = "road_presets"

    id = Column(Integer, primary_key=True, index=True)

    # Stable identifier used for upsert from seed files
    preset_key = Column(String(200), unique=True, nullable=False, index=True)

    # Mandatory metadata (normalized)
    road_category = Column(String(100), nullable=False)
    engineering_type = Column(String(50), nullable=True)
    construction_type = Column(String(80), nullable=True)
    region = Column(String(50), nullable=False, server_default="India")
    standards = Column(Text, nullable=True)

    # Safety flags
    user_modified = Column(Boolean, default=False, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    # Soft delete (never hard delete presets)
    is_deleted = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ------------------------------------------------------------------
    # Legacy / compatibility fields (kept to avoid breaking existing code)
    # ------------------------------------------------------------------
    # The runtime preset engine currently matches on this display string.
    road_engineering_type = Column(String(150), nullable=True)

    # Optional metadata (future-proofing)
    title = Column(String(255), nullable=True)
    detail_level = Column(String(80), nullable=True)
    material_depth = Column(String(80), nullable=True)

    # Snapshot JSON used by the existing preset engine loader.
    preset_json = Column(Text, nullable=False, server_default="{}")


class PresetActivity(Base):
    __tablename__ = "preset_activities"

    id = Column(Integer, primary_key=True, index=True)
    preset_id = Column(Integer, ForeignKey("road_presets.id", ondelete="CASCADE"), nullable=False, index=True)

    activity_code = Column(String(50), nullable=False)
    activity_name = Column(String(255), nullable=False)
    category = Column(String(80), nullable=True)
    sequence_no = Column(Integer, nullable=False)

    is_optional = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    user_modified = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("preset_id", "activity_code", name="uq_preset_activity_code"),
    )


class PresetMaterial(Base):
    __tablename__ = "preset_materials"

    id = Column(Integer, primary_key=True, index=True)
    preset_id = Column(Integer, ForeignKey("road_presets.id", ondelete="CASCADE"), nullable=False, index=True)

    material_code = Column(String(50), nullable=False)
    material_name = Column(String(255), nullable=False)
    unit = Column(String(30), nullable=True)
    default_spec = Column(String(80), nullable=True)
    is_expandable = Column(Boolean, default=False, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    user_modified = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("preset_id", "material_code", name="uq_preset_material_code"),
    )


class PresetActivityMaterialMap(Base):
    __tablename__ = "preset_activity_material_map"

    id = Column(Integer, primary_key=True, index=True)

    preset_activity_id = Column(
        Integer,
        ForeignKey("preset_activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preset_material_id = Column(
        Integer,
        ForeignKey("preset_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "preset_activity_id",
            "preset_material_id",
            name="uq_preset_activity_material_pair",
        ),
    )
