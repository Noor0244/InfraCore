from sqlalchemy import Column, Integer, String, Date
from app.db.base import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    report_date = Column(Date, nullable=False)
