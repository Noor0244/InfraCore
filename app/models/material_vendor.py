from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class MaterialVendor(Base):
    __tablename__ = "material_vendors"

    id = Column(Integer, primary_key=True, index=True)

    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)

    vendor_name = Column(String(200), nullable=False)
    contact_person = Column(String(150), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)

    lead_time_days = Column(Integer, nullable=False, default=0)
    min_order_qty = Column(Float, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    material = relationship("Material", back_populates="vendors")
