from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, get_db
from app.models.material import Material
from app.models.material_stock import MaterialStock
from app.models.project import Project
from datetime import datetime
from app.utils.flash import flash
from app.utils.template_filters import register_template_filters
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix="/stock",
    tags=["Material Stock"]
)
templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def add_material_stock(
    project_id: int,
    material_id: int,
    quantity_available: float,
    location: str | None = None,
    db: Session = Depends(get_db)
):
    if quantity_available < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")

    stock = MaterialStock(
        project_id=project_id,
        material_id=material_id,
        quantity_available=quantity_available,
        location=location
    )

    db.add(stock)
    db.commit()
    db.refresh(stock)

    return {
        "status": "success",
        "message": "Material stock added",
        "stock_id": stock.id
    }


@router.get("/current", response_class=HTMLResponse)
def current_stock_page(request: Request, db: Session = Depends(get_db)):
    # Get project_id from query or session (if available)
    project_id = request.query_params.get("project_id")
    if not project_id:
        project_id = request.session.get("project_id")
    user = request.session.get("user")
    
    # Apply admin project isolation
    if user and user.get("role") == "superadmin":
        projects = db.query(Project).filter(Project.is_active == True).order_by(Project.name.asc()).all()
    elif user and user.get("role") == "admin":
        projects = db.query(Project).filter(
            Project.is_active == True,
            Project.created_by == user["id"]
        ).order_by(Project.name.asc()).all()
    else:
        projects = []
    
    # Get project details and stretches
    project = None
    stretches = []
    if project_id:
        from app.models.road_stretch import RoadStretch
        project = db.query(Project).filter(Project.id == int(project_id)).first()
        stretches = db.query(RoadStretch).filter(RoadStretch.project_id == int(project_id)).order_by(RoadStretch.sequence_no.asc()).all()
    
    if project_id:
        stocks = db.query(MaterialStock).filter(MaterialStock.project_id == int(project_id)).all()
        # PROJECT-SPECIFIC: Only show materials that are added to this project
        from app.models.planned_material import PlannedMaterial
        project_material_ids = (
            db.query(PlannedMaterial.material_id)
            .filter(PlannedMaterial.project_id == int(project_id))
            .distinct()
            .subquery()
        )
        materials = (
            db.query(Material)
            .filter(Material.id.in_(project_material_ids))
            .order_by(Material.name.asc())
            .all()
        )
    else:
        stocks = db.query(MaterialStock).all()
        materials = db.query(Material).all()
    # Prepare stock data for template
    stock_data = []
    for s in stocks:
        stock_data.append({
            "id": s.id,
            "material_name": s.material.name if s.material else "",
            "quantity": s.quantity_available,
            "unit": getattr(s, 'unit', ''),
            "updated_at": s.last_updated,
            "location": getattr(s, 'location', ''),
        })
    return templates.TemplateResponse(
        "current_stock.html",
        {
            "request": request,
            "stocks": stock_data,
            "materials": materials,
            "project_id": project_id,
            "project": project,
            "stretches": stretches,
            "projects": projects,
            "user": user,
        }
    )


@router.post("/add")
def add_stock(request: Request, db: Session = Depends(get_db), project_id: int = Form(...), material_id: int = Form(...), quantity: float = Form(...), unit: str = Form(...), location: str = Form(None)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=302)
    
    # Check if stock already exists for this material
    existing = db.query(MaterialStock).filter(
        MaterialStock.project_id == project_id,
        MaterialStock.material_id == material_id
    ).first()
    
    if existing:
        # Update existing stock
        existing.quantity_available = float(existing.quantity_available or 0) + quantity
        existing.last_updated = datetime.utcnow()
        flash(request, f"Stock updated: added {quantity} {unit}", "success")
    else:
        # Create new stock entry
        stock = MaterialStock(
            project_id=project_id,
            material_id=material_id,
            quantity_available=quantity,
            location=location,
            last_updated=datetime.utcnow()
        )
        db.add(stock)
        flash(request, f"Stock added: {quantity} {unit}", "success")
    
    db.commit()
    return RedirectResponse(f"/stock/current?project_id={project_id}", status_code=303)
    flash(request, "Stock added successfully!", "success")
    return RedirectResponse(f"/stock/current?project_id={project_id}", status_code=302)


@router.post("/remove/{stock_id}")
def remove_stock(request: Request, stock_id: int, db: Session = Depends(get_db)):
    stock = db.query(MaterialStock).filter(MaterialStock.id == stock_id).first()
    if stock:
        db.delete(stock)
        db.commit()
        flash(request, "Stock removed successfully!", "success")
    return RedirectResponse("/stock/current", status_code=302)
