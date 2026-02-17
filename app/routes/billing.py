"""
Billing Routes
API endpoints for billing system operations
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import date
from app.db.session import get_db
from app.repositories.billing_repository import BillingRepository
from app.models import User
import json

router = APIRouter(prefix="/billing", tags=["billing"])


# ==================== MATERIAL RATES ====================

@router.post("/rates/create")
async def create_material_rate(request: Request, db: Session = Depends(get_db)):
    """Create a new material rate"""
    try:
        user = request.session.get("user")
        if not user or user["role"] not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        data = await request.json()
        
        rate = BillingRepository.create_material_rate(
            db=db,
            material_id=data["material_id"],
            vendor_id=data["vendor_id"],
            unit_price=float(data["unit_price"]),
            effective_from=date.fromisoformat(data["effective_from"]),
            gst_percentage=float(data.get("gst_percentage", 18.0)),
            created_by_user_id=user["id"],
            project_id=data.get("project_id"),
            effective_to=date.fromisoformat(data["effective_to"]) if data.get("effective_to") else None,
            delivery_charges=float(data.get("delivery_charges", 0.0)),
            handling_charges=float(data.get("handling_charges", 0.0)),
            notes=data.get("notes"),
        )
        
        return {
            "success": True,
            "message": "Material rate created successfully",
            "rate_id": rate.id,
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rates/{material_id}/{vendor_id}")
async def get_material_rate(material_id: int, vendor_id: int, db: Session = Depends(get_db)):
    """Get current material rate"""
    rate = BillingRepository.get_material_rate(
        db=db,
        material_id=material_id,
        vendor_id=vendor_id,
    )
    
    if not rate:
        raise HTTPException(status_code=404, detail="Material rate not found")
    
    return {
        "id": rate.id,
        "unit_price": rate.unit_price,
        "gst_percentage": rate.gst_percentage,
        "delivery_charges": rate.delivery_charges,
        "handling_charges": rate.handling_charges,
        "effective_from": rate.effective_from.isoformat(),
        "total_per_unit": rate.calculate_total_per_unit(),
    }


# ==================== BILLS ====================

@router.post("/bills/create")
async def create_bill(request: Request, db: Session = Depends(get_db)):
    """Create a new bill"""
    try:
        user = request.session.get("user")
        if not user or user["role"] not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        data = await request.json()
        
        bill_number = BillingRepository.generate_bill_number(db)
        
        bill = BillingRepository.create_bill(
            db=db,
            bill_number=bill_number,
            vendor_id=data["vendor_id"],
            project_id=data["project_id"],
            bill_date=date.fromisoformat(data["bill_date"]),
            due_date=date.fromisoformat(data["due_date"]),
            created_by_user_id=user["id"],
            payment_terms=data.get("payment_terms"),
            notes=data.get("notes"),
        )
        
        return {
            "success": True,
            "message": "Bill created successfully",
            "bill_id": bill.id,
            "bill_number": bill.bill_number,
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/bills/{bill_id}")
async def get_bill(bill_id: int, db: Session = Depends(get_db)):
    """Get bill details"""
    bill = BillingRepository.get_bill(db, bill_id)
    
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    return {
        "id": bill.id,
        "bill_number": bill.bill_number,
        "bill_date": bill.bill_date.isoformat(),
        "due_date": bill.due_date.isoformat(),
        "vendor_id": bill.vendor_id,
        "project_id": bill.project_id,
        "subtotal": bill.subtotal,
        "gst_amount": bill.gst_amount,
        "delivery_charges": bill.delivery_charges,
        "total_amount": bill.total_amount,
        "paid_amount": bill.paid_amount,
        "outstanding_amount": bill.outstanding_amount,
        "payment_status": bill.payment_status,
        "items_count": len(bill.bill_items),
    }


@router.get("/bills/project/{project_id}")
async def get_project_bills(project_id: int, db: Session = Depends(get_db)):
    """Get all bills for a project"""
    bills = BillingRepository.get_all_bills(db, project_id=project_id)
    
    return {
        "success": True,
        "bills": [
            {
                "id": bill.id,
                "bill_number": bill.bill_number,
                "bill_date": bill.bill_date.isoformat(),
                "vendor_id": bill.vendor_id,
                "total_amount": bill.total_amount,
                "paid_amount": bill.paid_amount,
                "outstanding_amount": bill.outstanding_amount,
                "payment_status": bill.payment_status,
            }
            for bill in bills
        ],
    }


@router.post("/bills/{bill_id}/add-item")
async def add_bill_item(bill_id: int, request: Request, db: Session = Depends(get_db)):
    """Add item to bill"""
    try:
        user = request.session.get("user")
        if not user or user["role"] not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        data = await request.json()
        
        bill_item = BillingRepository.add_bill_item(
            db=db,
            bill_id=bill_id,
            material_id=data["material_id"],
            quantity=float(data["quantity"]),
            unit=data["unit"],
            unit_price=float(data["unit_price"]),
            gst_percentage=float(data.get("gst_percentage", 18.0)),
            description=data.get("description"),
            procurement_log_id=data.get("procurement_log_id"),
        )
        
        # Recalculate bill totals
        bill = BillingRepository.get_bill(db, bill_id)
        bill.calculate_totals()
        BillingRepository.update_bill(db, bill)
        
        return {
            "success": True,
            "message": "Bill item added successfully",
            "item_id": bill_item.id,
            "line_total": bill_item.line_total_with_gst,
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== PAYMENTS ====================

@router.post("/payments/record")
async def record_payment(request: Request, db: Session = Depends(get_db)):
    """Record a payment"""
    try:
        user = request.session.get("user")
        if not user or user["role"] not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        data = await request.json()
        
        payment_number = BillingRepository.generate_payment_number(db)
        
        payment = BillingRepository.record_payment(
            db=db,
            payment_number=payment_number,
            bill_id=data["bill_id"],
            vendor_id=data["vendor_id"],
            project_id=data["project_id"],
            amount_paid=float(data["amount_paid"]),
            payment_date=date.fromisoformat(data["payment_date"]),
            payment_method=data["payment_method"],
            created_by_user_id=user["id"],
            cheque_number=data.get("cheque_number"),
            bank_name=data.get("bank_name"),
            transaction_reference=data.get("transaction_reference"),
            notes=data.get("notes"),
        )
        
        return {
            "success": True,
            "message": "Payment recorded successfully",
            "payment_id": payment.id,
            "payment_number": payment.payment_number,
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payments/{bill_id}")
async def get_bill_payments(bill_id: int, db: Session = Depends(get_db)):
    """Get all payments for a bill"""
    payments = BillingRepository.get_payments(db, bill_id=bill_id)
    
    return {
        "success": True,
        "payments": [
            {
                "id": p.id,
                "payment_number": p.payment_number,
                "payment_date": p.payment_date.isoformat(),
                "amount_paid": p.amount_paid,
                "payment_method": p.payment_method,
                "is_reconciled": p.is_reconciled,
                "cheque_number": p.cheque_number,
                "bank_name": p.bank_name,
            }
            for p in payments
        ],
    }


# ==================== BILL ITEMS ====================

@router.get("/bills/{bill_id}/items")
async def get_bill_items(bill_id: int, db: Session = Depends(get_db)):
    """Get all items for a bill"""
    items = BillingRepository.get_bill_items(db, bill_id)
    
    if not items:
        return {
            "success": True,
            "items": [],
        }
    
    return {
        "success": True,
        "items": [
            {
                "id": item.id,
                "material_id": item.material_id,
                "material_name": item.material.name if item.material else "N/A",
                "quantity": item.quantity,
                "unit": item.unit,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
                "gst_percentage": item.gst_percentage,
                "gst_amount": item.gst_amount,
                "line_total_with_gst": item.line_total_with_gst,
                "description": item.description,
            }
            for item in items
        ],
    }


@router.delete("/bills/{bill_id}/items/{item_id}")
async def delete_bill_item(bill_id: int, item_id: int, request: Request, db: Session = Depends(get_db)):
    """Remove item from bill"""
    try:
        user = request.session.get("user")
        if not user or user["role"] not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        BillingRepository.delete_bill_item(db, item_id)
        
        # Recalculate bill totals
        bill = BillingRepository.get_bill(db, bill_id)
        bill.calculate_totals()
        db.commit()
        
        return {
            "success": True,
            "message": "Bill item deleted successfully",
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== BILL MANAGEMENT ====================

@router.get("/bills")
async def get_all_bills(
    project_id: int = None,
    vendor_id: int = None,
    status: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all bills with filters and pagination"""
    bills = BillingRepository.get_all_bills(
        db=db,
        project_id=project_id,
        vendor_id=vendor_id,
        status=status,
    )
    
    # Pagination
    total = len(bills)
    bills = bills[skip:skip+limit]
    
    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "bills": [
            {
                "id": bill.id,
                "bill_number": bill.bill_number,
                "bill_date": bill.bill_date.isoformat(),
                "due_date": bill.due_date.isoformat(),
                "vendor_id": bill.vendor_id,
                "project_id": bill.project_id,
                "total_amount": bill.total_amount,
                "paid_amount": bill.paid_amount,
                "outstanding_amount": bill.outstanding_amount,
                "payment_status": bill.payment_status,
                "is_overdue": bill.is_overdue,
            }
            for bill in bills
        ],
    }


@router.put("/bills/{bill_id}")
async def update_bill(bill_id: int, request: Request, db: Session = Depends(get_db)):
    """Update bill details"""
    try:
        user = request.session.get("user")
        if not user or user["role"] not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        data = await request.json()
        bill = BillingRepository.get_bill(db, bill_id)
        
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        
        # Update fields
        if "due_date" in data:
            bill.due_date = date.fromisoformat(data["due_date"])
        if "payment_terms" in data:
            bill.payment_terms = data["payment_terms"]
        if "notes" in data:
            bill.notes = data["notes"]
        
        db.commit()
        
        return {
            "success": True,
            "message": "Bill updated successfully",
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/bills/{bill_id}")
async def delete_bill(bill_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a bill"""
    try:
        user = request.session.get("user")
        if not user or user["role"] not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        BillingRepository.delete_bill(db, bill_id)
        
        return {
            "success": True,
            "message": "Bill deleted successfully",
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== REPORTS ====================

@router.get("/reports/vendor-payment")
async def vendor_payment_report(
    vendor_id: int = None,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db)
):
    """Generate vendor payment report"""
    try:
        from app.services.billing_reports import BillingReports
        
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
        
        report = BillingReports.vendor_payment_report(
            db=db,
            vendor_id=vendor_id,
            start_date=start,
            end_date=end,
        )
        
        return {
            "success": True,
            "report": report,
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports/project-cost")
async def project_cost_report(project_id: int, db: Session = Depends(get_db)):
    """Generate project cost analysis report"""
    try:
        from app.services.billing_reports import BillingReports
        
        report = BillingReports.project_cost_report(db=db, project_id=project_id)
        
        return {
            "success": True,
            "report": report,
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports/outstanding")
async def outstanding_bills_report(project_id: int = None, db: Session = Depends(get_db)):
    """Generate outstanding bills report"""
    try:
        from app.services.billing_reports import BillingReports
        
        report = BillingReports.outstanding_bills_report(
            db=db,
            project_id=project_id,
        )
        
        return {
            "success": True,
            "report": report,
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports/payment-analysis")
async def payment_analysis_report(
    vendor_id: int = None,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db)
):
    """Generate payment analysis report"""
    try:
        from app.services.billing_reports import BillingReports
        
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
        
        report = BillingReports.payment_analysis_report(
            db=db,
            vendor_id=vendor_id,
            start_date=start,
            end_date=end,
        )
        
        return {
            "success": True,
            "report": report,
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
