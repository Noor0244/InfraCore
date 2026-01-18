from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.project import Project
from app.models.material import Material
from app.models.material_vendor import MaterialVendor
from app.models.project_material_vendor import ProjectMaterialVendor

router = APIRouter(prefix="/project-material-vendor", tags=["ProjectMaterialVendor"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/manage", response_class=HTMLResponse)
def manage_page(request: Request, db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    materials = db.query(Material).all()
    vendors = db.query(MaterialVendor).all()
    assignments = db.query(ProjectMaterialVendor).all()
    return templates.TemplateResponse(
        "project_material_vendor.html",
        {
            "request": request,
            "projects": projects,
            "materials": materials,
            "vendors": vendors,
            "assignments": assignments,
        },
    )

@router.post("/assign")
def assign_vendor(
    request: Request,
    project_id: int = Form(...),
    material_id: int = Form(...),
    vendor_id: int = Form(...),
    lead_time_days: int = Form(...),
    db: Session = Depends(get_db),
):
    assignment = ProjectMaterialVendor(
        project_id=project_id,
        material_id=material_id,
        vendor_id=vendor_id,
        lead_time_days=lead_time_days,
    )
    db.add(assignment)
    db.commit()
    return RedirectResponse("/project-material-vendor/manage", status_code=302)

@router.post("/delete")
def delete_assignment(
    request: Request,
    assignment_id: int = Form(...),
    db: Session = Depends(get_db),
):
    assignment = db.query(ProjectMaterialVendor).filter(ProjectMaterialVendor.id == assignment_id).first()
    if assignment:
        db.delete(assignment)
        db.commit()
    return RedirectResponse("/project-material-vendor/manage", status_code=302)
