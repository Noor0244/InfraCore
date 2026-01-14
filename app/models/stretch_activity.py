from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class StretchActivity(Base):
    __tablename__ = "stretch_activities"

    id = Column(Integer, primary_key=True, index=True)

    stretch_id = Column(Integer, ForeignKey("road_stretches.id"), nullable=False, index=True)

    # Links to the existing ProjectActivity row (project_activities.id)
    project_activity_id = Column(Integer, ForeignKey("project_activities.id"), nullable=False, index=True)

    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)

    # Optional time-of-day planning (HH:MM)
    planned_start_time = Column(String(10), nullable=True)
    planned_end_time = Column(String(10), nullable=True)

    # Hours-based duration planning (primary time unit)
    planned_duration_hours = Column(Float, nullable=True)

    planned_quantity = Column(Float, nullable=True)

    actual_quantity = Column(Float, nullable=True)
    progress_percent = Column(Float, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    stretch = relationship("RoadStretch", back_populates="stretch_activities")
    project_activity = relationship("ProjectActivity")

    stretch_materials = relationship(
        "StretchMaterial",
        back_populates="stretch_activity",
        cascade="all, delete-orphan",
    )
