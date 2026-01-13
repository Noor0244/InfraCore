# app/routes/materials.py
# --------------------------------------------------
# Material CRUD API (FIXED)
# InfraCore
# --------------------------------------------------

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text

from app.db.session import SessionLocal, engine
from app.models.material import Material
from app.utils.id_codes import generate_next_code

router = APIRouter(
    prefix="/materials",
    tags=["Materials"]
)


# ---------------- AUTO UNITS: SAFE DB EXTENSION ----------------
# InfraCore uses SQLite by default. We add columns if missing.
def _ensure_material_unit_columns() -> None:
    try:
        insp = inspect(engine)
        cols = {c.get("name") for c in insp.get_columns("materials")}
        with engine.begin() as conn:
            if "standard_unit" not in cols:
                conn.execute(text("ALTER TABLE materials ADD COLUMN standard_unit VARCHAR(50)"))
            if "allowed_units" not in cols:
                conn.execute(text("ALTER TABLE materials ADD COLUMN allowed_units TEXT"))
    except Exception:
        # Never block app startup/routes if migration can't run
        return


_ensure_material_unit_columns()


# ---------------- AUTO UNITS: FALLBACK CONFIG ----------------
# Used when DB fields are empty (or not yet populated).
DEFAULT_UNIT_CHOICES: list[str] = [
    "Bags",
    "Kg",
    "MT",
    "Cum",
    "Ton",
    "Nos",
    "Ltr",
]

FALLBACK_UNIT_CONFIG_BY_NAME: dict[str, dict[str, object]] = {
    "cement": {"standard_unit": "Bags", "allowed_units": ["Bags", "Kg", "MT"]},
    "sand": {"standard_unit": "Cum", "allowed_units": ["Cum", "Ton"]},
    "bitumen": {"standard_unit": "Kg", "allowed_units": ["Kg", "Ton"]},
    "steel": {"standard_unit": "Kg", "allowed_units": ["Kg", "Ton"]},
    "aggregate": {"standard_unit": "Cum", "allowed_units": ["Cum", "Ton"]},
}


def _resolve_units(material: Material) -> tuple[str, list[str]]:
    # Prefer per-row config if present
    allowed = material.get_allowed_units(default_unit_choices=DEFAULT_UNIT_CHOICES)
    standard = material.get_standard_unit(default_unit_choices=DEFAULT_UNIT_CHOICES)

    # If not configured, try fallback mapping by name
    if (not material.allowed_units and not material.standard_unit) and material.name:
        cfg = FALLBACK_UNIT_CONFIG_BY_NAME.get(material.name.strip().lower())
        if cfg:
            standard = str(cfg.get("standard_unit") or standard or "") or (standard or "")
            allowed = list(cfg.get("allowed_units") or allowed or DEFAULT_UNIT_CHOICES)

    # Final safety: ensure dropdown is never empty
    allowed = [u for u in (allowed or []) if str(u).strip()]
    if not allowed:
        allowed = list(DEFAULT_UNIT_CHOICES)
    if not standard:
        standard = allowed[0]
    if standard not in allowed:
        allowed = [standard] + [u for u in allowed if u != standard]
    return standard, allowed

# ---------------- DB DEPENDENCY ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- CREATE MATERIAL ----------------
@router.post("/")
def create_material(
    name: str,
    unit: str,
    lead_time_days: int,
    minimum_stock: float = 0,
    standard_unit: str | None = None,
    allowed_units: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Create a material.
    Example: Aggregate, Bitumen, Cement
    """

    # Backward-compatible: `unit` remains required and continues to work as-is.
    # If auto-units config is provided, validate it.
    su = standard_unit.strip() if standard_unit else None
    au = allowed_units.strip() if allowed_units else None
    if au:
        # Validate comma-separated or JSON list via model helper after persist.
        # Here we do minimal consistency checks.
        if su and su not in au and au.startswith("["):
            # JSON list will be validated via Material helper indirectly; keep lenient here.
            pass
        elif su and su not in [p.strip() for p in au.split(",") if p.strip()] and not au.startswith("["):
            raise HTTPException(status_code=400, detail="standard_unit must be included in allowed_units")
    material = Material(
        name=name,
        unit=unit,
        standard_unit=su,
        allowed_units=au,
        lead_time_days=lead_time_days,
        minimum_stock=minimum_stock,
    )

    material.code = generate_next_code(db, Material, code_attr="code", prefix="MAT", width=6)

    try:
        db.add(material)
        db.commit()
        db.refresh(material)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Material creation failed (duplicate or DB constraint)"
        )

    return {
        "status": "success",
        "material_id": material.id,
        "name": material.name,
        "unit": material.unit,
        "standard_unit": getattr(material, "standard_unit", None),
        "allowed_units": getattr(material, "allowed_units", None),
        "lead_time_days": material.lead_time_days,
        "minimum_stock": material.minimum_stock,
    }


# ---------------- GET MATERIAL UNITS ----------------
@router.get("/{material_id}/units")
def get_material_units(material_id: int, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    standard, allowed = _resolve_units(material)
    return {
        "standard_unit": standard,
        "allowed_units": allowed,
    }


# ---------------- LIST MATERIALS ----------------
@router.get("/")
def list_materials(db: Session = Depends(get_db)):
    """
    List all materials.
    """

    materials = db.query(Material).all()

    return [
        {
            "id": m.id,
            "name": m.name,
            "unit": m.unit,
            "standard_unit": getattr(m, "standard_unit", None),
            "allowed_units": getattr(m, "allowed_units", None),
            "lead_time_days": m.lead_time_days,
            "minimum_stock": m.minimum_stock,
        }
        for m in materials
    ]
