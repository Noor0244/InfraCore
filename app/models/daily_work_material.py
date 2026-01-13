from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class DailyWorkMaterial(Base):
    __tablename__ = "daily_work_materials"

    id = Column(Integer, primary_key=True, index=True)

    report_id = Column(Integer, ForeignKey("daily_work_reports.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)

    unit = Column(String(50), nullable=True)

    planned_today = Column(Float, nullable=True)
    issued_today = Column(Float, nullable=True)
    consumed_today = Column(Float, nullable=True)

    source = Column(String(50), nullable=True)  # Store/Plant/Supplier

    # Road mode (optional): per-material chainage span + layer
    chainage_start = Column(String(50), nullable=True)
    chainage_end = Column(String(50), nullable=True)
    road_layer = Column(String(30), nullable=True)  # Subgrade / GSB / WMM / DBM / BC

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    report = relationship("DailyWorkReport", back_populates="material_rows")
    material = relationship("Material")
    project = relationship("Project")
