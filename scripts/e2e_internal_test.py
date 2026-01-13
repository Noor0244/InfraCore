import sys
from pathlib import Path

# Ensure repository root is on sys.path so `import app.*` works when running scripts
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import SessionLocal
import app.db.models  # ensure all models are registered with SQLAlchemy
from app.models.user import User
from app.models.project import Project
from app.models.activity import Activity
from app.models.material import Material
from app.models.planned_material import PlannedMaterial
from app.models.project_user import ProjectUser
from datetime import date


def run():
    db = SessionLocal()
    try:
        # Ensure admin exists
        admin = db.query(User).filter(User.username == 'admin').first()
        if not admin:
            admin = User(username='admin', password_hash='x', role='admin', is_active=True)
            db.add(admin)
            db.commit()
            db.refresh(admin)
        print('Admin id:', admin.id)

        # Create project with preset Road
        p = Project(
            name='E2E Road Test',
            road_type='Asphalt',
            lanes=2,
            road_width=7.0,
            road_length_km=1.2,
            country='India',
            city='TestCity',
            planned_start_date=date(2025,1,1),
            planned_end_date=date(2025,12,31),
            created_by=admin.id,
            is_active=True,
            status='active',
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        print('Created project id:', p.id)

        # Simulate preset insertion logic (same as route)
        presets = {
            'Road': {
                'activities': ['Earthwork','Subgrade','WMM','Bituminous'],
                'materials':[{'name':'Aggregate','unit':'m3'},{'name':'Bitumen','unit':'MT'},{'name':'Cement','unit':'bags'},{'name':'Sand','unit':'m3'}]
            }
        }
        preset = presets['Road']
        for act_name in preset['activities']:
            exists = db.query(Activity).filter(Activity.project_id==p.id, Activity.name==act_name).first()
            if not exists:
                a = Activity(name=act_name, is_standard=True, project_id=p.id)
                db.add(a)
        db.commit()
        activities = db.query(Activity).filter(Activity.project_id==p.id).all()
        print('Activities created:', [a.name for a in activities])

        for mdef in preset['materials']:
            mat = db.query(Material).filter(Material.name==mdef['name']).first()
            if not mat:
                mat = Material(name=mdef['name'], unit=mdef.get('unit','unit'))
                db.add(mat)
                db.commit()
                db.refresh(mat)
            pm = db.query(PlannedMaterial).filter(PlannedMaterial.project_id==p.id, PlannedMaterial.material_id==mat.id).first()
            if not pm:
                pm = PlannedMaterial(project_id=p.id, material_id=mat.id, planned_quantity=0)
                db.add(pm)
        db.commit()
        pms = db.query(PlannedMaterial).filter(PlannedMaterial.project_id==p.id).all()
        print('Planned materials count:', len(pms))

        # Update project
        p.name = 'E2E Road Test Updated'
        db.commit()
        print('Project updated name:', db.query(Project).get(p.id).name)

        # Archive
        p.is_active = False
        p.status = 'archived'
        db.commit()
        print('Project archived status:', db.query(Project).get(p.id).is_active)

        # Restore
        p.is_active = True
        p.status = 'active'
        db.commit()
        print('Project restored status:', db.query(Project).get(p.id).is_active)

        # Complete
        p.completed_at = None
        p.status = 'completed'
        db.commit()
        print('Project status after complete:', db.query(Project).get(p.id).status)

        # Safe delete sequence: alignment -> project_user -> materials/planned -> activities -> project
        # (alignment table not used in this test)
        # Create a project_user entry to test deletion
        pu = ProjectUser(project_id=p.id, user_id=admin.id, role_in_project='owner')
        db.add(pu)
        db.commit()
        print('ProjectUser created')

        # Now delete per order
        from app.models.project_alignment import ProjectAlignmentPoint
        db.query(ProjectAlignmentPoint).filter(ProjectAlignmentPoint.project_id==p.id).delete(synchronize_session=False)
        db.query(ProjectUser).filter(ProjectUser.project_id==p.id).delete(synchronize_session=False)
        db.query(PlannedMaterial).filter(PlannedMaterial.project_id==p.id).delete(synchronize_session=False)
        db.query(Activity).filter(Activity.project_id==p.id).delete(synchronize_session=False)
        db.delete(p)
        db.commit()

        print('Project and dependents deleted successfully')

    finally:
        db.close()

if __name__ == '__main__':
    run()
