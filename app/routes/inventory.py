# app/routes/inventory.py
# --------------------------------------------------
# Inventory Routes
# InfraCore
# --------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.inventory_service import get_inventory_summary

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/summary/{project_id}")
def inventory_summary(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Inventory summary for a project
    """
    return {
        "project_id": project_id,
        "inventory": get_inventory_summary(db, project_id)
    }
