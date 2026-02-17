"""
Bill (Invoice) Model
Represents bills/invoices issued to vendors
"""

from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Boolean, Date, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    
    # Bill Reference
    bill_number = Column(String(50), nullable=False, unique=True, index=True)  # e.g., BILL-2026-0001
    bill_date = Column(Date, nullable=False, index=True)
    
    # Relationships
    vendor_id = Column(Integer, ForeignKey("material_vendors.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # Bill Details
    due_date = Column(Date, nullable=False)
    payment_terms = Column(String(100), nullable=True)  # e.g., "Net 30", "COD"
    
    # Financial Summary
    subtotal = Column(Float, nullable=False, default=0.0)  # Before GST
    gst_amount = Column(Float, nullable=False, default=0.0)
    delivery_charges = Column(Float, nullable=False, default=0.0)
    other_charges = Column(Float, nullable=False, default=0.0)
    discount_amount = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False, default=0.0)  # After GST and charges
    
    # Payment Info
    paid_amount = Column(Float, nullable=False, default=0.0)
    payment_status = Column(String(50), nullable=False, default="PENDING")  # PENDING, PARTIAL, PAID, OVERDUE, CANCELLED
    currency = Column(String(10), nullable=False, default="INR")
    
    # Additional Info
    bill_type = Column(String(50), nullable=False, default="MATERIAL")  # MATERIAL, LABOUR, EQUIPMENT, OTHER
    notes = Column(Text, nullable=True)
    reference_number = Column(String(100), nullable=True)  # Vendor's reference
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    bill_items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="bill", cascade="all, delete-orphan")

    @property
    def outstanding_amount(self) -> float:
        """Calculate outstanding balance"""
        return self.total_amount - self.paid_amount

    @property
    def is_overdue(self) -> bool:
        """Check if bill is overdue"""
        if self.payment_status == "PAID":
            return False
        return date.today() > self.due_date

    def calculate_totals(self):
        """Recalculate bill totals from items"""
        if not self.bill_items:
            self.subtotal = 0.0
            self.gst_amount = 0.0
            self.total_amount = 0.0
            return

        self.subtotal = sum(item.line_total for item in self.bill_items)
        self.gst_amount = sum(item.gst_amount for item in self.bill_items)
        
        total = self.subtotal + self.gst_amount
        total += self.delivery_charges + self.other_charges
        total -= self.discount_amount
        
        self.total_amount = max(total, 0.0)

    def __repr__(self):
        return f"<Bill(bill_number={self.bill_number}, vendor_id={self.vendor_id}, total={self.total_amount})>"
