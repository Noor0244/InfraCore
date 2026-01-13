from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.material_stock import MaterialStock

router = APIRouter(
    prefix="/material-stock",
    tags=["Material Stock"]
)

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
