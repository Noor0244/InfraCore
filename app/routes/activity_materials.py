# app/routes/activity_materials.py
# --------------------------------------------------
# Activity-Material Mapping CRUD API (FIXED)
# InfraCore
# --------------------------------------------------

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from datetime import datetime

from app.db.session import SessionLocal
from app.models.activity_material import ActivityMaterial
from app.models.activity import Activity
from app.models.material import Material
from app.models.project_material_vendor import ProjectMaterialVendor
from app.models.road_stretch import RoadStretch as Stretch
from app.models.project import Project
from app.models.ssr import SSRUnit
from app.utils.audit_logger import log_action, model_to_dict

router = APIRouter(
    prefix="/activity-materials",
    tags=["Activity Materials"]
)

# ---------------- DB DEPENDENCY ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- CREATE MAPPING ----------------
@router.post("/")
def create_activity_material(
    request: Request,
    activity_id: int,
    material_id: int,
    consumption_rate: float,
    db: Session = Depends(get_db),
):
    """
    Map material consumption to an activity.
    consumption_rate = material required per 1 unit of activity
    """

    # Validate Activity
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate Material
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # 🔒 Prevent duplicate mapping
    existing = (
        db.query(ActivityMaterial)
        .filter(
            ActivityMaterial.activity_id == activity_id,
            ActivityMaterial.material_id == material_id
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Mapping already exists"
        )

    mapping = ActivityMaterial(
        activity_id=activity_id,
        material_id=material_id,
        consumption_rate=consumption_rate,
    )

    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    log_action(
        db=db,
        request=request,
        action="CREATE",
        entity_type="ActivityMaterial",
        entity_id=mapping.id,
        description=f"Material mapped to activity: activity #{activity_id}, material #{material_id}",
        old_value=None,
        new_value={
            "mapping": model_to_dict(mapping),
            "activity": {"id": activity.id, "name": activity.name},
            "material": {"id": material.id, "name": material.name},
        },
    )

    return {
        "id": mapping.id,
        "activity": activity.name,
        "material": material.name,
        "consumption_rate": mapping.consumption_rate,
    }


# ---------------- LIST MAPPINGS ----------------
@router.get("/")
def list_activity_materials(db: Session = Depends(get_db)):
    """
    List all activity-material mappings (JOINED).
    """

    mappings = (
        db.query(ActivityMaterial, Activity, Material)
        .join(Activity, Activity.id == ActivityMaterial.activity_id)
        .join(Material, Material.id == ActivityMaterial.material_id)
        .order_by(ActivityMaterial.id)
        .all()
    )

    return [
        {
            "id": am.id,
            "activity_id": act.id,
            "activity": act.name,
            "material_id": mat.id,
            "material": mat.name,
            "material_unit": mat.unit,
            "consumption_rate": am.consumption_rate,
        }
        for am, act, mat in mappings
    ]


# --- New API for Activity-Material Linking ---
@router.get("/api/projects/{project_id}/stretches")
def get_project_stretches(project_id: int, db: Session = Depends(get_db)):
    stretches = db.query(Stretch).filter(Stretch.project_id == project_id).all()
    return [ {"id": s.id, "name": s.stretch_name} for s in stretches ]

@router.get("/api/stretches/{stretch_id}/activities")
def get_stretch_activities(stretch_id: int, db: Session = Depends(get_db)):
    acts = db.query(Activity).filter(Activity.stretch_id == stretch_id).all()
    return [ {"id": a.id, "name": a.activity_name} for a in acts ]

@router.get("/api/activity/{activity_id}/materials")
def get_activity_materials(activity_id: int, db: Session = Depends(get_db)):
    ams = db.query(ActivityMaterial).filter(ActivityMaterial.activity_id == activity_id, ActivityMaterial.is_active == True).all()
    return [ {"id": am.project_material_id} for am in ams ]

@router.post("/inventory/activity-materials/save")
async def save_activity_materials(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    project_id = data["project_id"]
    stretch_id = data["stretch_id"]
    activity_id = data["activity_id"]
    selected_material_ids = set(data["material_ids"])
    # Deactivate all existing mappings not in selected_material_ids
    existing = db.query(ActivityMaterial).filter(
        ActivityMaterial.project_id == project_id,
        ActivityMaterial.stretch_id == stretch_id,
        ActivityMaterial.activity_id == activity_id
    ).all()
    for am in existing:
        if am.project_material_id not in selected_material_ids and am.is_active:
            am.is_active = False
    # Add new mappings
    existing_ids = {am.project_material_id for am in existing if am.is_active}
    for mid in selected_material_ids:
        if mid not in existing_ids:
            db.add(ActivityMaterial(
                project_id=project_id,
                stretch_id=stretch_id,
                activity_id=activity_id,
                project_material_id=mid,
                is_active=True,
                created_at=datetime.utcnow()
            ))
    db.commit()
    return JSONResponse({"success": True})
