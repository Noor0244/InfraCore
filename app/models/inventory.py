from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from datetime import datetime

from app.db.base import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)

    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)

    quantity_available = Column(Float, nullable=False)

    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
