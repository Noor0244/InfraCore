# Manual Test Guide - InfraCore

## Test Admin Credentials
- **Username:** `testadmin`
- **Password:** `Test123!`

## Server Status
✅ Running on http://localhost:8000

---

## Test Sequence

### 1. Login and Create Test Project
1. Navigate to http://localhost:8000/login
2. Login with testadmin credentials
3. Go to Projects page
4. Create new project:
   - Name: `TEST_AUTO_DISTRIBUTE`
   - Location: `Test Highway`
   - Total Length: `10 km`
   - Start Date: `2024-01-01`
   - End Date: `2024-12-31`

### 2. Create Road Stretches (3 stretches)
Navigate to Road Stretches page and create:
- **Stretch 1:** KM 0-3, Length: 3.0 km
- **Stretch 2:** KM 3-7, Length: 4.0 km
- **Stretch 3:** KM 7-10, Length: 3.0 km

### 3. Create Materials (3 materials)
Navigate to Material Master page and create:
- **Cement:** Unit: `tonnes`, Lead Time: 7 days
- **Aggregate:** Unit: `m3`, Lead Time: 5 days
- **Bitumen:** Unit: `litres`, Lead Time: 10 days

### 4. Create Activities (2 activities)
Navigate to Activities page and create:
- **Base Layer:** Description: "Sub-base preparation"
- **Surface Course:** Description: "Bituminous surface"

---

## Critical Tests

### ✅ TEST A: Unit Superscript Rendering (unit_sup filter)
**What to check:**
1. Dashboard page - check if unit displays show superscripts correctly (m³, m²)
2. Material Master page - check unit column formatting
3. Material Vendor page - check if units display correctly

**Expected:** All units should show Unicode superscripts (m³ not m3, m² not m2)
**Fixed:** Added `register_template_filters()` to all routes

---

### ✅ TEST B: Material Linker - Dropdown Unit Formatting
**What to check:**
1. Go to Activity Material Planning / Material Linker page
2. Select an activity from dropdown
3. Click "Associate a Material"
4. Check if the unit dropdown shows formatted units (m³, tonnes, etc.)

**Expected:** Units in JS-rendered dropdowns show Unicode superscripts
**Fixed:** Added `formatUnitDisplayText()` JS function

---

### 🆕 TEST C: Auto Material Distribution Across Stretches
**Location:** Material & Vendor Management page

**Setup:**
1. Link Cement to Stretch 1 with vendor and set quantity = `100 tonnes`
2. Link Aggregate to Stretch 1 with vendor and set quantity = `50 m3`

**Test Steps:**
1. Click "Auto Distribute Materials" button (top right of page)
2. In modal, select "Stretch 1" as reference stretch
3. Set wastage percentage to `10%` (1.1x multiplier)
4. Check "Overwrite existing quantities" if needed
5. Click "Distribute"

**Expected Behavior:**
- **Stretch 2 (4 km):**
  - Cement: `100 / 3.0 * 4.0 * 1.1 = 146.67 tonnes`
  - Aggregate: `50 / 3.0 * 4.0 * 1.1 = 73.33 m3`
  
- **Stretch 3 (3 km):**
  - Cement: `100 / 3.0 * 3.0 * 1.1 = 110.00 tonnes`
  - Aggregate: `50 / 3.0 * 3.0 * 1.1 = 55.00 m3`

**Validation:**
- Check Material & Vendor page shows scaled quantities
- Check audit log (if visible) for distribution action
- Verify per-kilometer scaling is correct
- Verify wastage multiplier applied
- Verify rounded to 2 decimals

---

### TEST D: Activity Material Planning
**What to check:**
1. Go to Activity Material Planning page
2. Link materials to activities:
   - Base Layer → Cement (quantity: 50 tonnes)
   - Base Layer → Aggregate (quantity: 30 m3)
   - Surface Course → Bitumen (quantity: 20 litres)
3. Check if quantities save correctly
4. Check if unit formatting displays correctly

**Expected:** Units show superscripts, quantities persist

---

### TEST E: Daily Entry
**What to check:**
1. Go to Daily Entry page
2. Select Stretch 1, select a date
3. Record material usage:
   - Cement: 5 tonnes
   - Aggregate: 3 m3
4. Save entry

**Expected:** Entry saves without errors, quantities recorded

---

### TEST F: Inventory/Stock
**What to check:**
1. Go to Inventory page
2. Check if procured quantities (from Material & Vendor) show
3. Check if consumed quantities (from Daily Entry) show
4. Check if balance calculation is correct

**Expected:** Balance = Procured - Consumed

---

## Summary Checklist

After testing all flows, report:

✅ **WORKING:**
- [ ] Login with testadmin user
- [ ] Project creation
- [ ] Stretch creation
- [ ] Material creation
- [ ] Activity creation
- [ ] Unit superscript rendering (server-side)
- [ ] Unit dropdown formatting (client-side JS)
- [ ] Auto-distribution modal opens
- [ ] Auto-distribution calculation correct
- [ ] Auto-distribution saves to database
- [ ] Activity-material linking
- [ ] Daily entry submission
- [ ] Inventory calculations

❌ **NOT WORKING:**
- List any errors with:
  - Page name
  - Action attempted
  - Error message
  - Browser console errors (F12 → Console)

---

## Known Warnings (Non-Critical)
- Pydantic V2 warning: `'orm_mode' renamed to 'from_attributes'` - does not affect functionality

