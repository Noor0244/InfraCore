"""
Payment Model
Records payments made towards bills
"""

from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Date, Text, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    # Payment Reference
    payment_number = Column(String(50), nullable=False, unique=True, index=True)  # e.g., PAY-2026-0001
    payment_date = Column(Date, nullable=False, index=True)

    # Foreign Keys
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("material_vendors.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    # Payment Details
    amount_paid = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    payment_method = Column(String(50), nullable=False)  # CHEQUE, NEFT, RTGS, CASH, UPI, BANK_TRANSFER
    
    # Bank Details (if applicable)
    cheque_number = Column(String(50), nullable=True)
    bank_name = Column(String(100), nullable=True)
    transaction_reference = Column(String(100), nullable=True)  # NEFT/RTGS ref
    
    # Additional Info
    notes = Column(Text, nullable=True)
    is_reconciled = Column(Boolean, nullable=False, default=False)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationship
    bill = relationship("Bill", back_populates="payments")

    def __repr__(self):
        return f"<Payment(payment_number={self.payment_number}, bill_id={self.bill_id}, amount={self.amount_paid})>"
