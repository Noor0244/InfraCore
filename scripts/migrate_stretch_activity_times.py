"""SQLite migration: add planned_start_time/planned_end_time to stretch_activities.

Run:
  C:/Users/Benz/Desktop/InfraCore/venv/Scripts/python.exe scripts/migrate_stretch_activity_times.py

Idempotent:
- Can be run multiple times.
- Uses PRAGMA table_info to detect existing columns.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text

from app.db.session import engine


def _columns(table: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
        return {str(r[1]) for r in rows}


def _add_column(table: str, ddl: str) -> None:
    with engine.connect() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
        conn.commit()


def _safe_add(table: str, col: str, ddl: str) -> bool:
    cols = _columns(table)
    if col in cols:
        return False
    _add_column(table, ddl)
    return True


def main() -> None:
    changes: list[str] = []

    if _safe_add("stretch_activities", "planned_start_time", "planned_start_time VARCHAR(10)"):
        changes.append("stretch_activities.planned_start_time")

    if _safe_add("stretch_activities", "planned_end_time", "planned_end_time VARCHAR(10)"):
        changes.append("stretch_activities.planned_end_time")

    print("Migration complete.")
    if changes:
        print("Added columns:")
        for c in changes:
            print(" -", c)
    else:
        print("No changes needed (already migrated).")


if __name__ == "__main__":
    main()
