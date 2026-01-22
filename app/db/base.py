from sqlalchemy.orm import declarative_base

# Ensure all models are imported for SQLAlchemy relationship resolution
from app.models import *

Base = declarative_base()
