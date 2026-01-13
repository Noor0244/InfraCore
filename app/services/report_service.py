from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date

from app.models.report import Report
from app.db.session import SessionLocal


# ================= REPORT CRUD =================

def get_all_reports(db: Session):
    return (
        db.query(Report)
        .order_by(Report.report_date.desc().nullslast())
        .all()
    )


def get_report(db: Session, report_id: int):
    return db.query(Report).filter(Report.id == report_id).first()


def create_report(
    db: Session,
    report_type: str,
    description: str,
    report_date,
):
    report = Report(
        report_type=report_type,
        description=description,
        report_date=report_date,
    )

    try:
        db.add(report)
        db.commit()
        db.refresh(report)
        return report
    except Exception:
        db.rollback()
        raise


def update_report(
    db: Session,
    report_id: int,
    report_type: str,
    description: str,
    report_date,
):
    report = get_report(db, report_id)
    if not report:
        return None

    report.report_type = report_type
    report.description = description
    report.report_date = report_date

    try:
        db.commit()
        db.refresh(report)
        return report
    except Exception:
        db.rollback()
        raise


def delete_report(db: Session, report_id: int):
    report = get_report(db, report_id)
    if not report:
        return None

    try:
        db.delete(report)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


# ================= DASHBOARD SUMMARY =================
def get_summary(project_id: int | None = None):
    """
    Dashboard summary.
    NOTE:
    - Reports are GLOBAL right now
    - project_id is ignored (kept for future upgrade)
    """

    db = SessionLocal()
    try:
        base_query = db.query(Report)

        # ❌ DO NOT FILTER BY project_id (column does not exist)

        total_reports = (
            base_query.with_entities(func.count(Report.id)).scalar() or 0
        )

        reports_today = (
            base_query
            .filter(Report.report_date == date.today())
            .with_entities(func.count(Report.id))
            .scalar()
            or 0
        )

        reports_by_type = (
            base_query
            .with_entities(
                Report.report_type.label("type"),
                func.count(Report.id).label("count")
            )
            .group_by(Report.report_type)
            .all()
        )

        recent_reports = (
            base_query
            .order_by(Report.report_date.desc())
            .limit(5)
            .all()
        )

        return {
            "total_reports": total_reports,
            "reports_today": reports_today,
            "reports_by_type": reports_by_type,
            "recent_reports": recent_reports,
        }

    finally:
        db.close()
