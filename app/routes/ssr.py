from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services import ssr_service
from app.models import ssr

router = APIRouter(prefix="/ssr", tags=["SSR"])

@router.get("/project-types")
def get_project_types(db: Session = Depends(get_db)):
    return ssr_service.get_ssr_project_types(db)

@router.get("/{project_type_id}/chapters")
def get_chapters(project_type_id: int, db: Session = Depends(get_db)):
    return ssr_service.get_ssr_chapters(db, project_type_id)

@router.get("/{project_type_id}/items")
def get_items_by_project_type(project_type_id: int, db: Session = Depends(get_db)):
    return ssr_service.get_ssr_items_by_project_type(db, project_type_id)

@router.get("/chapters/{chapter_id}/items")
def get_items_by_chapter(chapter_id: int, db: Session = Depends(get_db)):
    return ssr_service.get_ssr_items_by_chapter(db, chapter_id)

# All SSR endpoints are read-only. No create/update/delete.
# Placeholders for future SSR features:
# - SSR → Activity mapping
# - SSR → Material consumption norms
# - SSR → BOQ generation
