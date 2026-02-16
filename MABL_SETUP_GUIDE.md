# 📍 Mabl Test Case Setup Guide

## Getting Started with Mabl

### What is Mabl?
Mabl is a visual testing and automation platform that:
- ✅ Records user interactions visually
- ✅ Replays tests intelligently
- ✅ Detects visual changes
- ✅ Manages test infrastructure
- ✅ Integrates with CI/CD pipelines

---

## Step 1: Initial Setup

### 1.1 Create Mabl Account
1. Go to `https://www.mabl.com/`
2. Sign up for account
3. Create your organization
4. Create a workspace for InfraCore

### 1.2 Install Mabl Desktop Recorder
1. In Mabl, go to **My Account** → **Browser Extensions**
2. Download Mabl Chrome/Firefox extension
3. Install extension
4. Login in extension

### 1.3 Create Your First Journey (Test)
1. In Mabl, click **+ Create**
2. Select **Journey** (test flow)
3. Name: `Login Test`
4. Click **Create**

---

## Step 2: Recording Your First Test

### 2.1 How to Record a Test

**Method 1: Using Mabl Recorder (Best for Beginners)**

1. Open Mabl → Click **Create Journey**
2. Enter app URL: `http://localhost:8000/login`
3. Click **Start Recording**
4. Mabl opens your app in a new window
5. Click on elements naturally - Mabl records actions:
   - Clicking
   - Typing text
   - Selecting dropdowns
   - Checking/unchecking boxes
   - Submitting forms

6. Verify the result (success/failure)
7. Click **Stop Recording** in Mabl
8. Mabl creates test steps automatically

### 2.2 Example: Recording Login Test

**Actions to Record**:
```
Step 1: Navigate to http://localhost:8000/login
Step 2: Click Username input field
Step 3: Type "admin"
Step 4: Click Password input field
Step 5: Type "admin123"
Step 6: Click Login button
Step 7: Verify page shows "Projects" or dashboard
```

**How Mabl Records This**:
```
1. Navigate to https://localhost:8000/login
2. Click element [Login Username Input] at (150, 250)
3. Type "admin"
4. Click element [Login Password Input] at (150, 300)
5. Type "admin123"
6. Click element [Login Button] at (200, 350)
7. Assert page title contains "Projects"
```

---

## Step 3: Test Case Creation - Login Flow

### Test Case 3.1: Valid Login

**To Create in Mabl:**

1. **Create New Journey**
   - Name: `TC-001-Valid Login`
   - URL: `http://localhost:8000/login`

2. **Record Steps**
   ```
   Step 1: Element - Click | Login Username Input
   Step 2: Input - Type | admin
   Step 3: Element - Click | Login Password Input
   Step 4: Input - Type | admin123
   Step 5: Element - Click | Login Button
   Step 6: Wait for navigation
   Step 7: Assertion - Page contains "Projects"
   ```

3. **Add Verifications**
   - Page title = "InfraCore"
   - Sidebar visible with username "admin"
   - URL contains "/projects" or "/dashboard"

4. **Add Assertions** (Mabl Assertions)
   ```
   Assert that:
   - element "Projects" is visible
   - element with text "admin" is visible in sidebar
   - URL changed from /login to /projects
   ```

5. **Save Journey**

---

## Step 4: Test Case Creation - Project Management

### Test Case 4.1: Create Project

**Testing Steps:**

```
Pre-condition: User logged in, on projects page

Step 1: Click "Create New Project" button or "+" icon
         Element: Button with text "Create New Project"
         
Step 2: Fill project form
         - Project Name input: Type "Test Project [timestamp]"
         - Description textarea: Type "Test Description"
         - Location input: Type "Test Location"
         - Budget input: Type "100000"
         
Step 3: Click "Create" or "Save" button
         Element: Button with text "Create"
         
Step 4: Verify success
         - Assert: Toast/Alert message shows "Project created successfully"
         - Assert: Page redirects to projects list
         - Assert: New project visible in table
         
Step 5: Verify data in table
         - Assert: Project name in first column = "Test Project [timestamp]"
         - Assert: Status shows "Active" badge
```

**In Mabl:**

1. Create Journey: `TC-002-Create Project`
2. Start at: `http://localhost:8000/projects`
3. Record:
   ```
   1. Click button "Create New Project"
   2. Wait for form to load
   3. Click input "Project Name"
   4. Type "Test Project 2026-02-17"
   5. Click textarea "Description"
   6. Type "Test Description"
   7. Click input "Location"
   8. Type "Test Location"
   9. Click input "Budget"
   10. Type "100000"
   11. Click button "Create"
   12. Wait for message
   13. Refresh if needed
   14. Assert project in table
   ```

4. Add Assertions:
   ```
   - Text "[success message]" appears
   - Text "Test Project 2026-02-17" appears in table
   - Text "Active" appears in status column
   ```

---

## Step 5: Test Case Creation - Responsive Design

### Test Case 5.1: Mobile View - Phone (375px)

**In Mabl:**

1. Create Journey: `TC-010-Mobile View Phone`
2. Set Device Emulation: **iPhone 12 (375px)**
3. Record normal interaction:
   ```
   1. Navigate to /projects
   2. Verify page displays without horizontal scroll
   3. Click menu button (hamburger icon)
   4. Verify sidebar visible
   5. Click project row
   6. Verify detail page loads properly
   ```

4. Add Visual Assertions
   ```
   - No elements overflow screen width
   - Touch targets visible and tappable
   - Font sizes readable (14px+)
   - Images responsive
   ```

5. **Add Layout Tests:**
   - Assert element width = 100% or viewport width
   - Assert no overflow-x
   - Assert button heights ≥ 44px

### Test Case 5.2: Mobile View - Tablet (768px)

```
Create Journey: `TC-011-Mobile View Tablet`
Device: iPad (768x1024)

Record:
1. Navigate to /projects
2. Verify layout optimized for tablet
3. Verify 2-column form if form exists
4. Verify tables show normally
5. Verify sidebar visible
```

---

## Step 6: Test Case Creation - Dark Mode

### Test Case 6.1: Dark Mode Toggle

**In Mabl:**

1. Create Journey: `TC-020-Dark Mode Toggle`
2. Start at: `http://localhost:8000/`
3. Record:
   ```
   Step 1: Login (if needed)
   Step 2: Locate dark mode toggle (sun/moon icon)
   Step 3: Click toggle to enable dark mode
   Step 4: Wait for colors to change
   Step 5: Assert background is dark
   Step 6: Assert text is light
   Step 7: Refresh page
   Step 8: Assert dark mode persists
   ```

4. Add Color Assertions:
   ```
   Assert element "body" has:
   - Background color = #0f172a (dark)
   - Text color = #e5e7eb (light)
   ```

5. Visual Assertion:
   - Compare screenshot before/after toggle
   - Verify colors changed appropriately

---

## Step 7: Using Mabl Variables

### 7.1 Create Test Data Variables

In Mabl, you can create variables for reusable test data:

```
Variable Name: testUsername
Value: admin

Variable Name: testPassword
Value: admin123

Variable Name: testProjectName
Value: Test Project {{date.today}}

Variable Name: testEmail
Value: testuser@example.com
```

**Use in Tests:**
```
Step 1: Type {{testUsername}}    # Replaces with "admin"
Step 2: Type {{testPassword}}    # Replaces with "admin123"
```

---

## Step 8: Creating Test Suites

### 8.1 Group Related Tests

In Mabl, create a **Plan** to run multiple journeys:

**Plan 1: Authentication**
- TC-001-Valid Login
- TC-002-Invalid Login
- TC-003-Empty Fields Login
- TC-004-Logout

**Plan 2: Projects Management**
- TC-010-View Projects
- TC-011-Create Project
- TC-012-Edit Project
- TC-013-Delete Project
- TC-014-Archive Project
- TC-015-Unarchive Project

**Plan 3: Responsive Design**
- TC-020-Mobile View Phone
- TC-021-Mobile View Tablet
- TC-022-Desktop View
- TC-023-Touch Interaction

**Plan 4: Forms & Validation**
- TC-030-Project Form Validation
- TC-031-Email Field Validation
- TC-032-Date Range Validation
- TC-033-Required Fields

**Plan 5: Dark Mode & Theme**
- TC-040-Dark Mode Toggle
- TC-041-Dark Mode Persistence
- TC-042-System Preference

---

## Step 9: Setting Up Assertions

### 9.1 Common Assertion Types

**Text Assertions**
```
Assert element contains text: "Projects"
Assert page title is: "InfraCore"
Assert element exact text: "Active"
```

**Element Visibility**
```
Assert element is visible: button.logout
Assert element is hidden: modal.delete-confirmation
Assert element count (tr) = 5   # 5 table rows
```

**URL Assertions**
```
Assert URL changes to: /projects
Assert URL contains: /admin/
Assert URL matches pattern: /projects/[0-9]+
```

**Property Assertions**
```
Assert element has attribute: disabled = true
Assert element has class: btn-primary
Assert element has style: background-color = #2563eb
```

**Wait Assertions**
```
Wait for element to appear: .success-message
Wait for element to disappear: .loading-spinner
Wait for URL change to: /projects
```

### 9.2 Add Assertion in Mabl

1. After recording a step, click **+ Add Assertion**
2. Select assertion type:
   - **Visual** - Compare screenshots
   - **Element Presence** - Element exists/visible
   - **Text** - Text contains/equals
   - **Element Count** - Number of elements
   - **URL** - URL contains/matches
   - **API** - API response validation

3. Configure assertion
4. Save

---

## Step 10: Running Tests

### 10.1 Run Single Journey

1. Open journey in Mabl
2. Click **Run** button
3. Select environment: **Development**
4. Click **Start Run**
5. Watch test execute
6. View results:
   - ✅ Passed
   - ❌ Failed
   - ⏭️ Skipped

### 10.2 Run Entire Plan

1. Open Plan
2. Click **Run Plan**
3. Select:
   - Environment: Development
   - Browser: Chrome (or all)
   - Device: Desktop (or multiple)
4. Click **Start Run**
5. View results by test

### 10.3 Schedule Tests (CI/CD Integration)

1. Open Plan
2. Click **Settings**
3. Go to **Schedule**
4. Set frequency:
   - Hourly
   - Daily
   - Weekly
5. Click **Save**

Tests will run automatically at scheduled times.

---

## Step 11: CI/CD Integration

### 11.1 GitHub Actions Integration

Add to `.github/workflows/test.yml`:

```yaml
name: Mabl Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  mabl-test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Run Mabl Tests
      uses: mablhq/mabl-action@v1
      with:
        api-key: ${{ secrets.MABL_API_KEY }}
        plan-id: your-plan-id
        environment: staging
        
    - name: Upload Results
      if: always()
      uses: actions/upload-artifact@v2
      with:
        name: mabl-results
        path: ./mabl-results/
```

### 11.2 Jenkins Integration

Add to Jenkinsfile:

```groovy
pipeline {
  stages {
    stage('Mabl Tests') {
      steps {
        sh '''
          curl -X POST https://api.mabl.com/public/v1/runs \
            -H "Authorization: Bearer ${MABL_API_KEY}" \
            -H "Content-Type: application/json" \
            -d '{"plan_id": "your-plan-id", "environment_id": "dev"}'
        '''
      }
    }
  }
}
```

---

## Step 12: Interpreting Results

### 12.1 Test Report

After running tests, Mabl provides:

**Overview**
- Total tests: 15
- Passed: 13 ✅
- Failed: 2 ❌
- Skipped: 0
- Success rate: 86.7%

**Failed Tests**
- `TC-012-Edit Project` - Element not found
  - Issue: Button text changed
  - Fix: Update button selector

- `TC-020-Dark Mode Toggle` - Visual mismatch
  - Issue: Color slightly different
  - Fix: Update expected color

**Screenshots**
- Before state
- After state
- Highlighted differences

### 12.2 Debugging Failed Tests

1. **Check Screenshots**
   - What did test expect?
   - What actually happened?

2. **Check Step-by-Step**
   - Which step failed?
   - What was the error?

3. **Review Code**
   - Did recent changes break test?
   - Need to update test expectations?

4. **Inspect Element**
   - Open DevTools and inspect element
   - Is selector still correct?
   - Is element visible?

5. **Edit Test**
   - Click **Edit** on failed journey
   - Re-record the step
   - Save and re-run

---

## Step 13: Best Practices

### 13.1 Recording Tips

✅ **Do:**
- Record at normal speed
- Wait for elements to load
- Click elements naturally
- Use stable selectors (IDs, classes)
- Test with realistic data

❌ **Don't:**
- Rush through recording
- Click too fast
- Use hardcoded data (use variables)
- Rely on order of elements
- Test with just one browser

### 13.2 Assertion Tips

✅ **Do:**
- Add multiple assertions
- Verify success AND data
- Check visual elements
- Wait for dynamic content
- Assert on unique identifiers

❌ **Don't:**
- Rely on single assertion
- Only check page loads
- Ignore visual changes
- Skip waiting for AJAX
- Use fragile selectors

### 13.3 Maintenance Tips

✅ **Do:**
- Review tests monthly
- Update when UI changes
- Use variables for data
- Document test purpose
- Keep tests independent

❌ **Don't:**
- Ignore failed tests
- Use deprecated selectors
- Create test dependencies
- Have unclear expectations
- Forget to update docs

---

## Step 14: Common Issues & Solutions

### Issue 1: Element Not Found

**Error**: `Element selector not found`

**Solution**:
1. Open test, click **Edit**
2. Re-record that step
3. Inspect element to verify selector
4. Use more specific selector if needed
5. Save and re-run

### Issue 2: Element Timing Issue

**Error**: `Timeout waiting for element`

**Solution**:
1. Add **Wait** step before element
2. Increase wait timeout (set to 10 seconds)
3. Wait for specific condition:
   ```
   Wait for element: .success-message
   Wait for URL change
   Wait for element visibility
   ```

### Issue 3: Sensitive to Data

**Error**: `Assert text mismatch - expected "123" but got "456"`

**Solution**:
1. Use variables instead of hardcoded values
2. Assert on partial text:
   ```
   Assert text contains "Active"   # Instead of exact match
   ```
3. Use regex patterns for dynamic content

### Issue 4: Responsive Design Changes

**Error**: `Visual assertion failed - layout changed`

**Solution**:
1. Create separate tests for each device size
2. Update visual baseline after intentional changes
3. Use device-specific assertions:
   ```
   Plan for Desktop
   Plan for Tablet
   Plan for Mobile
   ```

---

## Quick Reference: Recording Actions

| Action | Mabl Record | What to Do |
|--------|------------|-----------|
| Click | Click element | Click naturally on element |
| Type | Type text | Click input, then type |
| Select | Choose option | Click dropdown, select value |
| Navigate | Go to URL | Type URL in address bar |
| Wait | Wait step | Mabl auto-inserts wait |
| Assert | Add assertion | Click + Assert after step |
| Scroll | Scroll page | Scroll naturally on page |
| Hover | Hover element | Hover mouse over element |
| Focus | Focus input | Click input field |
| Clear | Clear input | Select all + delete |

---

## Test Template - Copy & Use

### Template: New Test Case

```
Test Name: [TC-XXX-Feature Name]
Description: [What does this test verify?]
Pre-conditions: [User logged in? On which page?]

Steps:
1. [Action on element] - [Expected result]
2. [Action on element] - [Expected result]
3. [Action on element] - [Expected result]

Assertions:
- [Assert 1]
- [Assert 2]
- [Assert 3]

Test Data:
- [Variable 1: value]
- [Variable 2: value]

Devices: Desktop, Mobile, Tablet
Browsers: Chrome, Firefox, Safari
Priority: High/Medium/Low
```

---

## Running Your First Tests

### Quick Start (5 minutes)

1. **Create Login Test**
   - Journey: `Login Test`
   - URL: `http://localhost:8000/login`
   - Record: username + password + login click
   - Assert: Page title changes
   - Save

2. **Create Projects View Test**
   - Journey: `View Projects`
   - URL: `http://localhost:8000/projects`
   - Assert: Projects table visible
   - Save

3. **Create Plan**
   - Name: `Smoke Tests`
   - Add both journeys
   - Run plan
   - Check results

4. **View Results**
   - Screenshot comparisons
   - Step-by-step execution
   - Success rate

---

**Next**: Start recording your first test case in Mabl!

