"""
Fix existing projects without created_by

This script assigns orphaned projects (created_by = NULL or 0) to the first superadmin.
Run this once after implementing admin project isolation.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.user import User


def migrate_orphaned_projects():
    """Assign orphaned projects to first superadmin"""
    db = SessionLocal()
    
    try:
        # Find first superadmin
        superadmin = db.query(User).filter(User.role == "superadmin").first()
        
        if not superadmin:
            print("❌ No superadmin found. Create a superadmin user first.")
            return
        
        print(f"✓ Found superadmin: {superadmin.username} (ID: {superadmin.id})")
        
        # Find orphaned projects
        orphaned = db.query(Project).filter(
            (Project.created_by == None) | (Project.created_by == 0)
        ).all()
        
        if not orphaned:
            print("✓ No orphaned projects found. All projects have owners.")
            return
        
        print(f"Found {len(orphaned)} orphaned projects:")
        for project in orphaned:
            print(f"  - {project.name} (ID: {project.id})")
        
        # Assign to superadmin
        for project in orphaned:
            project.created_by = superadmin.id
        
        db.commit()
        print(f"✓ Assigned {len(orphaned)} projects to {superadmin.username}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Admin Project Isolation - Orphaned Projects Migration")
    print("=" * 60)
    migrate_orphaned_projects()
    print("=" * 60)
    print("✓ Migration complete")
