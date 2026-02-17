"""
Material Rate Model
Stores vendor-specific pricing for materials
"""

from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Boolean, Date
from sqlalchemy.orm import relationship
from app.db.base import Base


class MaterialRate(Base):
    __tablename__ = "material_rates"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("material_vendors.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    # Pricing Details
    unit_price = Column(Float, nullable=False)  # Price per unit
    currency = Column(String(10), nullable=False, default="INR")
    gst_percentage = Column(Float, nullable=False, default=18.0)
    
    # Applicable Period
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)  # NULL = ongoing
    
    # Additional Charges
    delivery_charges = Column(Float, nullable=True, default=0.0)
    handling_charges = Column(Float, nullable=True, default=0.0)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    notes = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    def calculate_gst(self) -> float:
        """Calculate GST amount"""
        return self.unit_price * (self.gst_percentage / 100)

    def calculate_total_per_unit(self) -> float:
        """Calculate total price per unit including GST"""
        gst = self.calculate_gst()
        return self.unit_price + gst

    def __repr__(self):
        return f"<MaterialRate(material_id={self.material_id}, vendor_id={self.vendor_id}, unit_price={self.unit_price})>"
