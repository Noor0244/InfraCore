from datetime import date
from app.db.session import SessionLocal
from app.models.report import Report

def seed_reports():
    db = SessionLocal()

    reports = [
        Report(
            report_type="Labour Attendance",
            description="45 workers present on site",
            report_date=date.today()
        ),
        Report(
            report_type="Machinery Usage",
            description="Excavator operated for 6 hours",
            report_date=date.today()
        ),
        Report(
            report_type="Material",
            description="Cement and steel delivered",
            report_date=date.today()
        ),
    ]

    db.add_all(reports)
    db.commit()
    db.close()

    print("✅ Sample reports inserted")

if __name__ == "__main__":
    seed_reports()
