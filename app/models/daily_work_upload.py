from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class DailyWorkUpload(Base):
    __tablename__ = "daily_work_uploads"

    id = Column(Integer, primary_key=True, index=True)

    report_id = Column(Integer, ForeignKey("daily_work_reports.id"), nullable=False)

    category = Column(String(50), nullable=False)  # Before/During/After/Issue/QC/Safety/Docs
    file_path = Column(String(500), nullable=False)
    original_name = Column(String(255), nullable=True)

    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    report = relationship("DailyWorkReport", back_populates="uploads")
