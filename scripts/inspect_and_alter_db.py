import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.db.session import engine
from sqlalchemy import text

with engine.connect() as conn:
    cols = conn.execute(text("PRAGMA table_info('projects')")).fetchall()
    print('projects columns:')
    for c in cols:
        print(c)
    try:
        conn.execute(text("ALTER TABLE projects ADD COLUMN project_type VARCHAR(50) DEFAULT ''"))
        print('added project_type')
    except Exception as e:
        print('add project_type failed:', e)
    try:
        conn.execute(text("ALTER TABLE projects ADD COLUMN road_construction_type VARCHAR(100)"))
        print('added road_construction_type')
    except Exception as e:
        print('add road_construction_type failed:', e)
    cols = conn.execute(text("PRAGMA table_info('projects')")).fetchall()
    print('after, projects columns:')
    for c in cols:
        print(c)
