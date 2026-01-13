from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Date,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class ProjectActivity(Base):
    __tablename__ = "project_activities"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)

    planned_quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ✅ RELATIONSHIPS (CRITICAL FIX)
    project = relationship(
        "Project",
        back_populates="project_activities"
    )

    activity = relationship(
        "Activity",
        back_populates="project_activities"
    )
