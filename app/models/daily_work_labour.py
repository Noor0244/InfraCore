from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class DailyWorkLabour(Base):
    __tablename__ = "daily_work_labour"

    id = Column(Integer, primary_key=True, index=True)

    report_id = Column(Integer, ForeignKey("daily_work_reports.id"), nullable=False)

    category = Column(String(50), nullable=False)  # Skilled/Unskilled/Operator/Supervisor
    workers = Column(Integer, nullable=False, default=0)
    hours = Column(Float, nullable=False, default=0.0)
    overtime_hours = Column(Float, nullable=False, default=0.0)
    agency = Column(String(150), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    report = relationship("DailyWorkReport", back_populates="labour_rows")
