from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from app.db.base import Base


class RoadType(Base):
    __tablename__ = "road_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
