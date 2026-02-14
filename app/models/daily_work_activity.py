from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class DailyWorkActivity(Base):
    __tablename__ = "daily_work_activities"

    __table_args__ = (
        UniqueConstraint("report_id", "activity_id", name="uq_dwa_report_activity"),
    )

    id = Column(Integer, primary_key=True, index=True)

    report_id = Column(Integer, ForeignKey("daily_work_reports.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)

    # Snapshots (so DPR remains stable if plan changes later)
    planned_quantity = Column(Float, nullable=False, default=0)
    unit = Column(String(50), nullable=True)
    planned_start = Column(String(20), nullable=True)  # stored as ISO string for simplicity
    planned_end = Column(String(20), nullable=True)    # stored as ISO string for simplicity

    # Time snapshots (base unit = hours)
    planned_quantity_hours = Column(Float, nullable=False, default=0.0)
    display_unit = Column(String(10), nullable=False, default="hours")
    hours_per_day = Column(Float, nullable=False, default=8.0)

    executed_today = Column(Float, nullable=False, default=0)
    # Time execution (base unit = hours)
    executed_today_hours = Column(Float, nullable=False, default=0.0)
    remarks = Column(String(2000), nullable=True)

    approval_status = Column(String(20), nullable=True, default="Changed")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    report = relationship("DailyWorkReport", back_populates="activity_rows")
    project = relationship("Project")
    activity = relationship("Activity")
