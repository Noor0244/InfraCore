from sqlalchemy import Column, Integer, Float, ForeignKey, Date, DateTime, Boolean
from datetime import datetime

from app.db.base import Base


class ActivityMaterial(Base):
    __tablename__ = "activity_materials"

    id = Column(Integer, primary_key=True, index=True)

    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)

    # Consumption of material per 1 unit of activity
    # Example: 1.25 ton of aggregate per 1 km of GSB
    consumption_rate = Column(Float, nullable=False)

    # ---------------- Lead time & vendor planning (optional) ----------------
    vendor_id = Column(Integer, ForeignKey("material_vendors.id"), nullable=True)

    # Planning-only order context (NO auto-orders)
    order_date = Column(Date, nullable=True)

    # If set, overrides vendor/material default lead time
    lead_time_days_override = Column(Integer, nullable=True)

    # Snapshot of lead time used for calculations at save time
    lead_time_days = Column(Integer, nullable=True)

    # Snapshot of expected delivery date at save time
    expected_delivery_date = Column(Date, nullable=True)

    # Material risk flag (computed during planning)
    is_material_risk = Column(Boolean, nullable=False, default=False)

    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
