from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.project_wizard import ProjectWizardState


@dataclass
class WizardState:
    id: int
    current_step: int
    data: dict[str, Any]


def _loads(raw: str | None) -> dict[str, Any]:
    if not (raw or "").strip():
        return {}
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def create_wizard(db: Session, *, user_id: int) -> ProjectWizardState:
    row = ProjectWizardState(user_id=user_id, state_json="{}", current_step=0, is_active=True)
    db.add(row)
    db.flush()
    return row


def get_wizard(db: Session, *, wizard_id: int, user_id: int) -> ProjectWizardState | None:
    row = (
        db.query(ProjectWizardState)
        .filter(
            ProjectWizardState.id == wizard_id,
            ProjectWizardState.user_id == user_id,
            ProjectWizardState.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not row:
        return None
    if row.expires_at and row.expires_at < datetime.utcnow():
        row.is_active = False
        db.add(row)
        db.flush()
        return None
    return row


def get_state(db: Session, *, wizard_id: int, user_id: int) -> WizardState | None:
    row = get_wizard(db, wizard_id=wizard_id, user_id=user_id)
    if not row:
        return None
    return WizardState(id=row.id, current_step=row.current_step or 0, data=_loads(row.state_json))


def update_state(
    db: Session,
    *,
    wizard_id: int,
    user_id: int,
    patch: dict[str, Any],
    current_step: int | None = None,
) -> WizardState | None:
    row = get_wizard(db, wizard_id=wizard_id, user_id=user_id)
    if not row:
        return None

    data = _loads(row.state_json)
    data.update(patch or {})
    row.state_json = _dumps(data)
    if current_step is not None:
        row.current_step = int(current_step)
    db.add(row)
    db.flush()
    return WizardState(id=row.id, current_step=row.current_step or 0, data=data)


def deactivate(db: Session, *, wizard_id: int, user_id: int) -> None:
    row = get_wizard(db, wizard_id=wizard_id, user_id=user_id)
    if not row:
        return
    row.is_active = False
    db.add(row)
    db.flush()
