"""
Bill Item Model
Individual line items in a bill
"""

from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class BillItem(Base):
    __tablename__ = "bill_items"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    procurement_log_id = Column(Integer, ForeignKey("procurement_logs.id"), nullable=True, index=True)

    # Item Details
    description = Column(String(300), nullable=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    unit_price = Column(Float, nullable=False)
    
    # Financial
    line_total = Column(Float, nullable=False)  # quantity * unit_price (before GST)
    gst_percentage = Column(Float, nullable=False, default=18.0)
    gst_amount = Column(Float, nullable=False, default=0.0)
    line_total_with_gst = Column(Float, nullable=False)  # line_total + gst_amount
    
    # Additional Info
    notes = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    bill = relationship("Bill", back_populates="bill_items")

    def calculate_totals(self):
        """Calculate line item totals"""
        self.line_total = self.quantity * self.unit_price
        self.gst_amount = self.line_total * (self.gst_percentage / 100)
        self.line_total_with_gst = self.line_total + self.gst_amount

    def __repr__(self):
        return f"<BillItem(bill_id={self.bill_id}, material_id={self.material_id}, quantity={self.quantity})>"
