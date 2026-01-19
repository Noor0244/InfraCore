from sqlalchemy import Column, Integer, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.db.base import Base

class ActivityMaterial(Base):
    __tablename__ = "activity_materials"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    stretch_id = Column(Integer, ForeignKey("stretches.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    project_material_id = Column(Integer, ForeignKey("project_materials.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('project_id', 'stretch_id', 'activity_id', 'project_material_id', name='uq_activity_material'),
    )
