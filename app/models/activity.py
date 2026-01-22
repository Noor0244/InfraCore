from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)

    # Human-friendly ID (separate from numeric PK)
    # Example: ACT-000001
    code = Column(String(30), nullable=True, index=True)

    name = Column(String(150), nullable=False)

    # Optional default time-of-day for this activity (captured during project creation).
    # Stored as 'HH:MM' strings for SQLite compatibility.
    default_start_time = Column(String(10), nullable=True)
    default_end_time = Column(String(10), nullable=True)

    # True = standard (Earthwork, WMM, DBM)
    # False = user-created
    is_standard = Column(Boolean, default=False, nullable=False)

    # Soft-delete flag (archive) to avoid FK constraint issues
    is_active = Column(Boolean, default=True, nullable=False)

    # 🔴 PROJECT SCOPE
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ================= TIME TRACKING (BASE UNIT = HOURS) =================
    # Backward-compatible additive columns.
    #
    # Rules:
    # - Persist ONLY hours
    # - UI can display hours or days (per-activity)
    # - 1 day = hours_per_day (default 8; project-level config is future-ready)
    planned_quantity_hours = Column(Float, nullable=False, default=0.0)
    executed_quantity_hours = Column(Float, nullable=False, default=0.0)
    # Stored as string for SQLite compatibility. Allowed: 'hours' | 'days'
    display_unit = Column(String(10), nullable=False, default="hours")
    hours_per_day = Column(Float, nullable=False, default=8.0)

    # ================= RELATIONSHIPS =================

    # Project → Activities
    project = relationship(
        "Project",
        back_populates="activities"
    )

    # Activity → ProjectActivity (🔥 CRITICAL)
    project_activities = relationship(
        "ProjectActivity",
        back_populates="activity",
        cascade="all, delete-orphan"
    )

    # Many-to-many: Activity <-> Material
    materials_link = relationship(
        "MaterialActivity",
        back_populates="activity",
        cascade="all, delete-orphan"
    )
