# app/services/inventory_service.py
# --------------------------------------------------
# Inventory Service Logic
# InfraCore
# --------------------------------------------------

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.models.material_stock import MaterialStock
from app.models.material_usage import MaterialUsage
from app.models.material_usage_daily import MaterialUsageDaily
from app.models.material import Material


# ==================================================
# INVENTORY SUMMARY (READ-ONLY)
# ==================================================
def get_inventory_summary(db: Session, project_id: int):
    """
    Inventory summary per material for a project
    """

    materials = db.query(Material).all()
    result = []

    for material in materials:

        # Available stock
        stock = (
            db.query(MaterialStock.quantity_available)
            .filter(
                MaterialStock.project_id == project_id,
                MaterialStock.material_id == material.id,
                MaterialStock.is_active == True
            )
            .scalar()
        ) or 0

        # Planned requirement
        planned = (
            db.query(func.sum(MaterialUsage.quantity))
            .filter(
                MaterialUsage.project_id == project_id,
                MaterialUsage.material_id == material.id,
                MaterialUsage.is_planned == True
            )
            .scalar()
        ) or 0

        # Used till date (actual)
        used = (
            db.query(func.sum(MaterialUsageDaily.quantity_used))
            .filter(
                MaterialUsageDaily.project_id == project_id,
                MaterialUsageDaily.material_id == material.id
            )
            .scalar()
        ) or 0

        remaining = max(planned - used, 0)

        if stock >= remaining:
            status = "OK"
        elif stock > 0:
            status = "WARNING"
        else:
            status = "CRITICAL"

        result.append({
            "material_id": material.id,
            "material": material.name,
            "unit": material.unit,
            "available_stock": stock,
            "planned_required": planned,
            "used_till_date": used,
            "remaining_required": remaining,
            "status": status
        })

    return result


# ==================================================
# INVENTORY DEDUCTION (WRITE LOGIC)
# ==================================================
def deduct_inventory(
    db: Session,
    project_id: int,
    material_id: int,
    quantity_used: float
):
    """
    Deduct material from inventory when daily usage is recorded
    """

    if quantity_used <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity used must be greater than zero"
        )

    stock = (
        db.query(MaterialStock)
        .filter(
            MaterialStock.project_id == project_id,
            MaterialStock.material_id == material_id,
            MaterialStock.is_active == True
        )
        .first()
    )

    if not stock:
        raise HTTPException(
            status_code=404,
            detail="Material stock not found for this project"
        )

    if stock.quantity_available < quantity_used:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Available: {stock.quantity_available}"
        )

    # Deduct stock
    stock.quantity_available -= quantity_used
    db.add(stock)

    return stock.quantity_available
