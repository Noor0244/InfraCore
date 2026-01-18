from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from app.db.base import Base

class ProjectMaterialVendor(Base):
    __tablename__ = "project_material_vendors"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("material_vendors.id"), nullable=False, index=True)
    lead_time_days = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
