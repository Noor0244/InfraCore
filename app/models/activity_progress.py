from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class ActivityProgress(Base):
    __tablename__ = "activity_progress"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)

    planned_start = Column(Date, nullable=False)
    planned_end = Column(Date, nullable=False)

    actual_start = Column(Date, nullable=True)
    actual_end = Column(Date, nullable=True)

    progress_percent = Column(Integer, nullable=False, default=0)

    # NOT_STARTED | IN_PROGRESS | COMPLETED | DELAYED
    status = Column(String, nullable=False, default="NOT_STARTED")

    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Optional relationships (safe, no logic)
    project = relationship("Project")
    activity = relationship("Activity")
