from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class RoadGeometry(Base):
    __tablename__ = "road_geometries"

    __table_args__ = (
        UniqueConstraint("stretch_id", name="uq_road_geometries_stretch_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    stretch_id = Column(Integer, ForeignKey("road_stretches.id"), nullable=False, index=True)

    lanes = Column(Integer, nullable=True)
    carriageway_width_m = Column(Float, nullable=True)

    shoulder_type = Column(String(50), nullable=True)
    shoulder_width_m = Column(Float, nullable=True)

    median_type = Column(String(50), nullable=True)
    median_width_m = Column(Float, nullable=True)

    formation_width_m = Column(Float, nullable=True)
    terrain_type = Column(String(50), nullable=True)
    urban_or_rural_flag = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    stretch = relationship("RoadStretch", back_populates="geometry")
