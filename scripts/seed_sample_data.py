#!/usr/bin/env python
"""
Sample data seeding script for InfraCore
Creates a sample project with 3 users (Admin, Manager, Viewer)
"""
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.material import Material
from app.models.activity import Activity
from app.models.road_stretch import RoadStretch
from app.core.security import hash_password

def seed_database():
    db = SessionLocal()
    
    try:
        # ============================================
        # CREATE 3 USERS
        # ============================================
        print("Creating users...")
        
        # Admin User
        admin_user = User(
            username="admin_user",
            email="admin@infracore.com",
            password_hash=hash_password("admin@123"),
            role="admin",
            is_active=True
        )
        db.add(admin_user)
        
        # Manager User
        manager_user = User(
            username="manager_user",
            email="manager@infracore.com",
            password_hash=hash_password("manager@123"),
            role="manager",
            is_active=True
        )
        db.add(manager_user)
        
        # Viewer User
        viewer_user = User(
            username="viewer_user",
            email="viewer@infracore.com",
            password_hash=hash_password("viewer@123"),
            role="viewer",
            is_active=True
        )
        db.add(viewer_user)
        
        db.commit()
        print("✓ Users created successfully")
        
        # ============================================
        # CREATE SAMPLE PROJECT
        # ============================================
        print("\nCreating sample project...")
        
        today = datetime.now().date()
        start_date = today
        end_date = today + timedelta(days=180)  # 6 months project
        
        project = Project(
            name="NH-48 Four Laning Project - Phase 1",
            project_code="NH48-PH1-2026",
            client_authority="National Highways Authority of India (NHAI)",
            contractor="L&T Infrastructure Engineering Limited",
            consultant_pmc="EY Infrastructure Advisory",
            road_type="National Highway",
            lanes=4,
            road_width=24.5,
            road_length_km=42.5,
            carriageway_width=7.5,
            shoulder_type="Bituminous",
            median_type="Concrete (2.0m)",
            project_type="Road",
            road_name="Mumbai to Pune Highway",
            lane_configuration="4L",
            road_pavement_type="Flexible",
            terrain_type="Rolling",
            status="active",
            is_active=True,
            country="India",
            state="Maharashtra",
            district="Pune",
            city="Pune",
            planned_start_date=start_date,
            planned_end_date=end_date,
            created_by=admin_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(project)
        db.flush()
        print(f"✓ Project created: {project.name} (ID: {project.id})")
        
        # ============================================
        # CREATE SAMPLE MATERIALS
        # ============================================
        print("\nCreating sample materials...")
        
        materials_data = [
            {
                "name": "Cement",
                "category": "Binding Material",
                "unit": "MT",
                "specification": "OPC 53 Grade",
            },
            {
                "name": "Fine Aggregate (Sand)",
                "category": "Aggregate",
                "unit": "M³",
                "specification": "Zone II Sand, FM 2.8-3.0",
            },
            {
                "name": "Coarse Aggregate (20mm)",
                "category": "Aggregate",
                "unit": "M³",
                "specification": "Nominal Size 20mm",
            },
            {
                "name": "Bitumen (Asphalt)",
                "category": "Binding Material",
                "unit": "MT",
                "specification": "VG 30 Grade Bitumen",
            },
            {
                "name": "Steel Reinforcement",
                "category": "Reinforcement",
                "unit": "MT",
                "specification": "Fe 500 Grade, 12mm dia bars",
            },
            {
                "name": "Pre-Cast Concrete Blocks",
                "category": "Precast",
                "unit": "No",
                "specification": "400mm x 200mm x 200mm",
            }
        ]
        
        materials = []
        for mat_data in materials_data:
            material = Material(
                name=mat_data["name"],
                category=mat_data["category"],
                unit=mat_data["unit"],
                specification=mat_data["specification"]
            )
            db.add(material)
            materials.append(material)
        
        db.flush()
        print(f"✓ Created {len(materials)} materials")
        
        # ============================================
        # CREATE SAMPLE ACTIVITIES
        # ============================================
        print("\nCreating sample activities...")
        
        activities_data = [
            "Site Clearance & Preparation",
            "Subgrade Preparation",
            "Base Layer Construction",
            "Concrete Pavement",
            "Asphalt Overlay",
            "Median Construction",
            "Shoulder Construction",
            "Drainage Works",
            "Road Markings",
            "Safety Barriers"
        ]
        
        activities = []
        for act_name in activities_data:
            activity = Activity(
                name=act_name,
                project_id=project.id,
                is_standard=True
            )
            db.add(activity)
            activities.append(activity)
        
        db.flush()
        print(f"✓ Created {len(activities)} activities")
        
        # ============================================
        # CREATE SAMPLE ROAD STRETCHES
        # ============================================
        print("\nCreating sample road stretches...")
        
        stretches_data = [
            {"code": "S-1", "name": "Stretch 1: Km 0+000 to Km 10+500", "start": "0+000", "end": "10+500", "length_m": 10500, "seq": 1},
            {"code": "S-2", "name": "Stretch 2: Km 10+500 to Km 21+000", "start": "10+500", "end": "21+000", "length_m": 10500, "seq": 2},
            {"code": "S-3", "name": "Stretch 3: Km 21+000 to Km 31+500", "start": "21+000", "end": "31+500", "length_m": 10500, "seq": 3},
            {"code": "S-4", "name": "Stretch 4: Km 31+500 to Km 42+500", "start": "31+500", "end": "42+500", "length_m": 11000, "seq": 4},
        ]
        
        stretches = []
        for stretch_data in stretches_data:
            stretch = RoadStretch(
                project_id=project.id,
                stretch_code=stretch_data["code"],
                stretch_name=stretch_data["name"],
                start_chainage=stretch_data["start"],
                end_chainage=stretch_data["end"],
                length_m=stretch_data["length_m"],
                sequence_no=stretch_data["seq"]
            )
            db.add(stretch)
            stretches.append(stretch)
        
        db.flush()
        print(f"✓ Created {len(stretches)} road stretches")
        
        # ============================================
        # COMMIT ALL CHANGES
        # ============================================
        db.commit()
        
        print("\n" + "="*60)
        print("✅ SAMPLE DATA SEEDED SUCCESSFULLY!")
        print("="*60)
        print(f"\n📋 PROJECT DETAILS:")
        print(f"   Name: {project.name}")
        print(f"   Code: {project.project_code}")
        print(f"   Status: {project.status}")
        print(f"   Length: {project.road_length_km} km")
        print(f"   Lanes: {project.lanes} Lane(s)")
        
        print(f"\n👥 USER CREDENTIALS:")
        print(f"   Admin   | Username: admin_user      | Password: admin@123")
        print(f"   Manager | Username: manager_user    | Password: manager@123")
        print(f"   Viewer  | Username: viewer_user     | Password: viewer@123")
        
        print(f"\n📊 CREATED ENTITIES:")
        print(f"   Users: 3")
        print(f"   Projects: 1")
        print(f"   Materials: {len(materials)}")
        print(f"   Activities: {len(activities)}")
        print(f"   Road Stretches: {len(stretches)}")
        print("="*60 + "\n")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
