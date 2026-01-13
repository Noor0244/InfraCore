from sqlalchemy import (
    Column,
    Integer,
    Float,
    ForeignKey,
    DateTime,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class ProjectAlignmentPoint(Base):
    """
    Stores chainage-wise alignment and level data
    for a project (centerline + FRL + OGL).

    One record = one chainage point.
    """

    __tablename__ = "project_alignment_points"

    id = Column(Integer, primary_key=True, index=True)

    # ---------- PROJECT LINK ----------
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ---------- CHAINAGE ----------
    # Stored in meters from project start
    # Example: 0+250 -> 250
    chainage_m = Column(Integer, nullable=False)

    # ---------- CENTERLINE COORDINATES ----------
    northing = Column(Float, nullable=False)
    easting = Column(Float, nullable=False)

    # ---------- LEVELS ----------
    ogl = Column(Float, nullable=False)  # Original Ground Level
    frl = Column(Float, nullable=False)  # Finished Road Level

    # ---------- META ----------
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # ---------- CONSTRAINTS ----------
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "chainage_m",
            name="uq_project_chainage"
        ),
    )

    # ---------- RELATIONSHIPS ----------
    project = relationship(
        "Project",
        backref="alignment_points"
    )
