from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    ForeignKey,
    Float,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class DailyWorkReport(Base):
    """Industry-grade Daily Progress Report (DPR/DWE).

    Header + approval + safety are stored here.
    Row-details are stored in child tables (labour/machinery/qc/delays/materials/uploads).

    Notes:
    - Kept separate from `DailyEntry` to avoid breaking existing execution/progress logic.
    - Unique per (project_id, report_date).
    """

    __tablename__ = "daily_work_reports"

    __table_args__ = (
        UniqueConstraint("project_id", "report_date", name="uq_dwr_project_date"),
    )

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    report_date = Column(Date, nullable=False, default=date.today)

    # Daily header
    weather = Column(String(20), nullable=False, default="Sunny")
    shift = Column(String(20), nullable=False, default="Day")
    work_chainage_from = Column(String(50), nullable=True)
    work_chainage_to = Column(String(50), nullable=True)
    supervisor_name = Column(String(150), nullable=False, default="")

    # Prepared by (session user)
    prepared_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    prepared_by_name = Column(String(150), nullable=True)

    # Optional engineer remarks
    engineer_remarks = Column(String(2000), nullable=True)

    # Safety
    toolbox_talk_conducted = Column(Boolean, nullable=False, default=False)
    ppe_compliance_percent = Column(Float, nullable=True)
    incident_or_near_miss = Column(Boolean, nullable=False, default=False)
    incident_description = Column(String(2000), nullable=True)

    # Approval workflow (ready)
    status = Column(String(20), nullable=False, default="Draft")  # Draft/Submitted/Approved/Rejected
    checked_by = Column(String(150), nullable=True)
    approved_by = Column(String(150), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # -------- Relationships --------
    project = relationship("Project")
    prepared_by_user = relationship("User")

    labour_rows = relationship(
        "DailyWorkLabour",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    machinery_rows = relationship(
        "DailyWorkMachinery",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    qc_rows = relationship(
        "DailyWorkQC",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    delay_rows = relationship(
        "DailyWorkDelay",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    material_rows = relationship(
        "DailyWorkMaterial",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    activity_rows = relationship(
        "DailyWorkActivity",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    uploads = relationship(
        "DailyWorkUpload",
        back_populates="report",
        cascade="all, delete-orphan",
    )
