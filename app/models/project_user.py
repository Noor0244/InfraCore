from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class ProjectUser(Base):
    __tablename__ = "project_users"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Role INSIDE the project (different from system role)
    role_in_project = Column(String(50), default="member", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", backref="project_users")
    user = relationship("User", backref="project_users")

    # Add a unique constraint to prevent duplicate user-project pairs
    __table_args__ = (
        {
            'sqlite_autoincrement': True,
        },
    )

    # Optionally, add a __repr__ for better debugging
    def __repr__(self):
        return f"<ProjectUser id={self.id} project_id={self.project_id} user_id={self.user_id} role_in_project='{self.role_in_project}'>"
