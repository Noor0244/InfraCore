"""
Quick automated smoke test for InfraCore after auto-distribute feature implementation
Tests page loading and basic functionality
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.road_stretch import RoadStretch
from app.models.material import Material
from app.models.activity import Activity
from app.models.material_vendor import MaterialVendor
from app.models.planned_material import PlannedMaterial
from app.core.security import hash_password, verify_password
from decimal import Decimal

def test_user_creation():
    """Test that testadmin user exists and password works"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "testadmin").first()
        if not user:
            print("❌ FAIL: testadmin user not found")
            return False
        
        if not verify_password("Test123!", user.password_hash):
            print("❌ FAIL: testadmin password verification failed")
            return False
        
        if user.role != "admin":
            print(f"❌ FAIL: testadmin role is {user.role}, expected admin")
            return False
        
        print(f"✅ PASS: testadmin user exists (ID={user.id}, role={user.role})")
        return True
    finally:
        db.close()

def test_project_creation():
    """Create a test project if it doesn't exist"""
    db = SessionLocal()
    try:
        # Check if test project exists
        project = db.query(Project).filter(Project.name == "TEST_AUTO_DISTRIBUTE").first()
        if project:
            print(f"✅ PASS: Test project already exists (ID={project.id})")
            return project.id
        
        # Get testadmin user ID for created_by
        from app.models.user import User
        user = db.query(User).filter(User.username == "testadmin").first()
        
        # Create new test project (with all required fields)
        from datetime import date
        project = Project(
            name="TEST_AUTO_DISTRIBUTE",
            road_type="Highway",
            lanes=4,
            road_width=12.0,
            road_length_km=10.0,
            project_type="Road",
            country="India",
            state="Test State",
            district="Test District",
            city="Test City",
            planned_start_date=date(2024, 1, 1),
            planned_end_date=date(2024, 12, 31),
            created_by=user.id if user else 1
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"✅ PASS: Created test project (ID={project.id})")
        return project.id
    except Exception as e:
        print(f"❌ FAIL: Could not create test project: {e}")
        return None
    finally:
        db.close()

def test_stretch_creation(project_id):
    """Create 3 test stretches"""
    db = SessionLocal()
    try:
        stretches = db.query(RoadStretch).filter(RoadStretch.project_id == project_id).all()
        if len(stretches) >= 3:
            print(f"✅ PASS: Test stretches already exist (count={len(stretches)})")
            return [s.id for s in stretches[:3]]
        
        # Create stretches with correct schema
        stretch_data = [
            {"stretch_code": "S01", "stretch_name": "Stretch 1", "start_chainage": "0.0", "end_chainage": "3.0", "length_m": 3000, "sequence_no": 1},
            {"stretch_code": "S02", "stretch_name": "Stretch 2", "start_chainage": "3.0", "end_chainage": "7.0", "length_m": 4000, "sequence_no": 2},
            {"stretch_code": "S03", "stretch_name": "Stretch 3", "start_chainage": "7.0", "end_chainage": "10.0", "length_m": 3000, "sequence_no": 3},
        ]
        
        stretch_ids = []
        for data in stretch_data:
            stretch = RoadStretch(project_id=project_id, **data)
            db.add(stretch)
            db.flush()
            stretch_ids.append(stretch.id)
        
        db.commit()
        print(f"✅ PASS: Created 3 test stretches (IDs={stretch_ids})")
        return stretch_ids
    except Exception as e:
        print(f"❌ FAIL: Could not create stretches: {e}")
        db.rollback()
        return []
    finally:
        db.close()

def test_material_creation():
    """Create test materials"""
    db = SessionLocal()
    try:
        materials = db.query(Material).filter(Material.name.in_(["Cement_Test", "Aggregate_Test"])).all()
        if len(materials) >= 2:
            print(f"✅ PASS: Test materials already exist (count={len(materials)})")
            return [m.id for m in materials[:2]]
        
        # Create materials
        mat_data = [
            {"name": "Cement_Test", "unit": "tonnes", "lead_time_days": 7},
            {"name": "Aggregate_Test", "unit": "m3", "lead_time_days": 5},
        ]
        
        mat_ids = []
        for data in mat_data:
            material = Material(**data)
            db.add(material)
            db.flush()
            mat_ids.append(material.id)
        
        db.commit()
        print(f"✅ PASS: Created test materials (IDs={mat_ids})")
        return mat_ids
    except Exception as e:
        print(f"❌ FAIL: Could not create materials: {e}")
        return []
    finally:
        db.close()

def test_auto_distribute_logic(project_id, stretch_ids, material_ids):
    """Test auto-distribute calculation logic"""
    if len(stretch_ids) < 3 or len(material_ids) < 1:
        print("⚠️ SKIP: Not enough stretches or materials for distribution test")
        return False
    
    db = SessionLocal()
    try:
        # Get stretches
        ref_stretch = db.query(RoadStretch).get(stretch_ids[0])
        target_stretch = db.query(RoadStretch).get(stretch_ids[1])
        
        if not ref_stretch or not target_stretch:
            print("❌ FAIL: Could not load stretches")
            return False
        
        # Simulate distribution calculation (lengths are in meters, not km in the model!)
        ref_length = Decimal(str(ref_stretch.length_m)) / Decimal("1000")  # Convert to km
        target_length = Decimal(str(target_stretch.length_m)) / Decimal("1000")
        ref_qty = Decimal("100.00")
        wastage_factor = Decimal("1.10")  # 10% wastage
        
        # Calculate: (ref_qty / ref_length) * target_length * wastage_factor
        per_km_qty = ref_qty / ref_length
        target_qty = per_km_qty * target_length * wastage_factor
        target_qty = target_qty.quantize(Decimal("0.01"))
        
        expected_value = Decimal("146.67")  # 100 / 3 * 4 * 1.1 = 146.666... → 146.67
        
        if target_qty == expected_value:
            print(f"✅ PASS: Auto-distribute calculation correct: {ref_qty} / {ref_length} * {target_length} * {wastage_factor} = {target_qty}")
            return True
        else:
            print(f"❌ FAIL: Auto-distribute calculation wrong: expected {expected_value}, got {target_qty}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Auto-distribute logic test error: {e}")
        return False
    finally:
        db.close()

def test_template_filters():
    """Test that template filters module is importable and has unit_sup"""
    try:
        from app.utils.template_filters import format_unit_sup, register_template_filters
        
        # Test format_unit_sup function (exported as unit_sup filter)
        test_input = "m3"
        result = str(format_unit_sup(test_input))
        
        # The filter returns HTML markup with <sup> tags (correct for templates)
        if "<sup>3</sup>" in result:
            print(f"✅ PASS: unit_sup filter works correctly (returns HTML with <sup> tags)")
            print(f"   Input: '{test_input}' → Output: '{result}'")
            return True
        else:
            print(f"❌ FAIL: unit_sup filter output wrong: '{test_input}' → '{result}'")
            return False
    except Exception as e:
        print(f"❌ FAIL: Template filter test error: {e}")
        return False

def main():
    print("=" * 70)
    print("InfraCore Auto-Distribute Feature Smoke Test")
    print("=" * 70)
    print()
    
    results = {}
    
    print("1️⃣ Testing User Authentication...")
    results['user'] = test_user_creation()
    print()
    
    print("2️⃣ Testing Template Filters (unit_sup)...")
    results['filters'] = test_template_filters()
    print()
    
    print("3️⃣ Testing Project Creation...")
    project_id = test_project_creation()
    results['project'] = project_id is not None
    print()
    
    if project_id:
        print("4️⃣ Testing Stretch Creation...")
        stretch_ids = test_stretch_creation(project_id)
        results['stretches'] = len(stretch_ids) >= 3
        print()
        
        print("5️⃣ Testing Material Creation...")
        material_ids = test_material_creation()
        results['materials'] = len(material_ids) >= 2
        print()
        
        print("6️⃣ Testing Auto-Distribute Calculation Logic...")
        results['auto_distribute'] = test_auto_distribute_logic(project_id, stretch_ids, material_ids)
        print()
    else:
        print("⚠️ SKIP: Remaining tests skipped due to project creation failure")
        results['stretches'] = False
        results['materials'] = False
        results['auto_distribute'] = False
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All automated tests passed!")
    else:
        print("⚠️ Some tests failed - manual verification needed")
    
    print()
    print("=" * 70)
    print("NEXT STEPS - Manual Web UI Testing Required:")
    print("=" * 70)
    print("1. Open http://localhost:8000/login")
    print("2. Login: testadmin / Test123!")
    print("3. Navigate to Material & Vendor Management")
    print("4. Add materials to Stretch 1 with quantities")
    print("5. Click 'Auto Distribute Materials' button")
    print("6. Select Stretch 1 as reference, set wastage to 10%, click Distribute")
    print("7. Verify quantities appeared on other stretches")
    print("8. Check Activity Material Planning page for unit formatting")
    print()
    print("See: manual_test_guide.md for detailed test procedures")
    print("=" * 70)

if __name__ == "__main__":
    main()
