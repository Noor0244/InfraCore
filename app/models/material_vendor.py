from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class MaterialVendor(Base):
    __tablename__ = "material_vendors"

    id = Column(Integer, primary_key=True, index=True)

    material_id = Column(Integer, ForeignKey("materials.id"), nullable=True, index=True)

    # Basic Information
    vendor_name = Column(String(200), nullable=False)
    vendor_type = Column(String(100), nullable=True)  # Manufacturer, Distributor, Local Supplier, Transporter
    contact_person = Column(String(150), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    vendor_location = Column(String(200), nullable=True)
    service_area = Column(String(300), nullable=True)  # e.g., "50 km radius", "City-wide"
    vendor_priority = Column(String(50), nullable=True, default="Primary")  # Primary, Secondary, Backup
    reliability_rating = Column(String(50), nullable=True, default="Medium")  # High, Medium, Low

    # Commercial Details
    payment_terms = Column(String(100), nullable=True)  # Advance, COD, Credit
    credit_period = Column(Integer, nullable=True)  # Days allowed for payment
    gst_number = Column(String(50), nullable=True)
    gst_percentage = Column(Float, nullable=True, default=18.0)

    # Material Specific Details
    lead_time_days = Column(Integer, nullable=False, default=0)
    min_order_qty = Column(Float, nullable=True)
    unit_price = Column(Float, nullable=True)  # Per unit pricing for this vendor-material pair
    per_unit_quantity = Column(Float, nullable=True)  # e.g., 50 kg bag
    supply_capacity = Column(Float, nullable=True)  # e.g., 1000 bags/month

    # Contract Details
    contract_start_date = Column(DateTime, nullable=True)
    contract_end_date = Column(DateTime, nullable=True)

    # Document Paths (for file uploads)
    quotation_pdf = Column(String(500), nullable=True)
    agreement_pdf = Column(String(500), nullable=True)
    gst_certificate = Column(String(500), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    material = relationship("Material", back_populates="vendors")
