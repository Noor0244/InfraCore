from sqlalchemy import Column, Integer, Float, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class MaterialStock(Base):
    __tablename__ = "material_stocks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False)
    quantity_available = Column(Float, nullable=False)
    location = Column(String(100), nullable=True)
    supplier = Column(String(150), nullable=True)
    lead_time_days_override = Column(Integer, nullable=True)
    storage_location = Column(String(100), nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Integer, default=1, nullable=False)

    material = relationship("Material", backref="stocks")
