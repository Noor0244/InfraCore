"""
One-time SSR data ingestion script for BMC ROADS USOR 2023
- Manually parse PDF and insert SSR data
- Preload standard units
- Insert project type, chapters, items
"""
from app.db.session import get_db
from app.models.ssr import SSRProjectType, SSRUnit, SSRChapter, SSRItem
from sqlalchemy.orm import Session

# Preload standard units
SSR_UNITS = [
    {"name": "Meter", "symbol": "MTR", "description": "Linear meter"},
    {"name": "Square Meter", "symbol": "SQM", "description": "Area in square meters"},
    {"name": "Cubic Meter", "symbol": "CUM", "description": "Volume in cubic meters"},
    {"name": "Metric Tonne", "symbol": "MT", "description": "Metric tonne"},
    {"name": "Kilogram", "symbol": "KG", "description": "Kilogram"},
    {"name": "Number", "symbol": "NOS", "description": "Number of items"},
    {"name": "Lump Sum", "symbol": "LS", "description": "Lump sum"},
    {"name": "Litre", "symbol": "LTR", "description": "Litre"},
    {"name": "Square Feet", "symbol": "SFT", "description": "Area in square feet"},
    {"name": "Hour", "symbol": "HR", "description": "Hour"},
]

def ingest_ssr_data():
    db: Session = next(get_db())
    # Insert SSR units
    for u in SSR_UNITS:
        if not db.query(SSRUnit).filter_by(symbol=u["symbol"]).first():
            db.add(SSRUnit(**u))
    db.commit()

    # Insert project type (ROAD)
    road_type = db.query(SSRProjectType).filter_by(code="ROAD").first()
    if not road_type:
        road_type = SSRProjectType(code="ROAD", name="Road", description="Road Projects", is_active=True)
        db.add(road_type)
        db.commit()
    # Insert chapters and items (manually parsed from PDF)
    # Example:
    # chapters = [
    #     {"chapter_code": "RW-1", "chapter_name": "Earth Work", "display_order": 1},
    #     ...
    # ]
    # items = [
    #     {"item_code": "R3-RW-1-01", "item_description": "Excavation for roadway...", "unit_symbol": "CUM", "rate": 123.45, "chapter_code": "RW-1"},
    #     ...
    # ]
    # for ch in chapters:
    #     ...
    # for it in items:
    #     ...
    # See README for detailed instructions.
    print("SSR data ingestion complete. Add chapter/item parsing as needed.")

if __name__ == "__main__":
    ingest_ssr_data()
