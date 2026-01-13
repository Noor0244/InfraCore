from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.db.base import Base


class DailyWorkMachinery(Base):
    __tablename__ = "daily_work_machinery"

    id = Column(Integer, primary_key=True, index=True)

    report_id = Column(Integer, ForeignKey("daily_work_reports.id"), nullable=False)

    equipment_name = Column(String(150), nullable=False)
    equipment_type = Column(String(80), nullable=True)  # Hot Mix Plant / Paver / Roller / Excavator / Dumper
    hours_used = Column(Float, nullable=False, default=0.0)
    idle_hours = Column(Float, nullable=False, default=0.0)
    fuel_consumed = Column(Float, nullable=False, default=0.0)
    breakdown = Column(Boolean, nullable=False, default=False)
    breakdown_remarks = Column(String(2000), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    report = relationship("DailyWorkReport", back_populates="machinery_rows")
