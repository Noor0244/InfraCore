from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.base import Base


class StretchMaterial(Base):
    __tablename__ = "stretch_materials"

    id = Column(Integer, primary_key=True, index=True)

    stretch_activity_id = Column(Integer, ForeignKey("stretch_activities.id"), nullable=False, index=True)

    # Project-level material planning already exists via planned_materials.
    # Keep column name as project_material_id for domain consistency.
    project_material_id = Column(Integer, ForeignKey("planned_materials.id"), nullable=False, index=True)

    # Uses existing materials master table
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)

    required_quantity = Column(Float, nullable=False, default=0)
    consumed_quantity = Column(Float, nullable=False, default=0)
    balance_quantity = Column(Float, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    stretch_activity = relationship("StretchActivity", back_populates="stretch_materials")
    project_material = relationship("PlannedMaterial")
    material = relationship("Material")
