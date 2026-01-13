from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Boolean, String
from datetime import datetime

from app.db.base import Base


class MaterialUsage(Base):
    __tablename__ = "material_usages"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)

    # Backward-compatible: older code used quantity_used as the planned quantity.
    quantity_used = Column(Float, nullable=False)

    # Newer inventory logic expects these fields.
    # Keep them optional to avoid breaking existing rows.
    quantity = Column(Float, nullable=True)
    is_planned = Column(Boolean, nullable=True, default=False)
    unit = Column(String(50), nullable=True)

    usage_date = Column(DateTime, default=datetime.utcnow, nullable=False)
