from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from typing import Generator
import sqlite3
import os

# ======================================================
# FIXED DATABASE PATH (ABSOLUTE & STABLE)
# ======================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'infra.db')}"

# ======================================================
# ENGINE
# ======================================================

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

# ======================================================
# SQLITE FOREIGN KEY ENFORCEMENT (CRITICAL)
# ======================================================

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# ======================================================
# SESSION
# ======================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ======================================================
# DB DEPENDENCY
# ======================================================

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Ensure all models are imported so relationship() string targets resolve.
# This is important for standalone scripts that import SessionLocal directly.
try:
    import app.db.models  # noqa: F401
except Exception:
    # Avoid hard-failing at import time; the app can still start and report a clearer error later.
    pass
