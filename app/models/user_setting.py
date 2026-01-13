from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.db.base import Base


class UserSetting(Base):
    __tablename__ = "user_settings"

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_user_settings_user_key"),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    key = Column(String(120), nullable=False, index=True)
    value = Column(String(500), nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
