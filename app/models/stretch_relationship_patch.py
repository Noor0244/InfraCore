from app.models.stretch import Stretch
from app.models.stretch_activity import StretchActivity
from sqlalchemy.orm import relationship

Stretch.activities = relationship(
    "StretchActivity",
    back_populates="stretch",
    cascade="all, delete-orphan"
)
StretchActivity.stretch = relationship(
    "Stretch",
    back_populates="activities"
)
StretchActivity.stretch_materials = relationship(
    "StretchMaterial",
    back_populates="stretch_activity",
    cascade="all, delete-orphan"
)