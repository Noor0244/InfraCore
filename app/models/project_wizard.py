from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text

from app.db.base import Base


class ProjectWizardState(Base):
    __tablename__ = "project_wizard_states"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # JSON blob containing wizard fields across steps.
    state_json = Column(Text, nullable=False, default="{}")

    current_step = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Basic TTL to avoid DB bloat if users abandon the wizard.
    expires_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(days=7))
