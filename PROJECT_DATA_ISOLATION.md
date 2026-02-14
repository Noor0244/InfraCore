# Project Data Isolation - Implementation Summary

**Date:** February 14, 2026  
**Feature:** Project-Specific Data Isolation

---

## ✅ Changes Implemented

### Overview
All materials, vendors, and users are now **project-specific**. Data added to one project will not appear in other projects.

---

## 🔒 Data Isolation by Type

### 1. **Materials** ✅ IMPLEMENTED
**Previous Behavior:** Materials were global - all materials appeared in all projects  
**New Behavior:** Materials only appear in the project where they've been added

**How it works:**
- Materials are filtered through the `planned_materials` table
- Only materials that have been explicitly added to a project (via Material & Vendor Management or Activity Material Planning) will appear in that project
- Other projects will not see these materials

**Affected Pages:**
- ✅ Material & Vendor Management page
- ✅ Material Linker page
- ✅ Add Vendor page  
- ✅ Procurement page
- ✅ Material Stock page
- ✅ Dashboard (inventory predictions)

---

### 2. **Vendors** ✅ IMPLEMENTED
**Previous Behavior:** Vendors were global - all vendors appeared in all projects  
**New Behavior:** Vendors only appear in the project where they've been linked

**How it works:**
- Vendors are filtered through the `project_material_vendors` table
- Only vendors that have been linked to a project's materials will appear in that project
- Other projects will not see these vendors

**Affected Pages:**
- ✅ Material & Vendor Management page
- ✅ Procurement page

---

### 3. **Users** ✅ ALREADY IMPLEMENTED
**Behavior:** Users can only access projects they've been assigned to

**How it works:**
- User access is controlled through the `project_users` table
- Admin/Superadmin users can see all projects
- Regular users only see projects where they've been explicitly assigned
- Project creators automatically have access to their projects

**This was already working** - no changes needed

---

## 📋 Technical Implementation

### Database Tables Used
1. **`planned_materials`** - Links materials to projects
   - `project_id` + `material_id`
   - Created when materials are added via Material & Vendor Management

2. **`project_material_vendors`** - Links vendors to projects
   - `project_id` + `material_id` + `vendor_id`
   - Created when vendors are assigned to materials in a project

3. **`project_users`** - Links users to projects
   - `project_id` + `user_id` + `role_in_project`
   - Created when users are assigned to projects

### Query Pattern
All queries now use subqueries to filter by project:

```python
# Materials filtering example
project_material_ids = (
    db.query(PlannedMaterial.material_id)
    .filter(PlannedMaterial.project_id == project_id)
    .distinct()
    .subquery()
)
materials = (
    db.query(Material)
    .filter(Material.id.in_(project_material_ids))
    .all()
)

# Vendors filtering example
project_vendor_ids = (
    db.query(ProjectMaterialVendor.vendor_id)
    .filter(ProjectMaterialVendor.project_id == project_id)
    .distinct()
    .subquery()
)
vendors = (
    db.query(MaterialVendor)
    .filter(MaterialVendor.id.in_(project_vendor_ids))
    .all()
)
```

---

## 📂 Files Modified

1. **app/routes/material_vendor.py** (3 changes)
   - `material_linker_page()` - Filter materials to project-specific
   - `material_vendor_page()` - Filter materials and vendors to project-specific
   - `add_vendor_page()` - Filter materials to project-specific

2. **app/routes/procurement.py** (1 change)
   - `procurement_page()` - Filter materials and vendors to project-specific

3. **app/routes/material_stock.py** (1 change)
   - `current_stock_page()` - Filter materials to project-specific

4. **app/routes/dashboard.py** (1 change)
   - Dashboard inventory predictions - Filter materials to project-specific

---

## 🧪 Testing Scenarios

### Scenario 1: Create Materials in Project A
1. Go to Project A → Material & Vendor Management
2. Add material "Cement" with vendor "ABC Suppliers"
3. **Expected:** Cement and ABC Suppliers appear in Project A only

### Scenario 2: Check Project B
1. Go to Project B → Material & Vendor Management
2. **Expected:** Cement and ABC Suppliers DO NOT appear
3. Project B has its own empty material/vendor list

### Scenario 3: User Access
1. Create user "John" and assign to Project A only
2. Login as John
3. **Expected:** John only sees Project A in the project list
4. John cannot access Project B data

---

## ⚠️ Important Notes

### For Existing Projects
If you have existing projects that were created before this update:
- Materials that were added globally may not show up immediately
- You may need to re-add materials through the "Material & Vendor Management" page
- This ensures they're properly linked to the project via `planned_materials` table

### For New Projects
- Start fresh - add materials specific to each project
- Materials won't bleed across projects
- Each project has its own isolated material/vendor workspace

---

## 🔄 Workflow

### Adding Materials to a Project
1. Navigate to **Material & Vendor Management** page for your project
2. Click **"Add Material"** or use **"+ Link Material & Vendor"**
3. Fill in material details (name, unit, quantity, vendor)
4. Save - material is now linked to this project only

### Sharing Materials Across Projects (If Needed)
If you need the same material (e.g., "Cement") in multiple projects:
1. Go to each project separately
2. Add the material with the same name in each project
3. Each project will have its own procurement/stock tracking

---

## 📊 Database Schema

### PlannedMaterial Table
```
id | project_id | material_id | stretch_id | unit | quantity | vendor_id
```

### ProjectMaterialVendor Table
```
id | project_id | material_id | vendor_id | lead_time_days
```

### ProjectUser Table
```
id | project_id | user_id | role_in_project
```

---

## ✅ Verification Checklist

- [x] Materials isolated per project
- [x] Vendors isolated per project  
- [x] Users isolated per project (already working)
- [x] Dashboard shows project-specific materials
- [x] Procurement shows project-specific materials/vendors
- [x] Material stock shows project-specific materials
- [x] Material linker shows project-specific materials

---

## 🎯 Result

**Full project data isolation achieved!**  
Each project now has its own isolated workspace for:
- ✅ Materials
- ✅ Vendors
- ✅ Users
- ✅ Activities (already project-scoped)
- ✅ Stretches (already project-scoped)
- ✅ Daily entries (already project-scoped)
- ✅ Procurement logs (already project-scoped)

