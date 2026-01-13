"""SQLite migration: Activity time unit switching (Days ↔ Hours).

InfraCore does not currently use Alembic.
This script safely adds new columns if missing and backfills defaults.

Run:
  python scripts/migrate_activity_units.py

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
        # row: (cid, name, type, notnull, dflt_value, pk)
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

    # ---------------- activities ----------------
    if _safe_add("activities", "planned_quantity_hours", "planned_quantity_hours FLOAT NOT NULL DEFAULT 0.0"):
        changes.append("activities.planned_quantity_hours")
    if _safe_add("activities", "executed_quantity_hours", "executed_quantity_hours FLOAT NOT NULL DEFAULT 0.0"):
        changes.append("activities.executed_quantity_hours")
    if _safe_add("activities", "display_unit", "display_unit VARCHAR(10) NOT NULL DEFAULT 'hours'"):
        changes.append("activities.display_unit")
    if _safe_add("activities", "hours_per_day", "hours_per_day FLOAT NOT NULL DEFAULT 8.0"):
        changes.append("activities.hours_per_day")

    # Backfill any NULL/empty weirdness (defensive)
    with engine.connect() as conn:
        conn.execute(text("UPDATE activities SET display_unit='hours' WHERE display_unit IS NULL OR TRIM(display_unit)=''"))
        conn.execute(text("UPDATE activities SET hours_per_day=8.0 WHERE hours_per_day IS NULL OR hours_per_day<=0"))
        conn.commit()

    # ---------------- daily_work_activities ----------------
    if _safe_add("daily_work_activities", "planned_quantity_hours", "planned_quantity_hours FLOAT NOT NULL DEFAULT 0.0"):
        changes.append("daily_work_activities.planned_quantity_hours")
    if _safe_add("daily_work_activities", "display_unit", "display_unit VARCHAR(10) NOT NULL DEFAULT 'hours'"):
        changes.append("daily_work_activities.display_unit")
    if _safe_add("daily_work_activities", "hours_per_day", "hours_per_day FLOAT NOT NULL DEFAULT 8.0"):
        changes.append("daily_work_activities.hours_per_day")
    if _safe_add("daily_work_activities", "executed_today_hours", "executed_today_hours FLOAT NOT NULL DEFAULT 0.0"):
        changes.append("daily_work_activities.executed_today_hours")

    with engine.connect() as conn:
        conn.execute(text("UPDATE daily_work_activities SET display_unit='hours' WHERE display_unit IS NULL OR TRIM(display_unit)=''"))
        conn.execute(text("UPDATE daily_work_activities SET hours_per_day=8.0 WHERE hours_per_day IS NULL OR hours_per_day<=0"))
        conn.commit()

    # ---------------- daily_entries ----------------
    if _safe_add("daily_entries", "quantity_done_hours", "quantity_done_hours FLOAT NOT NULL DEFAULT 0.0"):
        changes.append("daily_entries.quantity_done_hours")

    with engine.connect() as conn:
        conn.execute(text("UPDATE daily_entries SET quantity_done_hours=0.0 WHERE quantity_done_hours IS NULL"))
        conn.commit()

    print("Migration complete.")
    if changes:
        print("Added columns:")
        for c in changes:
            print(" -", c)
    else:
        print("No changes needed (already migrated).")


if __name__ == "__main__":
    main()
