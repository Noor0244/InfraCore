from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.project_dashboard_analytics import (
    get_project_dashboard_analytics
)

router = APIRouter(
    prefix="/analytics",
    tags=["Project Dashboard Analytics"]
)


@router.get("/project-dashboard/{project_id}")
def project_dashboard(
    project_id: int,
    time_unit: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Get project-level dashboard KPIs:
    - Activity status summary
    - Overall progress %
    - Material health
    - Risk flags
    """
    try:
        return get_project_dashboard_analytics(
            db=db,
            project_id=project_id,
            time_unit=time_unit,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
