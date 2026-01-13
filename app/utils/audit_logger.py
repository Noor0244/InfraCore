from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import inspect

from app.models.activity_log import ActivityLog


ACTIONS = {"CREATE", "UPDATE", "DELETE", "ARCHIVE", "LOGIN", "LOGOUT"}


def _safe_json(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except Exception:
        try:
            return json.dumps(str(value), ensure_ascii=False)
        except Exception:
            return None


def model_to_dict(obj: Any) -> dict[str, Any]:
    try:
        mapper = inspect(obj).mapper
        out: dict[str, Any] = {}
        for attr in mapper.column_attrs:
            key = attr.key
            try:
                out[key] = getattr(obj, key)
            except Exception:
                out[key] = None
        return out
    except Exception:
        return {}


def get_client_ip(request) -> str | None:
    try:
        # Prefer proxy header if present
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip() or None
        if request.client:
            return request.client.host
    except Exception:
        return None
    return None


def log_action(
    db: Session,
    request,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    description: str = "",
    old_value: Any = None,
    new_value: Any = None,
) -> None:
    """Central audit logger.

    - Reads user from request.session
    - Stores cached username/role
    - Commits safely
    - Never raises (won't crash main flow)
    """

    try:
        user = None
        try:
            user = request.session.get("user") if request else None
        except Exception:
            user = None

        username = "SYSTEM"
        role = None
        user_id = None
        if user:
            user_id = user.get("id")
            username = user.get("username") or username
            role = user.get("role")

        act = (action or "").upper().strip()
        if act and act not in ACTIONS:
            # Keep it lenient; store raw string
            pass

        entry = ActivityLog(
            user_id=user_id,
            username=username,
            role=role,
            action=act or "UPDATE",
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            old_value=_safe_json(old_value),
            new_value=_safe_json(new_value),
            ip_address=get_client_ip(request),
            created_at=datetime.utcnow(),
            # Legacy
            details=description,
            timestamp=datetime.utcnow(),
        )

        db.add(entry)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return
