from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class PavementDesign(Base):
    __tablename__ = "pavement_designs"

    __table_args__ = (
        UniqueConstraint("stretch_id", name="uq_pavement_designs_stretch_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    stretch_id = Column(Integer, ForeignKey("road_stretches.id"), nullable=False, index=True)

    # ---------------- COMMON ----------------
    pavement_type = Column(String(30), nullable=True)
    design_life_years = Column(Integer, nullable=True)
    msa = Column(Float, nullable=True)
    subgrade_cbr = Column(Float, nullable=True)

    # ---------------- FLEXIBLE ----------------
    gsb_thickness_mm = Column(Float, nullable=True)
    wmm_thickness_mm = Column(Float, nullable=True)
    dbm_thickness_mm = Column(Float, nullable=True)
    bc_thickness_mm = Column(Float, nullable=True)

    # ---------------- RIGID ----------------
    slab_thickness_mm = Column(Float, nullable=True)
    concrete_grade = Column(String(50), nullable=True)
    joint_spacing_m = Column(Float, nullable=True)
    dowel_diameter_mm = Column(Float, nullable=True)
    tie_bar_diameter_mm = Column(Float, nullable=True)
    k_value = Column(Float, nullable=True)

    # ---------------- OVERLAY ----------------
    existing_pavement_type = Column(String(50), nullable=True)
    overlay_material = Column(String(50), nullable=True)
    overlay_thickness_mm = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    stretch = relationship("RoadStretch", back_populates="pavement_design")
