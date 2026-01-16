import json

from sqlalchemy import Column, Integer, ForeignKey, String, Numeric
from sqlalchemy.orm import relationship
from app.db.base import Base


class PlannedMaterial(Base):
    __tablename__ = "planned_materials"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)

    # Optional stretch-scoped planning (Road only)
    stretch_id = Column(Integer, ForeignKey("road_stretches.id"), nullable=True, index=True)

    # Project-level unit lock (selected at project creation)
    unit = Column(String(50), nullable=True)
    allowed_units = Column(String(500), nullable=True)

    # Quantity (max 5 decimals for stretch-level quantities)
    planned_quantity = Column(Numeric(18, 5), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="planned_materials")
    material = relationship("Material")

    # ---------------- Helpers ----------------
    def parsed_allowed_units(self) -> list[str]:
        raw = (self.allowed_units or "").strip()
        if not raw:
            return []

        if raw.startswith("["):
            try:
                value = json.loads(raw)
                if isinstance(value, list):
                    return [str(v).strip() for v in value if str(v).strip()]
            except Exception:
                return []

        return [p.strip() for p in raw.split(",") if p.strip()]

    def get_allowed_units(self, fallback: list[str] | None = None) -> list[str]:
        allowed = self.parsed_allowed_units()
        if allowed:
            return allowed
        if self.unit:
            return [self.unit]
        return list(fallback or [])
