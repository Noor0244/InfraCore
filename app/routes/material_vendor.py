from fastapi import status, APIRouter, Request, Depends, Form
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
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
from app.models.planned_material import PlannedMaterial
from app.models.project_material_vendor import ProjectMaterialVendor
from app.utils.audit_logger import log_action
from app.utils.template_filters import register_template_filters

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)


def _resolve_user(request: Request):
    if hasattr(request, "session") and request.session.get("user"):
        return request.session.get("user")
    if "user" in request.scope:
        return request.scope.get("user")
    return None


@router.get("/project/{project_id}/materials/add", response_class=HTMLResponse)
def add_material_page(request: Request, project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    user = _resolve_user(request)
    if not project:
        return RedirectResponse("/projects", status_code=302)

    return templates.TemplateResponse(
        "add_material.html",
        {
            "request": request,
            "user": user,
            "project": project,
        },
    )


@router.get("/vendors/add", response_class=HTMLResponse)
def add_vendor_page(request: Request, db: Session = Depends(get_db)):
    user = _resolve_user(request)
    project_id = request.query_params.get("project_id")
    
    # PROJECT-SPECIFIC: Only show materials that are added to the project
    if project_id:
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
        # Fallback: show all materials if no project context
        materials = db.query(Material).order_by(Material.name.asc()).all()

    return templates.TemplateResponse(
        "add_vendor.html",
        {
            "request": request,
            "user": user,
            "materials": materials,
            "project_id": project_id,
        },
    )


@router.get("/project/{project_id}/materials/linker/{material_id}", response_class=HTMLResponse)
def material_linker_page(
    request: Request,
    project_id: int,
    material_id: int,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    material = db.query(Material).filter(Material.id == material_id).first()
    user = _resolve_user(request)
    if not project or not material:
        return RedirectResponse("/projects", status_code=302)

    activities = db.query(Activity).filter(Activity.project_id == project_id).all()
    stretches = db.query(RoadStretch).filter(RoadStretch.project_id == project_id).all()
    
    # PROJECT-SPECIFIC: Only show materials that are added to this project
    project_material_ids = (
        db.query(PlannedMaterial.material_id)
        .filter(PlannedMaterial.project_id == project_id)
        .distinct()
        .subquery()
    )
    materials = (
        db.query(Material)
        .filter(
            Material.is_active == True,
            Material.id.in_(project_material_ids)
        )
        .order_by(Material.name.asc())
        .all()
    )
    if material and all(int(m.id) != int(material.id) for m in materials):
        materials = materials + [material]

    return templates.TemplateResponse(
        "material_linker.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "material": material,
            "materials": materials,
            "activities": activities,
            "stretches": stretches,
        },
    )

# --- AJAX endpoints for Material–Activity and Material–Stretch linking ---
# Get current activities linked to a material
@router.get("/material/{material_id}/activities")
def get_material_activities(material_id: int, db: Session = Depends(get_db)):
    links = db.query(MaterialActivity).filter(MaterialActivity.material_id == material_id).all()
    return {
        "activity_ids": [link.activity_id for link in links],
        "activity_quantities": {str(link.activity_id): (float(link.quantity) if link.quantity is not None else None) for link in links},
        "activity_units": {str(link.activity_id): (str(link.unit) if link.unit else None) for link in links},
    }

# Update activities linked to a material (replace all)
@router.post("/material/{material_id}/activities")
async def set_material_activities(material_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    activity_ids = data.get("activity_ids", [])
    activity_quantities = data.get("activity_quantities", {}) or {}
    activity_units = data.get("activity_units", {}) or {}
    # Remove old links
    db.query(MaterialActivity).filter(MaterialActivity.material_id == material_id).delete()
    # Add new links
    for aid in activity_ids:
        qty = activity_quantities.get(str(aid))
        qty_value = float(qty) if qty is not None and str(qty).strip() != "" else None
        unit_raw = activity_units.get(str(aid))
        unit_value = str(unit_raw).strip() if unit_raw is not None and str(unit_raw).strip() != "" else None
        db.add(MaterialActivity(material_id=material_id, activity_id=aid, quantity=qty_value, unit=unit_value))
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

# Auto-assign planned materials and stretch links from a reference stretch
@router.post("/project/{project_id}/stretches/{reference_stretch_id}/auto-assign-materials")
def auto_assign_materials_from_stretch(project_id: int, reference_stretch_id: int, db: Session = Depends(get_db)):
    from decimal import Decimal

    reference_stretch = db.query(RoadStretch).filter(
        RoadStretch.id == reference_stretch_id,
        RoadStretch.project_id == project_id
    ).first()
    if not reference_stretch:
        return JSONResponse({"success": False, "error": "Reference stretch not found."}, status_code=404)

    if not reference_stretch.length_m or reference_stretch.length_m <= 0:
        return JSONResponse({"success": False, "error": "Reference stretch length is invalid."}, status_code=400)

    ref_planned = db.query(PlannedMaterial).filter(
        PlannedMaterial.project_id == project_id,
        PlannedMaterial.stretch_id == reference_stretch_id
    ).all()

    ref_material_links = db.query(MaterialStretch).filter(
        MaterialStretch.stretch_id == reference_stretch_id
    ).all()

    if not ref_planned and not ref_material_links:
        return JSONResponse({"success": False, "error": "No reference data found for this stretch."}, status_code=400)

    target_stretches = db.query(RoadStretch).filter(
        RoadStretch.project_id == project_id,
        RoadStretch.id != reference_stretch_id
    ).all()

    ref_len = Decimal(reference_stretch.length_m)
    created = 0
    updated = 0
    links_created = 0

    for target in target_stretches:
        if not target.length_m or target.length_m <= 0:
            continue
        ratio = Decimal(target.length_m) / ref_len

        for ref in ref_planned:
            planned_qty = (ref.planned_quantity or Decimal("0")) * ratio
            existing = db.query(PlannedMaterial).filter(
                PlannedMaterial.project_id == project_id,
                PlannedMaterial.stretch_id == target.id,
                PlannedMaterial.material_id == ref.material_id
            ).first()
            if existing:
                existing.planned_quantity = planned_qty
                existing.unit = ref.unit
                existing.allowed_units = ref.allowed_units
                updated += 1
            else:
                db.add(PlannedMaterial(
                    project_id=project_id,
                    material_id=ref.material_id,
                    stretch_id=target.id,
                    unit=ref.unit,
                    allowed_units=ref.allowed_units,
                    planned_quantity=planned_qty
                ))
                created += 1

        for link in ref_material_links:
            exists = db.query(MaterialStretch).filter(
                MaterialStretch.material_id == link.material_id,
                MaterialStretch.stretch_id == target.id
            ).first()
            if not exists:
                db.add(MaterialStretch(material_id=link.material_id, stretch_id=target.id))
                links_created += 1

    db.commit()
    return JSONResponse({
        "success": True,
        "message": "Auto-assignment completed.",
        "materials_created": created,
        "materials_updated": updated,
        "links_created": links_created
    })


@router.post("/project/{project_id}/stretches/auto-distribute-materials")
async def auto_distribute_materials(request: Request, project_id: int, db: Session = Depends(get_db)):
    from decimal import Decimal, ROUND_HALF_UP

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    try:
        reference_stretch_id = int(payload.get("reference_stretch_id") or 0)
    except Exception:
        reference_stretch_id = 0

    try:
        wastage_percent = Decimal(str(payload.get("wastage_percent", "0") or "0"))
    except Exception:
        wastage_percent = Decimal("0")

    overwrite_existing = bool(payload.get("overwrite_existing"))

    if reference_stretch_id <= 0:
        return JSONResponse({"success": False, "error": "Reference stretch is required."}, status_code=400)

    reference_stretch = db.query(RoadStretch).filter(
        RoadStretch.id == reference_stretch_id,
        RoadStretch.project_id == project_id,
    ).first()
    if not reference_stretch:
        return JSONResponse({"success": False, "error": "Reference stretch not found."}, status_code=404)

    if not reference_stretch.length_m or reference_stretch.length_m <= 0:
        return JSONResponse({"success": False, "error": "Reference stretch length is invalid."}, status_code=400)

    ref_planned = db.query(PlannedMaterial).filter(
        PlannedMaterial.project_id == project_id,
        PlannedMaterial.stretch_id == reference_stretch_id,
    ).all()

    if not ref_planned:
        return JSONResponse({"success": False, "error": "Reference stretch has no materials."}, status_code=400)

    ref_len_km = Decimal(reference_stretch.length_m) / Decimal("1000")
    if ref_len_km <= 0:
        return JSONResponse({"success": False, "error": "Reference stretch length is invalid."}, status_code=400)

    target_stretches = db.query(RoadStretch).filter(
        RoadStretch.project_id == project_id,
        RoadStretch.id != reference_stretch_id,
    ).all()

    created = 0
    updated = 0
    skipped_existing = 0
    skipped_length = 0

    wastage_factor = Decimal("1") + (wastage_percent / Decimal("100"))
    round_step = Decimal("0.01")

    for target in target_stretches:
        if not target.length_m or target.length_m <= 0:
            skipped_length += 1
            continue
        target_len_km = Decimal(target.length_m) / Decimal("1000")
        if target_len_km <= 0:
            skipped_length += 1
            continue

        for ref in ref_planned:
            ref_qty = Decimal(str(ref.planned_quantity or 0))
            per_km_qty = ref_qty / ref_len_km
            base_qty = per_km_qty * target_len_km
            final_qty = (base_qty * wastage_factor).quantize(round_step, rounding=ROUND_HALF_UP)

            existing = db.query(PlannedMaterial).filter(
                PlannedMaterial.project_id == project_id,
                PlannedMaterial.stretch_id == target.id,
                PlannedMaterial.material_id == ref.material_id,
            ).first()

            if existing:
                if not overwrite_existing:
                    skipped_existing += 1
                    continue
                existing.planned_quantity = final_qty
                existing.unit = ref.unit
                existing.allowed_units = ref.allowed_units
                updated += 1
            else:
                db.add(PlannedMaterial(
                    project_id=project_id,
                    material_id=ref.material_id,
                    stretch_id=target.id,
                    unit=ref.unit,
                    allowed_units=ref.allowed_units,
                    planned_quantity=final_qty,
                ))
                created += 1

    db.commit()

    log_action(
        db,
        request,
        action="UPDATE",
        entity_type="planned_material_distribution",
        entity_id=project_id,
        description="Auto-distributed stretch materials",
        new_value={
            "project_id": project_id,
            "reference_stretch_id": reference_stretch_id,
            "wastage_percent": float(wastage_percent),
            "overwrite_existing": overwrite_existing,
            "created": created,
            "updated": updated,
            "skipped_existing": skipped_existing,
            "skipped_length": skipped_length,
        },
    )

    return JSONResponse({
        "success": True,
        "message": "Auto distribution completed.",
        "materials_created": created,
        "materials_updated": updated,
        "materials_skipped": skipped_existing,
        "stretches_skipped": skipped_length,
    })

# Get current vendors linked to a material (with full details)
@router.get("/material/{material_id}/vendors")
def get_material_vendors(material_id: int, project_id: int = None, db: Session = Depends(get_db)):
    # PROJECT-SPECIFIC: Only show vendors that are linked to this project
    if project_id:
        # Get vendor IDs that are linked to this project
        project_vendor_ids = (
            db.query(ProjectMaterialVendor.vendor_id)
            .filter(ProjectMaterialVendor.project_id == project_id)
            .distinct()
            .subquery()
        )
        # Get all vendors linked to this project
        all_vendors = (
            db.query(MaterialVendor)
            .filter(MaterialVendor.id.in_(project_vendor_ids))
            .order_by(MaterialVendor.vendor_name.asc())
            .all()
        )
        # Get vendor IDs already linked to this material in this project
        linked_vendor_ids = [
            pmv.vendor_id for pmv in db.query(ProjectMaterialVendor)
            .filter(
                ProjectMaterialVendor.project_id == project_id,
                ProjectMaterialVendor.material_id == material_id
            )
            .all()
        ]
    else:
        # Fallback: Get all vendors (backward compatibility)
        all_vendors = db.query(MaterialVendor).order_by(MaterialVendor.vendor_name.asc()).all()
        linked_vendor_ids = [vendor.id for vendor in all_vendors if vendor.material_id == material_id]
    
    return {
        "vendor_ids": linked_vendor_ids,
        "vendors": [
            {
                "id": vendor.id,
                "vendor_name": vendor.vendor_name,
                "contact_person": vendor.contact_person,
                "email": vendor.email,
                "lead_time_days": vendor.lead_time_days,
                "min_order_qty": vendor.min_order_qty
            }
            for vendor in all_vendors
        ]
    }

# Update vendors linked to a material (replace all)
@router.post("/material/{material_id}/vendors")
async def set_material_vendors(material_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    vendor_ids = data.get("vendor_ids", [])
    project_id = data.get("project_id")
    
    try:
        # PROJECT-SPECIFIC: Update ProjectMaterialVendor records
        if project_id:
            # Remove existing linkages for this material in this project
            db.query(ProjectMaterialVendor).filter(
                ProjectMaterialVendor.project_id == project_id,
                ProjectMaterialVendor.material_id == material_id
            ).delete()
            
            # Add new linkages
            for vendor_id in vendor_ids:
                # Check if vendor exists
                vendor = db.query(MaterialVendor).filter(MaterialVendor.id == vendor_id).first()
                if vendor:
                    # Create ProjectMaterialVendor record
                    pmv = ProjectMaterialVendor(
                        project_id=project_id,
                        material_id=material_id,
                        vendor_id=vendor_id,
                        lead_time_days=vendor.lead_time_days
                    )
                    db.add(pmv)
        else:
            # Fallback: Use old schema (backward compatibility)
            for vendor_id in vendor_ids:
                vendor = db.query(MaterialVendor).filter(MaterialVendor.id == vendor_id).first()
                if vendor:
                    vendor.material_id = material_id
                    db.add(vendor)
        
        db.commit()
        return JSONResponse({"success": True, "vendor_ids": vendor_ids})
    except Exception as e:
        db.rollback()
        print(f"Error updating vendors: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

# Add new vendor
@router.post("/vendors/add")
async def add_vendor(request: Request, db: Session = Depends(get_db)):
    from datetime import datetime
    
    form = await request.form()
    
    # Basic Information (required)
    vendor_name = form.get("vendor_name")
    vendor_type = form.get("vendor_type")
    vendor_contact = form.get("vendor_contact")
    vendor_email = form.get("vendor_email")
    vendor_location = form.get("vendor_location")
    service_area = form.get("service_area")
    vendor_priority = form.get("vendor_priority", "Primary")
    reliability_rating = form.get("reliability_rating", "Medium")
    
    # Commercial Details
    payment_terms = form.get("payment_terms")
    credit_period = form.get("credit_period")
    gst_number = form.get("gst_number")
    gst_percentage = form.get("gst_percentage")
    
    # Contract Details
    contract_start_date = form.get("contract_start_date")
    contract_end_date = form.get("contract_end_date")
    
    # Materials Supplied (repeatable section)
    materials_supplied = form.getlist("materials_supplied[]")
    unit_prices = form.getlist("unit_prices[]")
    per_unit_quantities = form.getlist("per_unit_quantities[]")
    lead_times = form.getlist("lead_times[]")
    supply_capacities = form.getlist("supply_capacities[]")
    
    return_to = form.get("return_to")
    if return_to and not str(return_to).startswith("/"):
        return_to = None

    if not vendor_name or not vendor_type or not vendor_contact or not vendor_location:
        target = return_to or "/material_vendor"
        connector = "&" if "?" in target else "?"
        return RedirectResponse(f"{target}{connector}error=Missing+required+fields", status_code=303)
    
    if not materials_supplied or not materials_supplied[0]:
        target = return_to or "/material_vendor"
        connector = "&" if "?" in target else "?"
        return RedirectResponse(f"{target}{connector}error=At+least+one+material+must+be+supplied", status_code=303)
    
    # Create ONE vendor entry (not per material)
    try:
        # Get the first non-empty material ID for initial material_id
        first_material_id = None
        for material_id in materials_supplied:
            if material_id:
                first_material_id = int(material_id)
                break
        if not first_material_id:
            target = return_to or "/material_vendor"
            connector = "&" if "?" in target else "?"
            return RedirectResponse(f"{target}{connector}error=Please+select+a+material", status_code=303)
        
        new_vendor = MaterialVendor(
            # Basic Information
            vendor_name=vendor_name,
            vendor_type=vendor_type,
            contact_person=vendor_contact,
            email=vendor_email,
            phone=form.get("phone"),
            vendor_location=vendor_location,
            service_area=service_area,
            vendor_priority=vendor_priority,
            reliability_rating=reliability_rating,
            
            # Commercial Details
            payment_terms=payment_terms,
            credit_period=int(credit_period) if credit_period else None,
            gst_number=gst_number,
            gst_percentage=float(gst_percentage) if gst_percentage else 18.0,
            
            # Material Specific Details (set to first material)
            material_id=first_material_id,
            unit_price=float(unit_prices[0]) if unit_prices and unit_prices[0] else None,
            per_unit_quantity=float(per_unit_quantities[0]) if per_unit_quantities and per_unit_quantities[0] else None,
            lead_time_days=int(lead_times[0]) if lead_times and lead_times[0] else 0,
            min_order_qty=float(supply_capacities[0]) if supply_capacities and supply_capacities[0] else None,
            supply_capacity=float(supply_capacities[0]) if supply_capacities and supply_capacities[0] else None,
            
            # Contract Details
            contract_start_date=datetime.fromisoformat(contract_start_date) if contract_start_date else None,
            contract_end_date=datetime.fromisoformat(contract_end_date) if contract_end_date else None,
            
            is_active=True
        )
        db.add(new_vendor)
        
        db.commit()
        target = return_to or "/material_vendor"
        connector = "&" if "?" in target else "?"
        return RedirectResponse(f"{target}{connector}success=Vendor+added+successfully", status_code=303)
    
    except Exception as e:
        db.rollback()
        target = return_to or "/material_vendor"
        connector = "&" if "?" in target else "?"
        return RedirectResponse(f"{target}{connector}error=Error+adding+vendor:{str(e)}", status_code=303)

# Update vendor
@router.post("/vendors/{vendor_id}/update")
async def update_vendor(vendor_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        form = await request.form()
        print(f"\n=== UPDATE VENDOR {vendor_id} ===")
        print(f"Form data: {dict(form)}")
        
        vendor = db.query(MaterialVendor).filter(MaterialVendor.id == vendor_id).first()
        
        if not vendor:
            print(f"Vendor {vendor_id} not found")
            return JSONResponse({"success": False, "error": "Vendor not found"})
        
        print(f"Found vendor: {vendor.vendor_name}")
        
        # Update vendor fields
        if form.get("vendor_name"):
            vendor.vendor_name = form.get("vendor_name")
            print(f"Updated vendor_name to: {vendor.vendor_name}")
        if form.get("contact_person"):
            vendor.contact_person = form.get("contact_person")
            print(f"Updated contact_person to: {vendor.contact_person}")
        if form.get("email"):
            vendor.email = form.get("email")
            print(f"Updated email to: {vendor.email}")
        if form.get("lead_time_days"):
            try:
                vendor.lead_time_days = int(form.get("lead_time_days"))
                print(f"Updated lead_time_days to: {vendor.lead_time_days}")
            except ValueError as ve:
                print(f"ValueError parsing lead_time_days: {ve}")
                vendor.lead_time_days = 0
        if form.get("min_order_qty"):
            try:
                vendor.min_order_qty = float(form.get("min_order_qty"))
                print(f"Updated min_order_qty to: {vendor.min_order_qty}")
            except ValueError as ve:
                print(f"ValueError parsing min_order_qty: {ve}")
                vendor.min_order_qty = None
        
        db.commit()
        print(f"Vendor {vendor_id} updated successfully")
        print("===")
        return JSONResponse({"success": True, "message": "Vendor updated successfully"})
    except Exception as e:
        db.rollback()
        import traceback
        print(f"\nERROR updating vendor {vendor_id}:")
        traceback.print_exc()
        print("===")
        return JSONResponse({"success": False, "error": str(e)})

# Toggle vendor status
@router.post("/vendors/{vendor_id}/toggle")
async def toggle_vendor_status(vendor_id: int, db: Session = Depends(get_db)):
    vendor = db.query(MaterialVendor).filter(MaterialVendor.id == vendor_id).first()
    
    if not vendor:
        return {"error": "Vendor not found"}
    
    vendor.is_active = not vendor.is_active
    db.commit()
    
    return {"success": True, "is_active": vendor.is_active}


@router.post("/vendors/{vendor_id}/delete")
async def delete_vendor(vendor_id: int, db: Session = Depends(get_db)):
    vendor = db.query(MaterialVendor).filter(MaterialVendor.id == vendor_id).first()
    if not vendor:
        return JSONResponse({"success": False, "error": "Vendor not found"}, status_code=404)

    try:
        db.delete(vendor)
        db.commit()
        return JSONResponse({"success": True})
    except Exception as e:
        db.rollback()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.post("/project/{project_id}/materials/add")
async def add_material(request: Request, project_id: int, db: Session = Depends(get_db)):
    import json
    from decimal import Decimal

    form = await request.form()
    name = (form.get("material_name") or "").strip()
    category = (form.get("material_category") or "").strip()
    custom_category = (form.get("custom_material_category") or "").strip()
    unit = (form.get("unit") or "").strip()
    material_type = (form.get("material_type") or "").strip()

    if category == "Other" and custom_category:
        category = custom_category

    if not name or not unit:
        return RedirectResponse(
            f"/project/{project_id}/materials?error=Missing+required+fields",
            status_code=303,
        )

    allowed_units = [unit] if unit else []
    allowed_units_json = json.dumps(allowed_units)

    existing_material = db.query(Material).filter(Material.name == name).first()
    if existing_material:
        mat = existing_material
        changed = False
        if not getattr(mat, "category", None) and category:
            mat.category = category
            changed = True
        if not getattr(mat, "unit", None) and unit:
            mat.unit = unit
            changed = True
        if not getattr(mat, "standard_unit", None) and unit:
            mat.standard_unit = unit
            changed = True
        if not getattr(mat, "allowed_units", None) and allowed_units:
            mat.allowed_units = allowed_units_json
            changed = True
        if changed:
            db.add(mat)
            db.commit()
            db.refresh(mat)
    else:
        mat = Material(
            name=name,
            category=category,
            unit=unit,
            standard_unit=unit,
            allowed_units=allowed_units_json,
        )
        db.add(mat)
        db.commit()
        db.refresh(mat)

    pm_exists = (
        db.query(PlannedMaterial)
        .filter(
            PlannedMaterial.project_id == project_id,
            PlannedMaterial.material_id == mat.id,
            PlannedMaterial.stretch_id == None,  # noqa: E711
        )
        .first()
    )

    if not pm_exists:
        db.add(
            PlannedMaterial(
                project_id=project_id,
                material_id=mat.id,
                stretch_id=None,
                unit=unit,
                allowed_units=allowed_units_json,
                planned_quantity=Decimal("0"),
            )
        )
        db.commit()
    else:
        changed_pm = False
        if not getattr(pm_exists, "unit", None) and unit:
            pm_exists.unit = unit
            changed_pm = True
        if not getattr(pm_exists, "allowed_units", None) and allowed_units:
            pm_exists.allowed_units = allowed_units_json
            changed_pm = True
        if changed_pm:
            db.add(pm_exists)
            db.commit()

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

    # PROJECT-SPECIFIC: Only show materials that are added to this project
    project_material_ids = (
        db.query(PlannedMaterial.material_id)
        .filter(PlannedMaterial.project_id == project_id)
        .distinct()
        .subquery()
    )
    
    # Eagerly load stretches and activities for each material, but NOT vendors yet
    materials = (
        db.query(Material)
        .filter(
            Material.is_active == True,
            Material.id.in_(project_material_ids)
        )
        .options(
            selectinload(Material.stretches_link).selectinload(MaterialStretch.stretch),
            selectinload(Material.activities_link).selectinload(MaterialActivity.activity)
        )
        .all()
    )
    
    # PROJECT-SPECIFIC: Manually attach only project-specific vendors to each material
    for material in materials:
        # Get vendors linked to this material AND this project
        project_vendors = (
            db.query(MaterialVendor)
            .join(ProjectMaterialVendor, ProjectMaterialVendor.vendor_id == MaterialVendor.id)
            .filter(
                ProjectMaterialVendor.project_id == project_id,
                ProjectMaterialVendor.material_id == material.id
            )
            .all()
        )
        # Override the vendors relationship with project-specific vendors
        material.vendors = project_vendors

    project = db.query(Project).filter(Project.id == project_id).first()
    project_data = get_project_data(project)

    activities = db.query(Activity).filter(Activity.project_id == project_id).all() if project else []
    stretches = db.query(RoadStretch).filter(RoadStretch.project_id == project_id).all() if project else []
    planned_rows = (
        db.query(PlannedMaterial)
        .filter(
            PlannedMaterial.project_id == project_id,
            PlannedMaterial.stretch_id == None,  # noqa: E711
        )
        .options(selectinload(PlannedMaterial.material))
        .all()
    )
    planned_material_rows = [
        {
            "planned_material_id": int(pm.id),
            "material_id": int(pm.material_id),
            "name": str(pm.material.name) if pm.material else "Unknown",
            "unit": str(pm.unit or ""),
        }
        for pm in planned_rows
    ]
    # PROJECT-SPECIFIC: Only show vendors that are linked to this project
    project_vendor_ids = (
        db.query(ProjectMaterialVendor.vendor_id)
        .filter(ProjectMaterialVendor.project_id == project_id)
        .distinct()
        .subquery()
    )
    all_vendors = (
        db.query(MaterialVendor)
        .filter(MaterialVendor.id.in_(project_vendor_ids))
        .all()
    )
    alerts = [] # TODO: Populate with real alert logic

    # Use session user if available, fallback only if not
    user = request.session.get("user") if hasattr(request, "session") and request.session.get("user") else request.scope.get("user") if "user" in request.scope else None
    if user is None:
        user = {"username": "Guest", "role": "admin"}

    # Ensure shared filters are available (safe to call per-request).
    register_template_filters(templates)
    
    # Pass the actual materials objects with vendors already loaded
    return templates.TemplateResponse("material_vendor.html", {
        "request": request,
        "project": project_data,
        "projects": projects,
        "materials": materials,  # Pass actual ORM objects with loaded vendors
        "all_materials": materials,  # For dropdowns
        "planned_material_rows": planned_material_rows,
        "activities": activities,
        "all_activities": activities,
        "stretches": stretches,
        "all_stretches": stretches,
        "all_vendors": all_vendors,  # All vendors for the modal
        "alerts": alerts,
        "user": user
    })

# ...existing code for POST endpoints...
