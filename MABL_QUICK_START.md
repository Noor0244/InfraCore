# 🧪 Mabl Test Cases - Quick Start Implementation

## How to Create Tests in Mabl - 3 Methods

### Method 1: Visual Recording (EASIEST - Recommended for Beginners)

**Steps:**
1. Login to Mabl dashboard
2. Click **Create → Journey**
3. Enter test name: `Login-Valid`
4. Enter URL: `http://localhost:8000/login`
5. Click **Record**
6. Mabl opens browser and starts recording
7. Perform actions naturally (click, type, submit)
8. Click **Stop** when done
9. Review steps and add assertions
10. Click **Save**

**Pros**: Visual, easy, requires no coding
**Cons**: Manual for each action
**Time**: ~15 minutes per test

---

### Method 2: Step-by-Step Builder (GOOD - For Fine Control)

**Steps:**
1. Create journey (same as above)
2. Click **Edit** instead of Record
3. Click **+ Add Step**
4. Select step type:
   - Navigate
   - Click
   - Type
   - Select
   - Wait
   - Assert
5. Fill in details
6. Configure each step
7. Save

**Pros**: Precise control, repeatable, no data variation
**Cons**: More manual work
**Time**: ~20 minutes per test

---

### Method 3: API Integration (ADVANCED - For CI/CD)

**Create via API:**
```bash
curl -X POST https://api.mabl.com/public/v1/journeys \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Login-Valid",
    "app_guid": "YOUR_APP_GUID",
    "steps": [
      {
        "action_type": "navigate",
        "url": "http://localhost:8000/login"
      },
      {
        "action_type": "click",
        "selector": "input#username"
      }
    ]
  }'
```

**Pros**: Automated, scriptable, integrates with CI/CD
**Cons**: Requires API knowledge, more complex
**Time**: ~30 minutes setup, then fast

---

## 🎯 Top 10 Tests to Create First (Priority Order)

### 1. Login - Valid Credentials ⭐⭐⭐

**Objective**: Verify user can login with valid credentials

**Visual Recording Steps:**
```
1. Navigate to http://localhost:8000/login
2. Click input field labeled "Username"
3. Type "admin"
4. Click input field labeled "Password"  
5. Type "admin123"
6. Click "Login" button
7. Wait for page load
8. Verify success
```

**Assertions to Add:**
```
✓ Page title contains "InfraCore"
✓ Text "Projects" visible
✓ Text "admin" visible in sidebar or greeting
✓ URL changed to /projects or /dashboard
```

**Test Data:**
- Username: `admin`
- Password: `admin123`
- Expected: Login successful

**Time to Record:** 5 minutes

---

### 2. Projects List View ⭐⭐⭐

**Objective**: Verify projects page displays correctly

**Recording Steps:**
```
1. (Assuming logged in) Navigate to http://localhost:8000/projects
2. Wait for table to load
3. Verify page displays
```

**Assertions:**
```
✓ Table header visible with columns: Name, Status, Actions
✓ At least one project row visible
✓ "Create New Project" button visible
✓ Action buttons (Edit, Delete) visible for each project
```

**Time to Record:** 3 minutes

---

### 3. Create Project ⭐⭐⭐

**Objective**: Verify user can create new project

**Recording Steps:**
```
1. Navigate to /projects
2. Click "Create New Project" button or "+" icon
3. Wait for form
4. Click "Project Name" field
5. Type "Test Project [Date]"      # Use variable: {{today}}
6. Click "Description" field
7. Type "Test project description"
8. Click "Budget" field
9. Type "100000"
10. Click "Create" button
11. Wait for success message
12. Verify project in list
```

**Assertions:**
```
✓ Success message appears: "Project created successfully"
✓ Page redirects to projects list
✓ New project visible in table
✓ Project status shows "Active"
```

**Variables to Use:**
```
{{project_name}} = "Test Project {{date}}"
{{budget}} = "100000"
{{location}} = "Test Location"
```

**Time to Record:** 8 minutes

---

### 4. Edit Project ⭐⭐

**Objective**: Verify user can edit project

**Recording Steps:**
```
1. Navigate to /projects
2. Find project row with name "Test Project"
3. Click "Edit" button
4. Wait for edit form
5. Click "Project Name" field
6. Clear existing text
7. Type "Updated Project Name"
8. Click "Save" button
9. Wait for success
```

**Assertions:**
```
✓ Success message shows
✓ Project name updated in list
✓ Other fields preserved
```

**Time to Record:** 6 minutes

---

### 5. Delete Project ⭐⭐

**Objective**: Verify user can delete project with confirmation

**Recording Steps:**
```
1. Navigate to /projects
2. Click "Delete" button for test project
3. Wait for confirmation dialog
4. Click "Confirm Delete" or "Yes" button
5. Wait for success
```

**Assertions:**
```
✓ Confirmation dialog appears
✓ Project removed from list after confirmation
✓ Success message shown
```

**Time to Record:** 5 minutes

---

### 6. Archive Project ⭐⭐

**Objective**: Verify user can archive active project

**Recording Steps:**
```
1. Navigate to /projects (Active view)
2. Click "Archive" button for a project
3. Wait for confirmation or refresh
4. Verify project removed from active list
5. Click "Archived" toggle/button
6. Verify project in archived list
```

**Assertions:**
```
✓ Project no longer in Active list
✓ Project appears in Archived list
✓ Status changed to "Archived"
```

**Time to Record:** 6 minutes

---

### 7. Dark Mode Toggle ⭐⭐

**Objective**: Verify dark mode switches and persists

**Recording Steps:**
```
1. Navigate to /projects
2. Look for dark mode toggle (sun/moon icon)
3. Click toggle to enable dark mode
4. Wait for colors to change
5. Observe background color change
6. Refresh page (Ctrl+R or F5)
7. Verify dark mode still active
```

**Assertions:**
```
✓ Toggle button found
✓ Colors change from light to dark
✓ After refresh, dark mode persists
✓ Text readable on dark background
```

**Visual Assertions:**
```
✓ Background color = dark (#0f172a)
✓ Text color = light (#e5e7eb)
```

**Time to Record:** 7 minutes

---

### 8. Mobile View - Phone (375px) ⭐⭐⭐

**Objective**: Verify responsive design on mobile

**Setup:**
1. In Mabl, before recording, click **Device Settings**
2. Select **iPhone 12** (375px width)
3. Record interaction

**Recording Steps:**
```
1. Navigate to /projects on mobile
2. Verify page displays fully (no horizontal scroll)
3. Verify buttons are tappable (large enough)
4. Click menu/hamburger button if visible
5. Navigate through sidebar
6. Click a project
7. Verify detail view in mobile format
```

**Assertions:**
```
✓ No horizontal scrollbar
✓ All content fits on screen width
✓ Text readable at 375px width
✓ Buttons appear large (44px+)
✓ Tables show as cards (not traditional table)
✓ Sidebar accessible via menu button
```

**Time to Record:** 10 minutes

---

### 9. Tablet View - iPad (768px) ⭐⭐

**Setup:**
1. Click **Device Settings** → **iPad** (768px)

**Recording Steps:**
```
1. Navigate to /projects
2. Verify 2-column form layout if on form
3. Verify tables show normal format
4. Verify sidebar visible
5. Test form submission
```

**Assertions:**
```
✓ Forms display in 2 columns
✓ Tables show headers and data normally
✓ Sidebar visible without toggle needed
✓ Touch targets large (48px+)
```

**Time to Record:** 7 minutes

---

### 10. Form Validation ⭐⭐

**Objective**: Verify form validation works

**Recording Steps:**
```
1. Navigate to Create Project form
2. Leave required fields empty
3. Click Create button
4. Verify error messages appear
5. Fill some fields
6. Click Create again
7. Verify errors updated/removed
8. Fill all required fields
9. Click Create
10. Verify form submits successfully
```

**Assertions:**
```
✓ Error messages shown for empty required fields
✓ Error messages disappear when fields filled
✓ Form cannot submit with validation errors
✓ Form submits when all fields valid
✓ Success message appears after submit
```

**Time to Record:** 10 minutes

---

## Test by Test - Expected Recording Time

| # | Test Name | Setup | Record | Assert | Total |
|---|-----------|-------|--------|--------|-------|
| 1 | Login | 2 min | 3 min | 2 min | 7 min |
| 2 | View Projects | 1 min | 2 min | 2 min | 5 min |
| 3 | Create Project | 2 min | 5 min | 3 min | 10 min |
| 4 | Edit Project | 2 min | 4 min | 2 min | 8 min |
| 5 | Delete Project | 2 min | 3 min | 2 min | 7 min |
| 6 | Archive Project | 2 min | 4 min | 2 min | 8 min |
| 7 | Dark Mode | 2 min | 5 min | 3 min | 10 min |
| 8 | Mobile Phone | 3 min | 6 min | 3 min | 12 min |
| 9 | Tablet | 3 min | 5 min | 2 min | 10 min |
| 10 | Form Validation | 2 min | 6 min | 3 min | 11 min |
| | **TOTAL** | | | | **88 min** |

**Total time to create 10 tests: ~1.5 hours**

---

## Step-by-Step: Create Your First Test (Login)

### Minute 1-2: Setup
1. Go to `https://app.mabl.com`
2. Click **+ Create → Journey**
3. Fill in:
   - Name: `TC-001 Login Valid`
   - Description: `Verify user can login with valid credentials`
4. Click **Next**

### Minute 3-5: Record
1. Click **Start Recording**
2. Browser opens with your app at login page
3. **Do these actions naturally:**
   ```
   Click username input → Type "admin" → 
   Click password input → Type "admin123" → 
   Click Login button
   ```
4. Wait for page to load
5. Click **Stop Recording**

### Minute 6-7: Add Assertions
Mabl should show recorded steps. Now add verifications:

1. After the login button click step, click **+ Add Assertion**
2. Select **Text Assertion**
3. Click the page (or sidebar)
4. Click on "admin" or "Projects" text
5. Choose "contains text" = "admin"
6. Add another assertion:
   - Select **URL Assertion**
   - URL contains: `/projects`

### Minute 8: Save & Run
1. Click **Save**
2. Click **Run**
3. Watch your first test execute!
4. Review results

**Congratulations! You've created your first Mabl test.** 🎉

---

## Creating a Test Plan (Group Tests)

### Create a Testing Plan:
1. Click **Create → Plan**
2. Name: `Smoke Tests - Core Features`
3. Add journeys:
   - Click **+ Add Journey**
   - Select `TC-001 Login Valid`
   - Select `TC-002 View Projects`
   - Select `TC-003 Create Project`
4. Configure:
   - Environment: Development
   - Browsers: Chrome, Firefox
   - Devices: Desktop
5. Click **Create Plan**

### Run the Plan:
1. Click **Run**
2. Watch all tests execute sequentially
3. Get summary report:
   - Total: 3 tests
   - Passed: 3 ✅
   - Failed: 0
   - Success Rate: 100%

---

## Organizing Tests by Category

### Test Organization Structure:

```
📁 InfraCore Tests
├── 🔐 Authentication (4 tests)
│   ├── TC-001 Login Valid
│   ├── TC-002 Login Invalid
│   ├── TC-003 Empty Fields
│   └── TC-004 Logout
│
├── 📋 Project Management (4 tests)
│   ├── TC-010 View Projects
│   ├── TC-011 Create Project
│   ├── TC-012 Edit Project
│   ├── TC-013 Delete Project
│   └── TC-014 Archive Project
│
├── 📱 Responsive Design (3 tests)
│   ├── TC-020 Mobile Phone
│   ├── TC-021 Tablet
│   └── TC-022 Desktop
│
├── 🎨 Theme & UI (2 tests)
│   ├── TC-030 Dark Mode
│   └── TC-031 Light Mode
│
└── ✔️ Forms & Validation (2 tests)
    ├── TC-040 Form Validation
    └── TC-041 Data Entry
```

### Create Plans for Each Category:
- **Plan: Authentication Tests** → Run tests TC-001 to TC-004
- **Plan: Project Tests** → Run tests TC-010 to TC-015
- **Plan: Responsive Tests** → Run tests TC-020 to TC-022
- **Plan: All Tests** → Run all journeys (full suite)

---

## Using Test Variables

### Create Variables:
1. In Mabl, go to **Settings → Variables**
2. Click **+ Create Variable**
3. Examples:

```
Variable: username_admin
  Value: admin
  
Variable: password_admin
  Value: admin123

Variable: project_name_base
  Value: Test Project
  
Variable: today
  Value: {{now | date: 'YYYY-MM-DD'}}
```

### Use in Tests:
When recording, instead of hardcoding "admin":
1. Type variable in recording: `{{username_admin}}`
2. Mabl will use actual value during playback
3. Easy to change globally

---

## Quick Test Creation - 10-Minute Version

**If you have limited time, create tests in this order (fastest wins):**

### Tier 1 (Must Have) - 30 minutes total:
1. ✅ Login - Valid (7 min)
2. ✅ Projects List (5 min)
3. ✅ Create Project (10 min)
4. ✅ Mobile View (8 min)

### Tier 2 (Should Have) - 20 minutes:
5. ✅ Edit Project (8 min)
6. ✅ Delete Project (7 min)
7. ✅ Dark Mode (5 min)

### Tier 3 (Nice to Have) - 20 minutes:
8. ✅ Form Validation (10 min)
9. ✅ Archive Project (8 min)
10. ✅ Tablet View (2 min)

---

## Running Tests Continuously

### Schedule Daily Tests:
1. Create your test plan
2. Click **Settings → Schedule**
3. Set to run **Daily at 2:00 AM**
4. Tests run automatically
5. Email report sent each morning

### Integrate with CI/CD:
See previous guide for GitHub Actions / Jenkins setup

---

## Next Steps:

1. **Start Recording**: Create first test this week
2. **Build Library**: Add 2 tests per day
3. **Create Plans**: Group related tests
4. **Run Regularly**: Schedule daily runs
5. **Monitor**: Review failures and fix
6. **Scale**: Add more tests as features expand

---

**Ready? Start with Test #1 - Login. You've got this! 💪**

For detailed technical setup: See `MABL_SETUP_GUIDE.md`
For complete test cases: See `MABL_TEST_CASES.md`

