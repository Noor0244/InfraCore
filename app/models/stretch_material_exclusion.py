from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class StretchMaterialExclusion(Base):
    __tablename__ = "stretch_material_exclusions"

    __table_args__ = (
        UniqueConstraint("stretch_id", "material_id", name="uq_stretch_material_exclusions"),
    )

    id = Column(Integer, primary_key=True, index=True)

    stretch_id = Column(Integer, ForeignKey("road_stretches.id"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    stretch = relationship("RoadStretch")
    material = relationship("Material")
