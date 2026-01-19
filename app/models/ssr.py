from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from app.db.base import Base

class SSRProjectType(Base):
    __tablename__ = "ssr_project_types"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(String(256))
    is_active = Column(Boolean, default=True)
    chapters = relationship("SSRChapter", back_populates="project_type")
    items = relationship("SSRItem", back_populates="project_type")

class SSRUnit(Base):
    __tablename__ = "ssr_units"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    symbol = Column(String(16), nullable=False, unique=True)
    description = Column(String(128))
    items = relationship("SSRItem", back_populates="unit")

class SSRChapter(Base):
    __tablename__ = "ssr_chapters"
    id = Column(Integer, primary_key=True, index=True)
    project_type_id = Column(Integer, ForeignKey("ssr_project_types.id"), nullable=False)
    chapter_code = Column(String(32), nullable=False)
    chapter_name = Column(String(128), nullable=False)
    display_order = Column(Integer, default=0)
    project_type = relationship("SSRProjectType", back_populates="chapters")
    items = relationship("SSRItem", back_populates="chapter")

class SSRItem(Base):
    __tablename__ = "ssr_items"
    id = Column(Integer, primary_key=True, index=True)
    project_type_id = Column(Integer, ForeignKey("ssr_project_types.id"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("ssr_chapters.id"), nullable=False)
    item_code = Column(String(64), nullable=False)
    item_description = Column(Text, nullable=False)
    unit_id = Column(Integer, ForeignKey("ssr_units.id"), nullable=False)
    rate = Column(Numeric(12, 2), nullable=True)
    is_active = Column(Boolean, default=True)
    project_type = relationship("SSRProjectType", back_populates="items")
    chapter = relationship("SSRChapter", back_populates="items")
    unit = relationship("SSRUnit", back_populates="items")

# Placeholders for future SSR features:
# - SSR → Activity mapping
# - SSR → Material consumption norms
# - SSR → BOQ generation
