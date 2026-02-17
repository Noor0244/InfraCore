# Admin Project Isolation

## Overview
Each admin now has their own isolated dashboard and can only see projects they created. Superadmins continue to see all projects.

## Changes Made

### 1. Database Schema
- **Field**: `projects.created_by` (already exists)
- **Type**: `Integer`, nullable=False
- **Purpose**: Tracks which user created each project

### 2. Project Visibility Rules

| User Role   | Can See Projects                                    |
|-------------|-----------------------------------------------------|
| superadmin  | All projects (no restrictions)                      |
| admin       | Only projects where `created_by = current_user_id`  |
| manager/user/viewer | Projects created by them OR assigned via `project_users` |

### 3. Updated Routes

#### `/projects` (Project List)
- **File**: `app/routes/projects.py`
- **Function**: `projects_page()`
- **Change**: Filters projects by `created_by` for admin role

#### `/dashboard` (Dashboard)
- **File**: `app/routes/dashboard.py`
- **Function**: `dashboard()`
- **Change**: Base query filters by `created_by` for admin role

#### `/execution` (Daily Execution Projects)
- **File**: `app/routes/daily_entry_ui.py`
- **Function**: `execution_projects_page()`
- **Change**: Filters projects by `created_by` for admin role

#### `/stock/current` (Current Stock)
- **File**: `app/routes/material_stock.py`
- **Function**: `current_stock_page()`
- **Change**: Filters available projects by `created_by` for admin role

### 4. Behavior

#### When Admin1 Creates a Project:
- Project is saved with `created_by = Admin1.id`
- Admin1 sees the project in their dashboard and project list
- Admin2 does NOT see this project
- Superadmin DOES see this project

#### When Admin2 Creates a Project:
- Project is saved with `created_by = Admin2.id`
- Admin2 sees the project in their dashboard and project list
- Admin1 does NOT see this project
- Superadmin DOES see this project

### 5. Testing Checklist

- [ ] Create Admin1 user (`role=admin`)
- [ ] Create Admin2 user (`role=admin`)
- [ ] Login as Admin1 and create Project A
- [ ] Login as Admin2 and verify Project A is NOT visible
- [ ] Login as Admin2 and create Project B
- [ ] Login as Admin1 and verify Project B is NOT visible
- [ ] Login as Superadmin and verify both projects are visible
- [ ] Verify dashboards show correct project counts
- [ ] Verify daily execution pages show correct projects
- [ ] Verify material/stock pages filter correctly

### 6. Migration Notes

If you have existing projects without `created_by` set, run:

```sql
-- Set created_by to the first superadmin for orphaned projects
UPDATE projects 
SET created_by = (SELECT id FROM users WHERE role = 'superadmin' LIMIT 1)
WHERE created_by IS NULL OR created_by = 0;
```

Or in Python:

```python
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.user import User

db = SessionLocal()
superadmin = db.query(User).filter(User.role == "superadmin").first()

if superadmin:
    orphaned = db.query(Project).filter(
        (Project.created_by == None) | (Project.created_by == 0)
    ).all()
    
    for project in orphaned:
        project.created_by = superadmin.id
    
    db.commit()
    print(f"Updated {len(orphaned)} orphaned projects")

db.close()
```

### 7. Security Considerations

- **Access Control**: Admins cannot view/edit projects they didn't create
- **API Endpoints**: All project-related endpoints respect the same isolation
- **Superadmin Override**: Superadmins maintain full visibility for system administration
- **Audit Trail**: `created_by` field provides clear ownership tracking

### 8. Future Enhancements

- [ ] Add project transfer feature (superadmin can reassign projects)
- [ ] Add project collaboration (admin can invite other admins to view/edit)
- [ ] Add role-based project templates per admin
- [ ] Add admin usage analytics (projects created, active users per admin)
