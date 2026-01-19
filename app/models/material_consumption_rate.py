from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String, UniqueConstraint
from datetime import datetime
from app.db.base import Base

class MaterialConsumptionRate(Base):
    __tablename__ = "material_consumption_rates"
    __table_args__ = (
        UniqueConstraint("project_id", "activity_id", "material_id", name="uq_material_rate"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    baseline_rate = Column(Float, nullable=False)  # e.g., qty per unit length or activity qty
    rate_type = Column(String(30), nullable=False, default="per_length")  # or "per_activity_qty"
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
