"""Idempotent SQLite migration for material vendor + lead time planning.

Run:
  C:/Users/Benz/Desktop/InfraCore/venv/Scripts/python.exe scripts/migrate_material_vendors.py

This migration is safe to run multiple times.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime


def _col_names(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cur.fetchone() is not None


def _add_column_if_missing(conn: sqlite3.Connection, table: str, col_def: str, col_name: str) -> bool:
    cols = _col_names(conn, table)
    if col_name in cols:
        return False
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
    return True


def main() -> None:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "infra.db")

    if not os.path.exists(db_path):
        raise SystemExit(f"infra.db not found at: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    added: list[str] = []

    try:
        # 1) Create material_vendors
        if not _table_exists(conn, "material_vendors"):
            conn.execute(
                """
                CREATE TABLE material_vendors (
                    id INTEGER PRIMARY KEY,
                    material_id INTEGER NOT NULL,
                    vendor_name VARCHAR(200) NOT NULL,
                    contact_person VARCHAR(150),
                    phone VARCHAR(50),
                    email VARCHAR(200),
                    lead_time_days INTEGER NOT NULL DEFAULT 0,
                    min_order_qty REAL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    FOREIGN KEY(material_id) REFERENCES materials(id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS ix_material_vendors_material_id ON material_vendors(material_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_material_vendors_vendor_name ON material_vendors(vendor_name)")
            added.append("material_vendors (table)")

        # 2) materials.default_lead_time_days
        if _add_column_if_missing(conn, "materials", "default_lead_time_days INTEGER", "default_lead_time_days"):
            added.append("materials.default_lead_time_days")

        # 3) activity_materials lead-time planning columns
        if _add_column_if_missing(conn, "activity_materials", "vendor_id INTEGER", "vendor_id"):
            added.append("activity_materials.vendor_id")
        if _add_column_if_missing(conn, "activity_materials", "order_date DATE", "order_date"):
            added.append("activity_materials.order_date")
        if _add_column_if_missing(conn, "activity_materials", "lead_time_days_override INTEGER", "lead_time_days_override"):
            added.append("activity_materials.lead_time_days_override")
        if _add_column_if_missing(conn, "activity_materials", "lead_time_days INTEGER", "lead_time_days"):
            added.append("activity_materials.lead_time_days")
        if _add_column_if_missing(conn, "activity_materials", "expected_delivery_date DATE", "expected_delivery_date"):
            added.append("activity_materials.expected_delivery_date")
        if _add_column_if_missing(conn, "activity_materials", "is_material_risk BOOLEAN NOT NULL DEFAULT 0", "is_material_risk"):
            added.append("activity_materials.is_material_risk")
        if _add_column_if_missing(conn, "activity_materials", "updated_at DATETIME", "updated_at"):
            added.append("activity_materials.updated_at")

        # Backfill updated_at if missing/null
        try:
            now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
            conn.execute(
                "UPDATE activity_materials SET updated_at = COALESCE(updated_at, created_at, ?)",
                (now,),
            )
        except Exception:
            pass

        conn.commit()

    finally:
        conn.close()

    print("Migration complete.")
    if added:
        print("Added:")
        for a in added:
            print(f" - {a}")
    else:
        print("No changes needed.")


if __name__ == "__main__":
    main()
