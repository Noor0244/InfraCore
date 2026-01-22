import json

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)

    # Human-friendly ID (separate from numeric PK)
    # Example: MAT-000001
    code = Column(String(30), nullable=True, index=True)

    name = Column(String(150), nullable=False, unique=True)
    unit = Column(String(50), nullable=False)          # m3, MT, bags

    # ---------------- Inventory metadata (optional / backward-compatible) ----------------
    # Example road categories: Bitumen, Aggregates, Stone Dust, Cement, WMM/GSB
    category = Column(String(80), nullable=True)
    # Free-text or code: VG-30, 20mm, 10mm, etc.
    specification = Column(String(120), nullable=True)
    # Optional price snapshot (for volatility feature). Leave null if not used.
    unit_cost = Column(Float, nullable=True)

    # ---------------- Auto Units (optional / backward-compatible) ----------------
    # STANDARD unit: preferred default when material is selected
    # ALLOWED units: comma-separated or JSON array string
    standard_unit = Column(String(50), nullable=True)
    allowed_units = Column(String(500), nullable=True)

    # ---------------- Lead time (planning) ----------------
    # New canonical default lead time field used by vendor/lead-time planning.
    # Keep legacy `lead_time_days` for backward compatibility.
    default_lead_time_days = Column(Integer, nullable=True)

    # ✅ Legacy field (kept for backward compatibility)
    lead_time_days = Column(Integer, nullable=True, default=0)

    minimum_stock = Column(Float, nullable=False, default=0)

    # Soft-delete flag (keeps history + prevents FK issues)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Vendors (master data)
    vendors = relationship(
        "MaterialVendor",
        back_populates="material",
        cascade="all, delete-orphan",
    )

    # Many-to-many: Material <-> Activity
    activities_link = relationship(
        "MaterialActivity",
        back_populates="material",
        cascade="all, delete-orphan",
    )

    # Many-to-many: Material <-> RoadStretch
    stretches_link = relationship(
        "MaterialStretch",
        back_populates="material",
        cascade="all, delete-orphan",
    )

    # ---------------- Helpers ----------------
    def parsed_allowed_units(self) -> list[str]:
        raw = (self.allowed_units or "").strip()
        if not raw:
            return []

        # Accept either JSON (e.g. ["Kg","Ton"]) or comma-separated (e.g. "Kg,Ton")
        if raw.startswith("["):
            try:
                value = json.loads(raw)
                if isinstance(value, list):
                    return [str(v).strip() for v in value if str(v).strip()]
            except Exception:
                return []

        return [p.strip() for p in raw.split(",") if p.strip()]

    def get_allowed_units(self, default_unit_choices: list[str] | None = None) -> list[str]:
        allowed = self.parsed_allowed_units()
        if allowed:
            return allowed

        # Fallback safety: do NOT break forms if config missing
        if self.unit:
            return [self.unit]

        return list(default_unit_choices or [])

    def get_standard_unit(self, default_unit_choices: list[str] | None = None) -> str | None:
        if self.standard_unit and self.standard_unit.strip():
            return self.standard_unit.strip()

        if self.unit and self.unit.strip():
            return self.unit.strip()

        allowed = self.get_allowed_units(default_unit_choices=default_unit_choices)
        return allowed[0] if allowed else None

    def is_unit_allowed(self, unit: str | None, default_unit_choices: list[str] | None = None) -> bool:
        if not unit:
            return False
        allowed = self.get_allowed_units(default_unit_choices=default_unit_choices)
        return unit.strip() in set(allowed)
