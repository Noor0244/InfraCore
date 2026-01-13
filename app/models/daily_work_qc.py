from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class DailyWorkQC(Base):
    __tablename__ = "daily_work_qc"

    id = Column(Integer, primary_key=True, index=True)

    report_id = Column(Integer, ForeignKey("daily_work_reports.id"), nullable=False)

    test_type = Column(String(150), nullable=False)
    location = Column(String(200), nullable=True)
    test_value = Column(String(100), nullable=True)
    result = Column(String(10), nullable=False, default="Pass")  # Pass/Fail
    engineer_name = Column(String(150), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    report = relationship("DailyWorkReport", back_populates="qc_rows")
