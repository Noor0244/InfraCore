from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text

from app.db.base import Base


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    project_type = Column(String(50), nullable=True)
    mode = Column(String(30), nullable=False, default="Inventory")  # Inventory/Delay/Cost/Combined

    inputs_json = Column(Text, nullable=False)
    outputs_json = Column(Text, nullable=False)

    action_taken = Column(String(80), nullable=True)  # e.g. Reorder now / Increase safety stock

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
