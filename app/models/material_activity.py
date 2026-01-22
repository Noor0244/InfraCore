from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base

class MaterialActivity(Base):
    __tablename__ = "material_activities"
    __table_args__ = (UniqueConstraint("material_id", "activity_id", name="uq_material_activity"),)

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False, index=True)

    material = relationship("Material", back_populates="activities_link")
    activity = relationship("Activity", back_populates="materials_link")
