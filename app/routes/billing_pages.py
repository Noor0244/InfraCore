"""
Billing Page Routes
HTML page endpoints for billing system UI
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from app.db.session import get_db
from starlette.templating import Jinja2Templates
import os

router = APIRouter(prefix="/app/billing", tags=["billing-pages"])

# Setup templates
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def billing_dashboard(request: Request, db: Session = Depends(get_db)):
    """Billing dashboard page"""
    user = request.session.get("user")
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/login", status_code=302)
    
    return templates.TemplateResponse("billing/bills_management.html", {
        "request": request,
        "user": user,
        "title": "Billing Management",
    })


@router.get("/bill", response_class=HTMLResponse)
async def bill_detail(request: Request, id: int, db: Session = Depends(get_db)):
    """Bill detail page"""
    user = request.session.get("user")
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/login", status_code=302)
    
    return templates.TemplateResponse("billing/bill_detail.html", {
        "request": request,
        "user": user,
        "bill_id": id,
        "title": "Bill Details",
    })


@router.get("/payment-record", response_class=HTMLResponse)
async def payment_record_page(request: Request, id: int, db: Session = Depends(get_db)):
    """Payment recording page"""
    user = request.session.get("user")
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/login", status_code=302)
    
    return templates.TemplateResponse("billing/payment_record.html", {
        "request": request,
        "user": user,
        "bill_id": id,
        "title": "Record Payment",
    })


@router.get("/reports", response_class=HTMLResponse)
async def billing_reports_page(request: Request, db: Session = Depends(get_db)):
    """Billing reports page"""
    user = request.session.get("user")
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/login", status_code=302)
    
    return templates.TemplateResponse("billing/billing_reports.html", {
        "request": request,
        "user": user,
        "title": "Billing Reports",
    })
