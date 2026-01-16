import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import engine
from sqlalchemy import text


def column_names(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
    return {str(r[1]) for r in rows}


def index_names(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA index_list('{table}')")).fetchall()
    return {str(r[1]) for r in rows}


with engine.connect() as conn:
    cols = column_names(conn, "planned_materials")
    print("planned_materials columns (before):", sorted(cols))

    if "stretch_id" not in cols:
        try:
            conn.execute(text("ALTER TABLE planned_materials ADD COLUMN stretch_id INTEGER"))
            print("added stretch_id")
        except Exception as exc:
            print("add stretch_id failed:", exc)

    if "unit" not in cols:
        try:
            conn.execute(text("ALTER TABLE planned_materials ADD COLUMN unit VARCHAR(50)"))
            print("added unit")
        except Exception as exc:
            print("add unit failed:", exc)

    if "allowed_units" not in cols:
        try:
            conn.execute(text("ALTER TABLE planned_materials ADD COLUMN allowed_units VARCHAR(500)"))
            print("added allowed_units")
        except Exception as exc:
            print("add allowed_units failed:", exc)

    # Add index for stretch_id to speed lookup/filtering.
    idx = index_names(conn, "planned_materials")
    if "ix_planned_materials_stretch_id" not in idx:
        try:
            conn.execute(text("CREATE INDEX ix_planned_materials_stretch_id ON planned_materials (stretch_id)"))
            print("added index ix_planned_materials_stretch_id")
        except Exception as exc:
            print("add index failed:", exc)

    cols_after = column_names(conn, "planned_materials")
    print("planned_materials columns (after):", sorted(cols_after))
