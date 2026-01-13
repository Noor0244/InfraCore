from sqlalchemy import Column, Integer, Float, Date, ForeignKey, DateTime, String
from datetime import datetime

from app.db.base import Base


class DailyEntry(Base):
    __tablename__ = "daily_entries"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)

    quantity_done = Column(Float, nullable=False)

    # Optional time-based execution for the same activity/date.
    # Base unit = hours. Kept separate to avoid breaking legacy quantity-based flows.
    quantity_done_hours = Column(Float, nullable=False, default=0.0)

    # Optional remarks (used by DPR-style daily execution)
    remarks = Column(String(2000), nullable=True)

    entry_date = Column(Date, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
