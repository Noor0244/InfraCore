# app/routes/material_requirements.py
# --------------------------------------------------
# Material Requirement Routes (FINAL)
# InfraCore
# --------------------------------------------------

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.material_calculator import MaterialRequirementCalculator

router = APIRouter(
    prefix="/material-requirements",
    tags=["Material Requirements"]
)

# ---------------- DB DEPENDENCY ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/calculate/{project_id}")
def calculate_material_requirements(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Trigger planned material requirement calculation
    for a given project.
    """
    try:
        calculator = MaterialRequirementCalculator(db)
        result = calculator.calculate_for_project(project_id)

        if not result:
            return {
                "status": "success",
                "message": "No activities found for project",
                "data": {}
            }

        return {
            "status": "success",
            "message": "Material requirement calculated successfully",
            "data": result
        }

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
