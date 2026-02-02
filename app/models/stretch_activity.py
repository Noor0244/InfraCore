
from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class StretchActivity(Base):
    __tablename__ = "stretch_activities"

    id = Column(Integer, primary_key=True, index=True)
    stretch_id = Column(Integer, ForeignKey("stretches.id"), nullable=False, index=True)
    project_activity_id = Column(Integer, ForeignKey("project_activities.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    planned_duration_days = Column(Integer, nullable=True)
    manual_override = Column(Boolean, default=False, nullable=False)

    # Relationship will be set after both classes are defined to avoid circular import issues

    # Add stretch_materials relationship for back_populates
    stretch_materials = relationship("StretchMaterial", back_populates="stretch_activity", cascade="all, delete-orphan")
