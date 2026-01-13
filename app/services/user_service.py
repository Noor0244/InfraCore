from sqlalchemy.orm import Session

from app.models.user import User
from app.core.security import verify_password


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """
    Authenticate user by username and password.
    Returns User if valid, otherwise None.
    """

    if not username or not password:
        return None

    # Normalize username (optional but recommended)
    username = username.strip()

    user = db.query(User).filter(User.username == username).first()

    if not user:
        return None

    # IMPORTANT: this field name MUST match your User model
    if not verify_password(password, user.password_hash):
        return None

    return user
