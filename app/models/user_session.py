from sqlalchemy import Column, Integer, DateTime, ForeignKey
from datetime import datetime

from app.db.base import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    login_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    logout_time = Column(DateTime, nullable=True)

    # total session duration in seconds
    session_duration = Column(Integer, nullable=True)
