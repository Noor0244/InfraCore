from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base

class MaterialStretch(Base):
    __tablename__ = "material_stretches"
    __table_args__ = (UniqueConstraint("material_id", "stretch_id", name="uq_material_stretch"),)

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    stretch_id = Column(Integer, ForeignKey("road_stretches.id"), nullable=False, index=True)

    material = relationship("Material", back_populates="stretches_link")
    stretch = relationship("RoadStretch", back_populates="materials_link")
