from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class PlannedMaterial(Base):
    __tablename__ = "planned_materials"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)

    planned_quantity = Column(Float, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="planned_materials")
    material = relationship("Material")
