from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import csv, io

from app.db.session import SessionLocal
from app.models.report import Report
from app.utils.flash import flash
from app.utils.template_filters import register_template_filters
from app.utils.dates import parse_date_ddmmyyyy_or_iso

# ✅ ACTIVITY LOG SERVICE
from app.services.activity_service import log_activity


# ---------------- ROUTER ----------------
router = APIRouter(tags=["Reports"])
templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)


# ---------------- DB ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- LIST ----------------
@router.get("/", response_class=HTMLResponse)
def reports_page(
    request: Request,
    report_type: str | None = None,
    report_date: str | None = None,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if user is None:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    query = db.query(Report)

    if report_type:
        query = query.filter(Report.report_type == report_type)

    if report_date:
        try:
            parsed = parse_date_ddmmyyyy_or_iso(report_date)
            query = query.filter(Report.report_date == parsed)
        except Exception:
            # If a bad date is provided, treat as no filter rather than erroring.
            pass

    reports = query.order_by(Report.report_date.desc()).all()

    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "user": user,
            "reports": reports,
            "selected_type": report_type,
            "selected_date": report_date,
        },
    )


# ---------------- ADD ----------------
@router.get("/new", response_class=HTMLResponse)
def add_report_page(request: Request):
    user = request.session.get("user")
    if user is None:
        flash(request, "Please login to add a report", "warning")
        return RedirectResponse("/login", status_code=302)

    return templates.TemplateResponse(
        "add_report.html",
        {"request": request, "user": user},
    )


@router.post("/new")
def create_report(
    request: Request,
    report_type: str = Form(...),
    description: str = Form(...),
    report_date: str = Form(...),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if user is None:
        flash(request, "Session expired. Please login again.", "warning")
        return RedirectResponse("/login", status_code=302)

    try:
        parsed_date = parse_date_ddmmyyyy_or_iso(report_date)
    except Exception:
        flash(request, "Invalid date. Please use DD/MM/YYYY.", "error")
        return RedirectResponse("/reports/new", status_code=303)

    db.add(
        Report(
            report_type=report_type,
            description=description,
            report_date=parsed_date,
        )
    )
    db.commit()

    # ✅ LOG CREATE
    log_activity(
        db,
        user,
        action="CREATE_REPORT",
        details=f"Created report: {report_type}",
    )

    flash(request, "Report added successfully", "success")
    return RedirectResponse("/reports", status_code=303)


# ---------------- EDIT ----------------
@router.get("/edit/{report_id}", response_class=HTMLResponse)
def edit_report_page(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if user is None:
        flash(request, "Please login to edit reports", "warning")
        return RedirectResponse("/login", status_code=302)

    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        flash(request, "Report not found", "error")
        return RedirectResponse("/reports", status_code=302)

    return templates.TemplateResponse(
        "edit_report.html",
        {"request": request, "user": user, "report": report},
    )


@router.post("/edit/{report_id}")
def update_report(
    report_id: int,
    request: Request,
    report_type: str = Form(...),
    description: str = Form(...),
    report_date: str = Form(...),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if user is None:
        flash(request, "Session expired. Please login again.", "warning")
        return RedirectResponse("/login", status_code=302)

    report = db.query(Report).filter(Report.id == report_id).first()
    if report:
        report.report_type = report_type
        report.description = description
        try:
            report.report_date = parse_date_ddmmyyyy_or_iso(report_date)
        except Exception:
            flash(request, "Invalid date. Please use DD/MM/YYYY.", "error")
            return RedirectResponse(f"/reports/edit/{report_id}", status_code=303)
        db.commit()

        # ✅ LOG UPDATE
        log_activity(
            db,
            user,
            action="UPDATE_REPORT",
            details=f"Updated report ID {report_id}",
        )

        flash(request, "Report updated successfully", "success")
    else:
        flash(request, "Report not found", "error")

    return RedirectResponse("/reports", status_code=303)


# ---------------- DELETE (CONFIRM PAGE) ----------------
@router.get("/delete/{report_id}", response_class=HTMLResponse)
def confirm_delete_report(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if user is None:
        flash(request, "Please login to delete reports", "warning")
        return RedirectResponse("/login", status_code=302)

    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        flash(request, "Report not found", "error")
        return RedirectResponse("/reports", status_code=302)

    return templates.TemplateResponse(
        "delete_confirm.html",
        {
            "request": request,
            "user": user,
            "report": report,
        },
    )


@router.post("/delete/{report_id}")
def delete_report_confirmed(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if user is None:
        flash(request, "Session expired. Please login again.", "warning")
        return RedirectResponse("/login", status_code=302)

    report = db.query(Report).filter(Report.id == report_id).first()
    if report:
        db.delete(report)
        db.commit()

        # ✅ LOG DELETE
        log_activity(
            db,
            user,
            action="DELETE_REPORT",
            details=f"Deleted report ID {report_id}",
        )

        flash(request, "Report deleted successfully", "success")
    else:
        flash(request, "Report not found", "error")

    return RedirectResponse("/reports", status_code=303)


# ---------------- EXPORT ----------------
@router.get("/export")
def export_excel(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Description"])

    for r in db.query(Report).order_by(Report.report_date.desc()).all():
        writer.writerow([r.report_date, r.report_type, r.description])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reports.csv"},
    )
