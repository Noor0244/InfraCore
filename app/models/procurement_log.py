from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text

from app.db.base import Base


class ProcurementLog(Base):
    __tablename__ = "procurement_logs"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("material_vendors.id"), nullable=True, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True, index=True)

    order_date = Column(Date, nullable=False)
    promised_delivery_date = Column(Date, nullable=True)
    delivered_date = Column(Date, nullable=True)

    promised_lead_time_days = Column(Integer, nullable=True)
    actual_lead_time_days = Column(Integer, nullable=True)

    quantity = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)

    notes = Column(Text, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @staticmethod
    def compute_lead_time_days(order_date: date | None, other_date: date | None) -> int | None:
        if not order_date or not other_date:
            return None
        try:
            return int((other_date - order_date).days)
        except Exception:
            return None
