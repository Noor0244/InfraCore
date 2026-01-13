# app/routes/material_daily_usage.py
# --------------------------------------------------
# Daily Material Usage (Service-based Inventory Deduction)
# InfraCore
# --------------------------------------------------

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.material_usage_daily import MaterialUsageDaily
from app.services.inventory_service import deduct_inventory
from app.utils.audit_logger import log_action, model_to_dict

router = APIRouter(
    prefix="/daily-material-usage",
    tags=["Daily Material Usage"]
)

# ---------------- DB DEP ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- ADD DAILY USAGE ----------------
@router.post("/")
def add_daily_usage(
    request: Request,
    project_id: int,
    material_id: int,
    quantity_used: float,
    db: Session = Depends(get_db)
):
    """
    Record daily material usage and auto-deduct inventory
    """

    # 1️⃣ Deduct inventory using service
    remaining_stock = deduct_inventory(
        db=db,
        project_id=project_id,
        material_id=material_id,
        quantity_used=quantity_used
    )

    # 2️⃣ Record daily usage
    usage = MaterialUsageDaily(
        project_id=project_id,
        material_id=material_id,
        quantity_used=quantity_used
    )

    db.add(usage)
    db.commit()
    db.refresh(usage)

    log_action(
        db=db,
        request=request,
        action="CREATE",
        entity_type="MaterialUsageDaily",
        entity_id=usage.id,
        description=f"Material usage recorded: project #{project_id}, material #{material_id}",
        old_value=None,
        new_value={"usage": model_to_dict(usage), "remaining_stock": remaining_stock},
    )

    return {
        "status": "success",
        "message": "Daily material usage recorded & inventory updated",
        "usage_id": usage.id,
        "remaining_stock": remaining_stock
    }


# ---------------- LIST DAILY USAGE ----------------
@router.get("/")
def list_daily_usage(db: Session = Depends(get_db)):
    usages = db.query(MaterialUsageDaily).all()

    return [
        {
            "id": u.id,
            "project_id": u.project_id,
            "material_id": u.material_id,
            "quantity_used": u.quantity_used,
            "date": u.created_at
        }
        for u in usages
    ]
