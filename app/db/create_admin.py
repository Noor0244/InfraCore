from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.user import User
from app.core.security import hash_password

def create_admin():
    # make sure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    username = "admin"
    password = "admin123"

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        print("⚠️ Admin already exists")
        return

    user = User(
        username=username,
        password_hash=hash_password(password),
        role="admin"
    )

    db.add(user)
    db.commit()

    print("✅ Admin user created")
    print("Username:", username)
    print("Password:", password)

if __name__ == "__main__":
    create_admin()
