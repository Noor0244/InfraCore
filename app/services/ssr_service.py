"""
SSR Service Layer for InfraCore
"""
from sqlalchemy.orm import Session
from app.models import ssr

def get_ssr_project_types(db: Session):
    return db.query(ssr.SSRProjectType).filter(ssr.SSRProjectType.is_active == True).all()

def get_ssr_chapters(db: Session, project_type_id: int):
    return db.query(ssr.SSRChapter).filter(ssr.SSRChapter.project_type_id == project_type_id).order_by(ssr.SSRChapter.display_order).all()

def get_ssr_items_by_project_type(db: Session, project_type_id: int):
    return db.query(ssr.SSRItem).filter(ssr.SSRItem.project_type_id == project_type_id, ssr.SSRItem.is_active == True).all()

def get_ssr_items_by_chapter(db: Session, chapter_id: int):
    return db.query(ssr.SSRItem).filter(ssr.SSRItem.chapter_id == chapter_id, ssr.SSRItem.is_active == True).all()

# Placeholders for future SSR features:
# - SSR → Activity mapping
# - SSR → Material consumption norms
# - SSR → BOQ generation
