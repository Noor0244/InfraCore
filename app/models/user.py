from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # EXISTING (UNCHANGED)
    role = Column(String, default="user")

    # ✅ NEW: ENABLE / DISABLE USER
    is_active = Column(Boolean, default=True, nullable=False)

    # ✅ NEW: AUDIT FIELDS (SAFE, OPTIONAL)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
