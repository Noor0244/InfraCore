from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.user_setting import UserSetting


def get_setting(db: Session, user_id: int, key: str) -> str | None:
    row = (
        db.query(UserSetting)
        .filter(UserSetting.user_id == int(user_id), UserSetting.key == str(key))
        .first()
    )
    return str(row.value) if row and row.value is not None else None


def get_int_setting(db: Session, user_id: int, key: str, default: int) -> int:
    raw = get_setting(db, user_id=user_id, key=key)
    if raw is None or str(raw).strip() == "":
        return int(default)
    try:
        return int(float(str(raw).strip()))
    except Exception:
        return int(default)


def set_setting(db: Session, user_id: int, key: str, value: str | None) -> None:
    key = str(key)
    row = (
        db.query(UserSetting)
        .filter(UserSetting.user_id == int(user_id), UserSetting.key == key)
        .first()
    )
    if row:
        row.value = None if value is None else str(value)
        row.updated_at = datetime.utcnow()
        db.add(row)
        return

    row = UserSetting(
        user_id=int(user_id),
        key=key,
        value=None if value is None else str(value),
        updated_at=datetime.utcnow(),
    )
    db.add(row)
