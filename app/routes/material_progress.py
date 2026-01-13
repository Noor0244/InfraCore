from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.material_progress_analytics import (
    get_material_progress_analytics
)

router = APIRouter(
    prefix="/analytics",
    tags=["Material Progress Analytics"]
)


@router.get("/material-progress/{project_id}/{activity_id}")
def material_progress_analytics(
    project_id: int,
    activity_id: int,
    db: Session = Depends(get_db)
):
    """
    Get planned vs actual material usage based on activity progress %
    """
    try:
        return get_material_progress_analytics(
            db=db,
            project_id=project_id,
            activity_id=activity_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
