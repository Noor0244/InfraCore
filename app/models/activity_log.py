from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from datetime import datetime

from app.db.base import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    __table_args__ = (
        Index("ix_activity_logs_created_at", "created_at"),
        Index("ix_activity_logs_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Cached actor
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(150), nullable=False)
    role = Column(String(50), nullable=True)

    # What happened
    action = Column(String(20), nullable=False)  # CREATE, UPDATE, DELETE, ARCHIVE, LOGIN, LOGOUT
    entity_type = Column(String(50), nullable=True)  # Project, Activity, Material, User, Execution
    entity_id = Column(Integer, nullable=True)

    description = Column(Text, nullable=True)
    old_value = Column(Text, nullable=True)  # JSON string
    new_value = Column(Text, nullable=True)  # JSON string
    ip_address = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Legacy columns (kept for backward compatibility with existing DB)
    details = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
