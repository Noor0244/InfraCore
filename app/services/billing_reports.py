"""
Billing Reports Service
Generate comprehensive billing reports
"""

from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Bill, Payment, MaterialRate
from typing import List, Dict
import io


class BillingReports:
    """Generate various billing reports"""

    @staticmethod
    def vendor_payment_report(db: Session, vendor_id: int = None, start_date: date = None, end_date: date = None) -> Dict:
        """Generate vendor payment summary report"""
        query = db.query(Bill)
        
        if vendor_id:
            query = query.filter(Bill.vendor_id == vendor_id)
        if start_date:
            query = query.filter(Bill.bill_date >= start_date)
        if end_date:
            query = query.filter(Bill.bill_date <= end_date)
        
        bills = query.all()
        
        summary = {
            "total_bills": len(bills),
            "total_amount": sum(b.total_amount for b in bills),
            "total_paid": sum(b.paid_amount for b in bills),
            "total_outstanding": sum(b.outstanding_amount for b in bills),
            "overdue_bills": len([b for b in bills if b.is_overdue]),
            "overdue_amount": sum(b.outstanding_amount for b in bills if b.is_overdue),
            "bills_by_status": {
                "PENDING": len([b for b in bills if b.payment_status == "PENDING"]),
                "PARTIAL": len([b for b in bills if b.payment_status == "PARTIAL"]),
                "PAID": len([b for b in bills if b.payment_status == "PAID"]),
                "OVERDUE": len([b for b in bills if b.is_overdue]),
            },
            "bills": [
                {
                    "bill_number": b.bill_number,
                    "bill_date": b.bill_date.isoformat(),
                    "due_date": b.due_date.isoformat(),
                    "total_amount": b.total_amount,
                    "paid_amount": b.paid_amount,
                    "outstanding": b.outstanding_amount,
                    "status": b.payment_status,
                }
                for b in bills
            ],
        }
        
        return summary

    @staticmethod
    def project_cost_report(db: Session, project_id: int) -> Dict:
        """Generate project cost analysis report"""
        bills = db.query(Bill).filter(Bill.project_id == project_id).all()
        
        # Break down by bill type
        by_type = {}
        for bill in bills:
            bill_type = bill.bill_type
            if bill_type not in by_type:
                by_type[bill_type] = {
                    "count": 0,
                    "amount": 0,
                    "paid": 0,
                    "outstanding": 0,
                }
            
            by_type[bill_type]["count"] += 1
            by_type[bill_type]["amount"] += bill.total_amount
            by_type[bill_type]["paid"] += bill.paid_amount
            by_type[bill_type]["outstanding"] += bill.outstanding_amount
        
        # Overall summary
        summary = {
            "project_id": project_id,
            "total_cost": sum(b.total_amount for b in bills),
            "total_paid": sum(b.paid_amount for b in bills),
            "total_outstanding": sum(b.outstanding_amount for b in bills),
            "average_bill_amount": sum(b.total_amount for b in bills) / len(bills) if bills else 0,
            "cost_by_type": by_type,
            "payment_status_distribution": {
                "PENDING": len([b for b in bills if b.payment_status == "PENDING"]),
                "PARTIAL": len([b for b in bills if b.payment_status == "PARTIAL"]),
                "PAID": len([b for b in bills if b.payment_status == "PAID"]),
            },
        }
        
        return summary

    @staticmethod
    def outstanding_bills_report(db: Session, project_id: int = None) -> Dict:
        """Generate outstanding bills report"""
        query = db.query(Bill).filter(Bill.payment_status != "PAID")
        
        if project_id:
            query = query.filter(Bill.project_id == project_id)
        
        bills = query.all()
        
        # Categorize by overdue status
        overdue_bills = [b for b in bills if b.is_overdue]
        upcoming_bills = [b for b in bills if not b.is_overdue]
        
        summary = {
            "total_outstanding_amount": sum(b.outstanding_amount for b in bills),
            "overdue": {
                "count": len(overdue_bills),
                "amount": sum(b.outstanding_amount for b in overdue_bills),
                "bills": [
                    {
                        "bill_number": b.bill_number,
                        "vendor_id": b.vendor_id,
                        "outstanding": b.outstanding_amount,
                        "due_date": b.due_date.isoformat(),
                        "days_overdue": (date.today() - b.due_date).days,
                    }
                    for b in sorted(overdue_bills, key=lambda x: x.due_date)
                ],
            },
            "upcoming": {
                "count": len(upcoming_bills),
                "amount": sum(b.outstanding_amount for b in upcoming_bills),
                "bills": [
                    {
                        "bill_number": b.bill_number,
                        "vendor_id": b.vendor_id,
                        "outstanding": b.outstanding_amount,
                        "due_date": b.due_date.isoformat(),
                        "days_until_due": (b.due_date - date.today()).days,
                    }
                    for b in sorted(upcoming_bills, key=lambda x: x.due_date)
                ],
            },
        }
        
        return summary

    @staticmethod
    def payment_analysis_report(db: Session, vendor_id: int = None, start_date: date = None, end_date: date = None) -> Dict:
        """Analyze payment patterns"""
        query = db.query(Payment)
        
        if vendor_id:
            query = query.filter(Payment.vendor_id == vendor_id)
        if start_date:
            query = query.filter(Payment.payment_date >= start_date)
        if end_date:
            query = query.filter(Payment.payment_date <= end_date)
        
        payments = query.all()
        
        # Payment method breakdown
        by_method = {}
        for payment in payments:
            method = payment.payment_method
            if method not in by_method:
                by_method[method] = {"count": 0, "amount": 0}
            
            by_method[method]["count"] += 1
            by_method[method]["amount"] += payment.amount_paid
        
        # Payment timeline
        summary = {
            "total_payments": len(payments),
            "total_amount_paid": sum(p.amount_paid for p in payments),
            "average_payment": sum(p.amount_paid for p in payments) / len(payments) if payments else 0,
            "payment_by_method": by_method,
            "reconciliation_status": {
                "reconciled": len([p for p in payments if p.is_reconciled]),
                "pending": len([p for p in payments if not p.is_reconciled]),
            },
        }
        
        return summary

    @staticmethod
    def generate_pdf_report(report_data: Dict, report_title: str) -> bytes:
        """Generate PDF report"""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
        except ImportError:
            raise ImportError("reportlab not installed. Install with: pip install reportlab")
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=30,
            alignment=1,  # Center
        )
        
        # Title
        elements.append(Paragraph(report_title, title_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Summary section
        if "total_bills" in report_data:
            summary_data = [
                ["Metric", "Value"],
                ["Total Bills", str(report_data.get("total_bills", 0))],
                ["Total Amount", f"₹{report_data.get('total_amount', 0):,.2f}"],
                ["Total Paid", f"₹{report_data.get('total_paid', 0):,.2f}"],
                ["Outstanding", f"₹{report_data.get('total_outstanding', 0):,.2f}"],
            ]
            
            table = Table(summary_data, colWidths=[3*inch, 3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
