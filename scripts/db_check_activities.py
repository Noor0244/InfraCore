import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import app.db.models  # ensure all model mappings registered
from app.db.session import SessionLocal
from app.models.activity import Activity

db = SessionLocal()
rows = db.query(Activity).filter(Activity.project_id==5).all()
print('Activities for project 5:')
for r in rows:
    print('-', r.name)
from app.models.project import Project
proj = db.query(Project).filter(Project.id==5).first()
print('Project row:', proj and (proj.id, proj.project_type, proj.road_construction_type) or None)

from sqlalchemy import text
rows2 = db.execute(text('SELECT * FROM project_activities WHERE project_id=5')).fetchall()
print('ProjectActivity rows count:', len(rows2))
for r in rows2:
    print('-', dict(r))

db.close()
