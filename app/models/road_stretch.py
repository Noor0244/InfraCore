from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class RoadStretch(Base):
    __tablename__ = "road_stretches"

    __table_args__ = (
        UniqueConstraint("project_id", "stretch_code", name="uq_road_stretches_project_code"),
        UniqueConstraint("project_id", "sequence_no", name="uq_road_stretches_project_sequence"),
    )

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    # Stretch-specific classification (can vary per stretch)
    road_category = Column(String(100), nullable=True)
    engineering_type = Column(String(50), nullable=True)

    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True, index=True)

    stretch_code = Column(String(20), nullable=False, index=True)
    stretch_name = Column(String(255), nullable=False)

    start_chainage = Column(String(20), nullable=False)
    end_chainage = Column(String(20), nullable=False)

    length_m = Column(Integer, nullable=False)
    sequence_no = Column(Integer, nullable=False, index=True)

    # Planned schedule (stretch-scoped)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = relationship("Project")
    location = relationship("Location")

    geometry = relationship(
        "RoadGeometry",
        back_populates="stretch",
        cascade="all, delete-orphan",
        uselist=False,
    )

    pavement_design = relationship(
        "PavementDesign",
        back_populates="stretch",
        cascade="all, delete-orphan",
        uselist=False,
    )

    stretch_activities = relationship(
        "StretchActivity",
        back_populates="stretch",
        cascade="all, delete-orphan",
    )

    # Many-to-many: RoadStretch <-> Material
    materials_link = relationship(
        "MaterialStretch",
        back_populates="stretch",
        cascade="all, delete-orphan",
    )
