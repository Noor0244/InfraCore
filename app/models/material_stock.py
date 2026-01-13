from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Boolean, String, Integer as SAInteger
from datetime import datetime

from app.db.base import Base


class MaterialStock(Base):
    __tablename__ = "material_stocks"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)

    quantity_available = Column(Float, nullable=False, default=0)

    # Optional future use (multiple yards / godowns)
    location = Column(String(100), nullable=True)

    # Supplier / lead time / storage location (optional; enables road inventory prediction)
    supplier = Column(String(150), nullable=True)
    lead_time_days_override = Column(SAInteger, nullable=True)
    storage_location = Column(String(100), nullable=True)  # e.g. Bitumen Tank / Stack Yard / Crusher Yard

    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)

    is_active = Column(Boolean, default=True)
