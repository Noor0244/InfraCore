from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String
from datetime import datetime
from app.db.base import Base

class MaterialBufferAlert(Base):
    __tablename__ = "material_buffer_alerts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)  # "buffer_breach", "zero_stock", "late_procurement"
    predicted_date = Column(DateTime, nullable=False)
    predicted_stock = Column(Float, nullable=False)
    resolved = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)