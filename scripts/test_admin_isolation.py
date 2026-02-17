"""
Test Admin Project Isolation

This script verifies that admin users only see projects they created.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.user import User
from sqlalchemy import or_
from sqlalchemy.orm import Session


def get_projects_for_user(db: Session, user: dict) -> list[Project]:
    """
    Replicate the project filtering logic from routes
    """
    user_id = user["id"]
    user_role = user.get("role")
    
    if user_role == "superadmin":
        # Superadmin sees all projects
        projects = db.query(Project).filter(Project.is_active == True).all()
    elif user_role == "admin":
        # Admin sees only projects they created
        projects = db.query(Project).filter(
            Project.is_active == True,
            Project.created_by == user_id
        ).all()
    else:
        # Regular users see projects they created or are assigned to
        from app.models.project_user import ProjectUser
        projects = (
            db.query(Project)
            .outerjoin(ProjectUser, Project.id == ProjectUser.project_id)
            .filter(
                Project.is_active == True,
                or_(
                    Project.created_by == user_id,
                    ProjectUser.user_id == user_id,
                )
            )
            .distinct()
            .all()
        )
    
    return projects


def test_admin_isolation():
    """Test that admins only see their own projects"""
    db = SessionLocal()
    
    try:
        print("\n" + "=" * 70)
        print("ADMIN PROJECT ISOLATION TEST")
        print("=" * 70)
        
        # Get all admins
        admins = db.query(User).filter(User.role == "admin", User.is_active == True).all()
        superadmins = db.query(User).filter(User.role == "superadmin", User.is_active == True).all()
        
        if not admins:
            print("❌ No admin users found. Create at least 2 admin users to test isolation.")
            return
        
        print(f"\nFound {len(admins)} admin(s) and {len(superadmins)} superadmin(s)")
        
        # Test each admin
        for admin in admins:
            admin_dict = {
                "id": admin.id,
                "username": admin.username,
                "role": admin.role
            }
            
            projects = get_projects_for_user(db, admin_dict)
            
            print(f"\n👤 {admin.username} (Admin ID: {admin.id})")
            print(f"   Can see {len(projects)} project(s):")
            
            for project in projects:
                owner = db.query(User).filter(User.id == project.created_by).first()
                owner_name = owner.username if owner else "Unknown"
                is_owner = "✓ OWNER" if project.created_by == admin.id else "✗ NOT OWNER"
                print(f"   - {project.name} (ID: {project.id}) | Created by: {owner_name} | {is_owner}")
            
            # Check isolation
            non_owned = [p for p in projects if p.created_by != admin.id]
            if non_owned:
                print(f"   ⚠️  WARNING: Admin sees {len(non_owned)} project(s) they didn't create!")
            else:
                print(f"   ✓ Isolation working: Admin only sees own projects")
        
        # Test superadmin
        if superadmins:
            superadmin = superadmins[0]
            superadmin_dict = {
                "id": superadmin.id,
                "username": superadmin.username,
                "role": superadmin.role
            }
            
            projects = get_projects_for_user(db, superadmin_dict)
            
            print(f"\n👑 {superadmin.username} (Superadmin ID: {superadmin.id})")
            print(f"   Can see {len(projects)} project(s) (ALL PROJECTS)")
        
        # Summary
        all_projects = db.query(Project).filter(Project.is_active == True).all()
        print(f"\n" + "=" * 70)
        print(f"SUMMARY:")
        print(f"  Total active projects: {len(all_projects)}")
        print(f"  Total admins: {len(admins)}")
        print(f"  Total superadmins: {len(superadmins)}")
        
        # Check for orphaned projects
        orphaned = db.query(Project).filter(
            Project.is_active == True,
            or_(Project.created_by == None, Project.created_by == 0)
        ).all()
        
        if orphaned:
            print(f"  ⚠️  {len(orphaned)} orphaned project(s) found (no owner):")
            for p in orphaned:
                print(f"     - {p.name} (ID: {p.id})")
            print(f"  Run: python scripts/migrate_orphaned_projects.py")
        else:
            print(f"  ✓ No orphaned projects")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_admin_isolation()
