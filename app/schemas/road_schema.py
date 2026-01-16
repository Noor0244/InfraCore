from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RoadCategory(str, Enum):
    EXPRESSWAY = "Expressway"
    NH = "National Highway (NH)"
    SH = "State Highway (SH)"
    MDR = "Major District Road (MDR)"
    ODR = "Other District Road (ODR)"
    VR = "Village / Rural Road (VR)"
    URBAN = "Urban Road"
    SERVICE = "Service Road"


class EngineeringType(str, Enum):
    FLEXIBLE = "Flexible"
    RIGID = "Rigid"
    OVERLAY = "Overlay"
    COMPOSITE = "Composite"
    URBAN = "Urban"
    RURAL = "Rural"


class PavementType(str, Enum):
    FLEXIBLE = "Flexible"
    RIGID = "Rigid"
    OVERLAY = "Overlay"
    COMPOSITE = "Composite"


class LocationIn(BaseModel):
    country: str
    state: Optional[str] = None
    district: Optional[str] = None
    city: str


class LocationOut(LocationIn):
    id: int

    class Config:
        orm_mode = True


class RoadProjectCreate(BaseModel):
    project_name: str
    location: LocationIn


class RoadProjectOut(BaseModel):
    id: int
    project_name: str
    project_type: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    location: LocationOut

    class Config:
        orm_mode = True


class RoadStretchBase(BaseModel):
    stretch_name: str
    road_category: RoadCategory
    engineering_type: EngineeringType
    start_chainage: str
    end_chainage: str
    length_m: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class RoadStretchCreate(RoadStretchBase):
    pass


class RoadStretchUpdate(BaseModel):
    stretch_name: Optional[str] = None
    road_category: Optional[RoadCategory] = None
    engineering_type: Optional[EngineeringType] = None
    start_chainage: Optional[str] = None
    end_chainage: Optional[str] = None
    length_m: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class RoadStretchOut(RoadStretchBase):
    id: int
    project_id: int

    class Config:
        orm_mode = True


class RoadGeometryIn(BaseModel):
    lanes: Optional[int] = None
    carriageway_width_m: Optional[float] = None
    shoulder_type: Optional[str] = None
    shoulder_width_m: Optional[float] = None
    median_type: Optional[str] = None
    median_width_m: Optional[float] = None
    formation_width_m: Optional[float] = None
    terrain_type: Optional[str] = None
    urban_or_rural_flag: Optional[str] = None


class RoadGeometryOut(RoadGeometryIn):
    id: int
    stretch_id: int

    class Config:
        orm_mode = True


class PavementDesignIn(BaseModel):
    pavement_type: Optional[PavementType] = None
    design_life_years: Optional[int] = None
    msa: Optional[float] = None
    subgrade_cbr: Optional[float] = None

    gsb_thickness_mm: Optional[float] = None
    wmm_thickness_mm: Optional[float] = None
    dbm_thickness_mm: Optional[float] = None
    bc_thickness_mm: Optional[float] = None

    slab_thickness_mm: Optional[float] = None
    concrete_grade: Optional[str] = None
    joint_spacing_m: Optional[float] = None
    dowel_diameter_mm: Optional[float] = None
    tie_bar_diameter_mm: Optional[float] = None
    k_value: Optional[float] = None

    existing_pavement_type: Optional[str] = None
    overlay_material: Optional[str] = None
    overlay_thickness_mm: Optional[float] = None

    apply_defaults: bool = Field(default=False)
    defaults: Optional[Dict[str, Any]] = None

    class Config:
        extra = "ignore"


class PavementDesignOut(BaseModel):
    pavement_type: Optional[PavementType] = None
    design_life_years: Optional[int] = None
    msa: Optional[float] = None
    subgrade_cbr: Optional[float] = None

    gsb_thickness_mm: Optional[float] = None
    wmm_thickness_mm: Optional[float] = None
    dbm_thickness_mm: Optional[float] = None
    bc_thickness_mm: Optional[float] = None

    slab_thickness_mm: Optional[float] = None
    concrete_grade: Optional[str] = None
    joint_spacing_m: Optional[float] = None
    dowel_diameter_mm: Optional[float] = None
    tie_bar_diameter_mm: Optional[float] = None
    k_value: Optional[float] = None

    existing_pavement_type: Optional[str] = None
    overlay_material: Optional[str] = None
    overlay_thickness_mm: Optional[float] = None

    id: int
    stretch_id: int

    class Config:
        orm_mode = True


class DprStretchSection(BaseModel):
    stretch: RoadStretchOut
    geometry: Optional[RoadGeometryOut] = None
    pavement: Optional[PavementDesignOut] = None
    warnings: List[str] = Field(default_factory=list)


class DprDataOut(BaseModel):
    project: RoadProjectOut
    stretches: List[DprStretchSection]
    chainage_summary: List[Dict[str, Any]]
    pavement_tables: List[Dict[str, Any]]
