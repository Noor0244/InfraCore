"""
Billing Repository
Handles all database operations for billing module
"""

from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.models import Bill, BillItem, Payment, MaterialRate
from typing import List, Optional


class BillingRepository:
    """Repository for billing operations"""

    @staticmethod
    def create_bill(
        db: Session,
        bill_number: str,
        vendor_id: int,
        project_id: int,
        bill_date: date,
        due_date: date,
        created_by_user_id: int,
        payment_terms: str = None,
        notes: str = None,
    ) -> Bill:
        """Create a new bill"""
        bill = Bill(
            bill_number=bill_number,
            bill_date=bill_date,
            due_date=due_date,
            vendor_id=vendor_id,
            project_id=project_id,
            payment_terms=payment_terms,
            notes=notes,
            created_by_user_id=created_by_user_id,
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)
        return bill

    @staticmethod
    def get_bill(db: Session, bill_id: int) -> Optional[Bill]:
        """Get bill by ID"""
        return db.query(Bill).filter(Bill.id == bill_id).first()

    @staticmethod
    def get_bill_by_number(db: Session, bill_number: str) -> Optional[Bill]:
        """Get bill by bill number"""
        return db.query(Bill).filter(Bill.bill_number == bill_number).first()

    @staticmethod
    def get_all_bills(db: Session, project_id: int = None, vendor_id: int = None) -> List[Bill]:
        """Get all bills with optional filters"""
        query = db.query(Bill)
        
        if project_id:
            query = query.filter(Bill.project_id == project_id)
        if vendor_id:
            query = query.filter(Bill.vendor_id == vendor_id)
        
        return query.order_by(desc(Bill.bill_date)).all()

    @staticmethod
    def update_bill(db: Session, bill: Bill) -> Bill:
        """Update bill"""
        db.merge(bill)
        db.commit()
        db.refresh(bill)
        return bill

    @staticmethod
    def delete_bill(db: Session, bill_id: int) -> bool:
        """Delete a bill"""
        bill = db.query(Bill).filter(Bill.id == bill_id).first()
        if not bill:
            return False
        db.delete(bill)
        db.commit()
        return True

    @staticmethod
    def add_bill_item(
        db: Session,
        bill_id: int,
        material_id: int,
        quantity: float,
        unit: str,
        unit_price: float,
        gst_percentage: float = 18.0,
        description: str = None,
        procurement_log_id: int = None,
    ) -> BillItem:
        """Add item to bill"""
        bill_item = BillItem(
            bill_id=bill_id,
            material_id=material_id,
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
            gst_percentage=gst_percentage,
            description=description,
            procurement_log_id=procurement_log_id,
        )
        bill_item.calculate_totals()
        db.add(bill_item)
        db.commit()
        db.refresh(bill_item)
        return bill_item

    @staticmethod
    def get_bill_items(db: Session, bill_id: int) -> List[BillItem]:
        """Get all items in a bill"""
        return db.query(BillItem).filter(BillItem.bill_id == bill_id).all()

    @staticmethod
    def delete_bill_item(db: Session, item_id: int) -> bool:
        """Delete bill item"""
        item = db.query(BillItem).filter(BillItem.id == item_id).first()
        if not item:
            return False
        db.delete(item)
        db.commit()
        return True

    @staticmethod
    def record_payment(
        db: Session,
        payment_number: str,
        bill_id: int,
        vendor_id: int,
        project_id: int,
        amount_paid: float,
        payment_date: date,
        payment_method: str,
        created_by_user_id: int,
        cheque_number: str = None,
        bank_name: str = None,
        transaction_reference: str = None,
        notes: str = None,
    ) -> Payment:
        """Record a payment"""
        payment = Payment(
            payment_number=payment_number,
            bill_id=bill_id,
            vendor_id=vendor_id,
            project_id=project_id,
            amount_paid=amount_paid,
            payment_date=payment_date,
            payment_method=payment_method,
            cheque_number=cheque_number,
            bank_name=bank_name,
            transaction_reference=transaction_reference,
            notes=notes,
            created_by_user_id=created_by_user_id,
        )
        db.add(payment)
        
        # Update bill's paid amount
        bill = db.query(Bill).filter(Bill.id == bill_id).first()
        if bill:
            bill.paid_amount += amount_paid
            if bill.paid_amount >= bill.total_amount:
                bill.payment_status = "PAID"
            elif bill.paid_amount > 0:
                bill.payment_status = "PARTIAL"
            db.merge(bill)
        
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def get_payments(db: Session, bill_id: int = None, vendor_id: int = None) -> List[Payment]:
        """Get payments with optional filters"""
        query = db.query(Payment)
        
        if bill_id:
            query = query.filter(Payment.bill_id == bill_id)
        if vendor_id:
            query = query.filter(Payment.vendor_id == vendor_id)
        
        return query.order_by(desc(Payment.payment_date)).all()

    @staticmethod
    def get_material_rate(
        db: Session,
        material_id: int,
        vendor_id: int,
        project_id: int = None,
        reference_date: date = None,
    ) -> Optional[MaterialRate]:
        """Get applicable material rate"""
        if reference_date is None:
            reference_date = date.today()
        
        query = db.query(MaterialRate).filter(
            and_(
                MaterialRate.material_id == material_id,
                MaterialRate.vendor_id == vendor_id,
                MaterialRate.effective_from <= reference_date,
                MaterialRate.is_active == True,
            )
        )
        
        # Optional: filter by project
        if project_id:
            query = query.filter(
                (MaterialRate.project_id == project_id) | (MaterialRate.project_id == None)
            )
        
        # Get most recent rate
        return query.order_by(desc(MaterialRate.effective_from)).first()

    @staticmethod
    def create_material_rate(
        db: Session,
        material_id: int,
        vendor_id: int,
        unit_price: float,
        effective_from: date,
        gst_percentage: float = 18.0,
        created_by_user_id: int = None,
        project_id: int = None,
        effective_to: date = None,
        delivery_charges: float = 0.0,
        handling_charges: float = 0.0,
        notes: str = None,
    ) -> MaterialRate:
        """Create a new material rate"""
        rate = MaterialRate(
            material_id=material_id,
            vendor_id=vendor_id,
            unit_price=unit_price,
            effective_from=effective_from,
            effective_to=effective_to,
            gst_percentage=gst_percentage,
            delivery_charges=delivery_charges,
            handling_charges=handling_charges,
            notes=notes,
            created_by_user_id=created_by_user_id,
            project_id=project_id,
        )
        db.add(rate)
        db.commit()
        db.refresh(rate)
        return rate

    @staticmethod
    def generate_bill_number(db: Session) -> str:
        """Generate next bill number"""
        last_bill = db.query(Bill).order_by(desc(Bill.id)).first()
        if last_bill:
            # Extract number from bill_number (e.g., "BILL-2026-0001" -> 1)
            last_num = int(last_bill.bill_number.split('-')[-1])
            next_num = last_num + 1
        else:
            next_num = 1
        
        from datetime import datetime
        year = datetime.now().year
        return f"BILL-{year}-{next_num:04d}"

    @staticmethod
    def generate_payment_number(db: Session) -> str:
        """Generate next payment number"""
        last_payment = db.query(Payment).order_by(desc(Payment.id)).first()
        if last_payment:
            last_num = int(last_payment.payment_number.split('-')[-1])
            next_num = last_num + 1
        else:
            next_num = 1
        
        from datetime import datetime
        year = datetime.now().year
        return f"PAY-{year}-{next_num:04d}"
