"""SQLite migration: create stretch_material_exclusions table.

InfraCore does not currently use Alembic.
The app also calls Base.metadata.create_all() on startup, but this script is
useful for existing DBs without restarting the server.

Run:
  C:/Users/Benz/Desktop/InfraCore/venv/Scripts/python.exe scripts/migrate_stretch_material_exclusions.py

Idempotent:
- Uses CREATE TABLE IF NOT EXISTS.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text

from app.db.session import engine


def main() -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS stretch_material_exclusions (
        id INTEGER PRIMARY KEY,
        stretch_id INTEGER NOT NULL,
        material_id INTEGER NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_stretch_material_exclusions UNIQUE (stretch_id, material_id),
        FOREIGN KEY(stretch_id) REFERENCES road_stretches(id) ON DELETE CASCADE,
        FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE CASCADE
    );
    """
    with engine.connect() as conn:
        conn.execute(text(ddl))
        conn.commit()

    print("Migration complete. Ensured table: stretch_material_exclusions")


if __name__ == "__main__":
    main()
