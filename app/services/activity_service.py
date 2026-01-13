from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog


def log_activity(
    db: Session,
    user: dict,
    action: str,
    details: str | None = None,
):
    log = ActivityLog(
        user_id=user.get("id"),
        username=user.get("username"),
        action=action,
        details=details,
    )

    db.add(log)
    db.commit()


def get_recent_activities(db: Session, limit: int = 50):
    return (
        db.query(ActivityLog)
        .order_by(ActivityLog.timestamp.desc())
        .limit(limit)
        .all()
    )
