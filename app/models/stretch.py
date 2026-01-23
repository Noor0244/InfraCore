from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Stretch(Base):
    __tablename__ = "stretches"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    sequence_no = Column(Integer, nullable=False)
    name = Column(String(255), nullable=True)
    code = Column(String(50), nullable=True)
    length_m = Column(Integer, nullable=False)
    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    manual_override = Column(Boolean, default=False, nullable=False)

    # Relationship will be set after both classes are defined to avoid circular import issues

