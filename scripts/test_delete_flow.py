from datetime import date
from types import SimpleNamespace
import os
import sys

# Ensure project root is on sys.path so `import app` works when running this script
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.db.session import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_user import ProjectUser
from app.models.project_alignment import ProjectAlignmentPoint
from app.models.activity import Activity
from app.models.project_activity import ProjectActivity
from app.models.planned_material import PlannedMaterial
from app.models.material import Material
from app.models.material_usage_daily import MaterialUsageDaily
from app.models.material_usage import MaterialUsage
from app.models.material_stock import MaterialStock
from app.models.activity_progress import ActivityProgress
from app.models.daily_entry import DailyEntry

# Avoid importing FastAPI route modules (they require extras at import-time).
projects_routes = None


def create_test_data(db):
    # create admin user (or reuse if exists)
    admin = db.query(User).filter(User.username == "test_admin_delete").first()
    if not admin:
        admin = User(username="test_admin_delete", password_hash="x", role="admin")
        db.add(admin)
        db.commit()
        db.refresh(admin)

    # create material (or reuse if exists)
    mat_name = f"mat_{admin.id}"
    mat = db.query(Material).filter(Material.name == mat_name).first()
    if not mat:
        mat = Material(name=mat_name, unit="MT", lead_time_days=0, minimum_stock=0)
        db.add(mat)
        db.commit()
        db.refresh(mat)

    # create project
    proj = Project(
        name="Test Delete Project",
        road_type="Highway",
        lanes=2,
        road_width=7.5,
        road_length_km=1.2,
        country="TestLand",
        city="TestCity",
        planned_start_date=date.today(),
        planned_end_date=date.today(),
        created_by=admin.id,
        is_active=True,
        status="active",
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)

    # project user
    pu = ProjectUser(project_id=proj.id, user_id=admin.id, role_in_project="owner")
    db.add(pu)

    # alignment point
    ap = ProjectAlignmentPoint(project_id=proj.id, chainage_m=0, northing=0.0, easting=0.0, ogl=0.0, frl=0.0)
    db.add(ap)

    # activity
    act = Activity(name="Test Activity", is_standard=False, project_id=proj.id)
    db.add(act)
    db.commit()
    db.refresh(act)

    # project activity
    pa = ProjectActivity(project_id=proj.id, activity_id=act.id, planned_quantity=10.0, unit="m3", start_date=date.today(), end_date=date.today())
    db.add(pa)

    # planned material
    pm = PlannedMaterial(project_id=proj.id, material_id=mat.id, planned_quantity=100.0)
    db.add(pm)

    # material usage daily
    mud = MaterialUsageDaily(project_id=proj.id, material_id=mat.id, usage_date=date.today(), quantity_used=5.0)
    db.add(mud)

    # material usage
    mu = MaterialUsage(project_id=proj.id, activity_id=act.id, material_id=mat.id, quantity_used=2.5)
    db.add(mu)

    # material stock
    ms = MaterialStock(project_id=proj.id, material_id=mat.id, quantity_available=50.0)
    db.add(ms)

    # activity progress
    apg = ActivityProgress(project_id=proj.id, activity_id=act.id, planned_start=date.today(), planned_end=date.today(), progress_percent=10)
    db.add(apg)

    # daily entry
    de = DailyEntry(project_id=proj.id, activity_id=act.id, quantity_done=1.0, entry_date=date.today())
    db.add(de)

    db.commit()

    return admin, proj


def print_counts(db, project_id):
    def c(q):
        return db.execute(q, {"pid": project_id}).fetchall()[0][0]

    from sqlalchemy import text

    counts = {
        "projects": c(text("SELECT COUNT(1) FROM projects WHERE id = :pid")) ,
        "project_users": c(text("SELECT COUNT(1) FROM project_users WHERE project_id = :pid")),
        "alignment_points": c(text("SELECT COUNT(1) FROM project_alignment_points WHERE project_id = :pid")),
        "activities": c(text("SELECT COUNT(1) FROM activities WHERE project_id = :pid")),
        "project_activities": c(text("SELECT COUNT(1) FROM project_activities WHERE project_id = :pid")),
        "planned_materials": c(text("SELECT COUNT(1) FROM planned_materials WHERE project_id = :pid")),
        "material_usage_daily": c(text("SELECT COUNT(1) FROM material_usage_daily WHERE project_id = :pid")),
        "material_usages": c(text("SELECT COUNT(1) FROM material_usages WHERE project_id = :pid")),
        "material_stocks": c(text("SELECT COUNT(1) FROM material_stocks WHERE project_id = :pid")),
        "activity_progress": c(text("SELECT COUNT(1) FROM activity_progress WHERE project_id = :pid")),
        "daily_entries": c(text("SELECT COUNT(1) FROM daily_entries WHERE project_id = :pid")),
    }

    print("Counts for project_id=", project_id)
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        admin, proj = create_test_data(db)
        print("Created admin id=", admin.id, "project id=", proj.id)
        print("Before delete:")
        print_counts(db, proj.id)

        # Simulate delete logic identical to the route (explicit dependent deletes)
        try:
            # Safe deletion order mirroring route logic
            db.query(MaterialUsage).filter(MaterialUsage.project_id == proj.id).delete(synchronize_session=False)
            db.query(DailyEntry).filter(DailyEntry.project_id == proj.id).delete(synchronize_session=False)
            db.query(ActivityProgress).filter(ActivityProgress.project_id == proj.id).delete(synchronize_session=False)

            db.query(ProjectActivity).filter(ProjectActivity.project_id == proj.id).delete(synchronize_session=False)
            db.query(Activity).filter(Activity.project_id == proj.id).delete(synchronize_session=False)

            db.query(PlannedMaterial).filter(PlannedMaterial.project_id == proj.id).delete(synchronize_session=False)
            db.query(MaterialUsageDaily).filter(MaterialUsageDaily.project_id == proj.id).delete(synchronize_session=False)
            db.query(MaterialStock).filter(MaterialStock.project_id == proj.id).delete(synchronize_session=False)

            db.query(ProjectAlignmentPoint).filter(ProjectAlignmentPoint.project_id == proj.id).delete(synchronize_session=False)
            db.query(ProjectUser).filter(ProjectUser.project_id == proj.id).delete(synchronize_session=False)

            db.delete(proj)
            db.commit()
            print("Simulated delete completed")
        except Exception as e:
            db.rollback()
            print("Simulated delete raised:", repr(e))

        print("After delete:")
        print_counts(db, proj.id)

    finally:
        db.close()
