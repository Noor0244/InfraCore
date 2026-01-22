from fastapi import status, APIRouter, Request, Depends, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from app.db.session import get_db
from app.models.material import Material
from app.models.material_vendor import MaterialVendor
from app.models.project import Project
from app.models.activity import Activity
from app.models.road_stretch import RoadStretch
from app.models.material_activity import MaterialActivity
from app.models.material_stretch import MaterialStretch

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# --- AJAX endpoints for Material–Activity and Material–Stretch linking ---
# Get current activities linked to a material
@router.get("/material/{material_id}/activities")
def get_material_activities(material_id: int, db: Session = Depends(get_db)):
    links = db.query(MaterialActivity).filter(MaterialActivity.material_id == material_id).all()
    return {"activity_ids": [link.activity_id for link in links]}

# Update activities linked to a material (replace all)
@router.post("/material/{material_id}/activities")
async def set_material_activities(material_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    activity_ids = data.get("activity_ids", [])
    # Remove old links
    db.query(MaterialActivity).filter(MaterialActivity.material_id == material_id).delete()
    # Add new links
    for aid in activity_ids:
        db.add(MaterialActivity(material_id=material_id, activity_id=aid))
    db.commit()
    return JSONResponse({"success": True, "activity_ids": activity_ids})

# Get current stretches linked to a material
@router.get("/material/{material_id}/stretches")
def get_material_stretches(material_id: int, db: Session = Depends(get_db)):
    links = db.query(MaterialStretch).filter(MaterialStretch.material_id == material_id).all()
    return {"stretch_ids": [link.stretch_id for link in links]}

# Update stretches linked to a material (replace all)
@router.post("/material/{material_id}/stretches")
async def set_material_stretches(material_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    stretch_ids = data.get("stretch_ids", [])
    # Remove old links
    db.query(MaterialStretch).filter(MaterialStretch.material_id == material_id).delete()
    # Add new links
    for sid in stretch_ids:
        db.add(MaterialStretch(material_id=material_id, stretch_id=sid))
    db.commit()
    return JSONResponse({"success": True, "stretch_ids": stretch_ids})
    form = await request.form()
    vendor_name = form.get("vendor_name")
    material_id = form.get("materials_supplied")
    lead_time = form.get("lead_time")
    # You can extract more fields as needed
    if not vendor_name or not material_id:
        return RedirectResponse("/project/1/materials?error=Missing+required+fields", status_code=303)

    new_vendor = MaterialVendor(
        vendor_name=vendor_name,
        material_id=material_id,
        lead_time_days=int(lead_time) if lead_time else 0,
        # Add more fields as needed
    )
    db.add(new_vendor)
    db.commit()
    db.refresh(new_vendor)
    # Redirect to a relevant page (adjust project_id as needed)
    return RedirectResponse("/project/1/materials?success=Vendor+added", status_code=303)
@router.post("/project/{project_id}/materials/add")
async def add_material(request: Request, project_id: int, db: Session = Depends(get_db)):
    form = await request.form()
    # Extract form fields (adjust as needed)
    name = form.get("material_name")
    category = form.get("material_category")
    unit = form.get("unit")
    material_type = form.get("material_type")
    # Add more fields as needed


    # Check if material with the same name already exists
    existing_material = db.query(Material).filter(Material.name == name).first()
    if existing_material:
        # Redirect back with error message in query string
        return RedirectResponse(
            f"/project/{project_id}/materials?error=Material+with+name+{name}+already+exists",
            status_code=303
        )

    # Create and add new Material
    new_material = Material(
        name=name,
        category=category,
        unit=unit,
        # Add more fields as needed
    )
    db.add(new_material)
    db.commit()
    db.refresh(new_material)

    # Redirect back to the materials page
    return RedirectResponse(f"/project/{project_id}/materials", status_code=303)




# Always require a project_id in the URL for project-specific context
@router.get("/project/{project_id}/materials", response_class=None)
def material_vendor_page(request: Request, project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    # Get all active projects for selection dropdown
    projects = db.query(Project).filter(Project.is_active == True).all()
    # Use FastAPI dependency for session
    def get_project_data(project):
        if not project:
            return None
        from fastapi import APIRouter, Request, Depends, Form
        from fastapi.responses import RedirectResponse
        from fastapi.templating import Jinja2Templates
        from sqlalchemy.orm import Session, selectinload
        from app.db.session import get_db
        from app.models.material import Material
        from app.models.material_vendor import MaterialVendor
        from app.models.project import Project
        from app.models.activity import Activity
        from app.models.road_stretch import RoadStretch

        router = APIRouter()
        templates = Jinja2Templates(directory="app/templates")
        return {
            "id": project.id,
            "name": project.name,
            "location": project.location,
            "planned_start_date": project.planned_start_date,
            "planned_end_date": project.planned_end_date,
            "status": project.status,
        }

    # Eagerly load vendors for each material
    materials = (
        db.query(Material)
        .filter(Material.is_active == True)
        .options(selectinload(Material.vendors))
        .all()
    )

    project = db.query(Project).filter(Project.id == project_id).first()
    project_data = get_project_data(project)

    activities = db.query(Activity).filter(Activity.project_id == project_id).all() if project else []
    stretches = db.query(RoadStretch).filter(RoadStretch.project_id == project_id).all() if project else []
    alerts = [] # TODO: Populate with real alert logic

    # Prepare materials for template (avoid lazy loading)
    materials_data = []
    for m in materials:
        vendors_data = [
            {"id": v.id, "vendor_name": v.vendor_name}
            for v in m.vendors
        ]
        materials_data.append({
            "id": m.id,
            "name": m.name,
            "vendors": vendors_data,
        })

    # Use session user if available, fallback only if not
    user = request.session.get("user") if hasattr(request, "session") and request.session.get("user") else request.scope.get("user") if "user" in request.scope else None
    if user is None:
        user = {"username": "Guest", "role": "admin"}
    return templates.TemplateResponse("material_vendor.html", {
        "request": request,
        "project": project_data,
        "projects": projects,
        "materials": materials_data,
        "activities": activities,
        "stretches": stretches,
        "alerts": alerts,
        "user": user
    })

# ...existing code for POST endpoints...
