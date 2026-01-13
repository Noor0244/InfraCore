from sqlalchemy import Column, Integer, Float, ForeignKey, Date, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime, date

from app.db.base import Base


class MaterialUsageDaily(Base):
    __tablename__ = "material_usage_daily"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)

    usage_date = Column(Date, nullable=False, default=date.today)
    quantity_used = Column(Float, nullable=False)

    # Road mode (optional): chainage-based time-series features
    chainage_start = Column(String(50), nullable=True)
    chainage_end = Column(String(50), nullable=True)
    road_layer = Column(String(30), nullable=True)  # Subgrade / GSB / WMM / DBM / BC

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ---------- RELATIONSHIPS ----------
    project = relationship("Project", back_populates="material_usage_daily")
    material = relationship("Material")
