# 🧪 Testing InfraCore on Mabl - Step-by-Step Guide

## ⚡ Quick Start (10 Minutes)

### Step 1: Open Mabl
1. Go to `https://app.mabl.com` (or your Mabl workspace)
2. Login with your account
3. You should see the dashboard

### Step 2: Create Your First Journey (Test)
1. Click **+ Create** button
2. Select **Journey**
3. Fill in:
   - Name: `Login Test`
   - Description: `Test login with valid credentials`
4. Click **Next** or **Create**

### Step 3: Start Recording
1. You'll see an option to enter URL
2. Enter: `http://localhost:8000/login`
3. Click **Start Recording** or **Record**
4. Mabl will open your website in a new window

### Step 4: Perform Login (5 minutes)
In the opened browser window:

```
Action 1: Click username input field
         → Type: admin
         
Action 2: Click password input field  
         → Type: admin123
         
Action 3: Click Login button
         → Wait for page to load
```

Mabl records every action automatically! 🎥

### Step 5: Stop Recording
1. Go back to Mabl window
2. Click **Stop Recording** button
3. Mabl shows you a summary of steps recorded

### Step 6: Add Verification (Assertion)
After login, add what to check:

1. Click **+ Add Assertion** button
2. Select **Text Assertion**
3. Click on the page where you see "Projects"
4. Select "contains text"
5. Text: `Projects`
6. Click **Save**

### Step 7: Save & Run
1. Click **Save Journey**
2. Click **Run** to execute the test
3. Watch your test run automatically ✅

**Congratulations! Your first test is complete!** 🎉

---

## 📋 Testing Your Website - Full Process

### What Your Website Needs
Your website is already running on:
```
http://localhost:8000/
```

Make sure you can access:
- ✅ `http://localhost:8000/login` - Login page
- ✅ `http://localhost:8000/projects` - Projects list
- ✅ `http://localhost:8000/` - Home/dashboard

### Prerequisites Before Testing
- [ ] InfraCore server running (`uvicorn app.main:app --host 127.0.0.1 --port 8000`)
- [ ] Mabl account created (free tier available)
- [ ] Browser extension installed
- [ ] Can access http://localhost:8000 in browser

---

## 🔐 Test 1: Login (Most Important First)

### In Mabl Dashboard:
```
1. Click: + Create → Journey
2. Name: "TC-001-Login-Valid"
3. URL: http://localhost:8000/login
4. Click: Start Recording
```

### In Browser Window That Opens:
```
STEP 1: Click the Username field
        → Mabl highlights it
        → You see the field is selected

STEP 2: Type: admin
        → Mabl records: "Type: admin"

STEP 3: Click the Password field
        → Mabl highlights it

STEP 4: Type: admin123
        → Mabl records: "Type: admin123"

STEP 5: Click the "Login" button
        → Mabl records: "Click: Login button"
        → Page redirects to /projects
        → Wait a few seconds for page to load
```

### Back in Mabl:
```
1. Click: Stop Recording
2. Mabl shows steps taken:
   - Navigate to http://localhost:8000/login
   - Click [username field]
   - Type "admin"
   - Click [password field]
   - Type "admin123"
   - Click [Login button]
   - Wait for page load
```

### Add Assertion (Verification):
```
1. Click: + Add Assertion (after logout button step)
2. Select: Text Assertion
3. In the page, click where you see "Projects" or your username
4. Choose: "contains text"
5. Enter: "Projects" (or "admin" if you see username)
6. Click: Save Assertion
```

### Run Test:
```
1. Click: Save Journey
2. Click: Run
3. Wait 30-60 seconds for test to run
4. Result should show: ✅ PASSED
```

**If it fails:**
- Check login credentials are correct
- Verify server is running
- Check the screenshot to see what went wrong

---

## 📱 Test 2: View Projects List

### Create New Journey:
```
Name: "TC-002-View-Projects"
URL: http://localhost:8000/projects
```

### Record (Assuming you need to login first):
```
STEP 1: Navigate to /projects
        (If redirected to login, login first)
        
STEP 2: Wait for projects table to load
        (Mabl auto-inserts wait)

STEP 3: Look at projects table
        Page should show:
        - Column headers (Name, Status, Actions)
        - List of projects
        - Buttons (Create, Edit, Delete)
```

### No actions needed - just observation!
Since viewing doesn't require clicks, after recording:

### Add Assertions:
```
1. Click: + Add Assertion
2. Select: Text Assertion
3. Click on "Projects" title or table header
4. Element should contain: "Projects"

2. Click: + Add Assertion (again, for another check)
3. Select: Element Visibility
4. Click on the table element
5. Verify: Element is visible
```

### Run Test:
```
1. Click: Save
2. Click: Run
3. Should show: ✅ PASSED
```

---

## ➕ Test 3: Create a New Project

### Create Journey:
```
Name: "TC-003-Create-Project"
URL: http://localhost:8000/projects
```

### Recording Steps:

**Step 1: Click "Create New Project" button**
```
In browser:
- Look for button with text "Create New Project" or "+" icon
- Click it
- Wait for form to appear
- Mabl records: "Click [Create Project Button]"
```

**Step 2: Fill Project Name**
```
- Click "Project Name" field
- Type: "Test Project 2026-02-17"
- Mabl records: "Type: Test Project 2026-02-17"
```

**Step 3: Fill Description**
```
- Click "Description" field
- Type: "Automated test project"
- Mabl records the typing
```

**Step 4: Fill Budget** 
```
- Click "Budget" field
- Type: "100000"
- Mabl records it
```

**Step 5: Click Create/Save Button**
```
- Look for "Create" or "Save" button
- Click it
- Wait for success message
```

### Add Assertions:
```
1. + Add Assertion
2. Select: Text Assertion
3. Click on success message area
4. Select: "contains text"
5. Text: "created successfully" (or whatever your message says)

4. + Add Assertion (for verification)
5. Select: Text Assertion  
6. Click on the new project name in the table
7. Select: "contains text"
8. Text: "Test Project 2026-02-17"
```

### Run Test:
```
1. Save → Run
2. Should show: ✅ PASSED (if creation works)
```

---

## 📱 Test 4: Mobile View (375px - Phone)

This is important! Tests your responsive design.

### Create Journey:
```
Name: "TC-004-Mobile-View-Phone"
```

### BEFORE Recording - Set Device:
```
1. Click: Settings (or Device Settings)
2. Select: iPhone 12 (or similar)
3. This sets width to 375px
4. Click: Start Recording

Now when browser opens, it's in PHONE SIZE!
```

### Record Actions:
```
STEP 1: Navigate to /projects
STEP 2: Verify page visible without horizontal scroll
STEP 3: Click menu icon (hamburger ☰) if visible
STEP 4: Verify sidebar/menu opens
STEP 5: Click a project to view details
STEP 6: Verify detail page loads
```

### Add Assertions:
```
1. + Add Assertion
2. Element Property
3. Click on body/container
4. Property: width
5. Value: should not exceed viewport

(Or)
1. + Add Assertion
2. Visual Assertion
3. Compare screenshot before/after
4. Verify no elements outside screen
```

### Run on Mobile:
```
1. Save
2. Run
3. Check results - should show mobile layout ✅
```

---

## 🎨 Test 5: Dark Mode Toggle

### Create Journey:
```
Name: "TC-005-Dark-Mode"
URL: http://localhost:8000/
```

### Recording:
```
STEP 1: Look for dark mode toggle
        Usually: sun/moon icon in header
        Click it

STEP 2: Watch colors change
        Background should go dark
        Text should go light

STEP 3: Refresh page (F5 or Ctrl+R)
        Dark mode should persist

STEP 4: Toggle back to light mode
        Colors switch back
```

### Add Assertions:
```
1. + Add Assertion
2. Visual Assertion
3. Before toggle - take screenshot
4. Select: "visual comparison"
5. After toggle - colors should be different ✅

OR

1. + Add Assertion
2. Element Property
3. Click on background element
4. Check: background-color = dark color (#0f172a)
```

### Run Test:
```
1. Save → Run
2. Visual comparison runs
3. Shows: ✅ PASSED if colors are different
```

---

## 🧪 Running Multiple Tests Together

Once you've created several tests:

### Create a Test Plan:
```
1. Click: + Create → Plan
2. Name: "Smoke Tests"
3. Click: + Add Journey
4. Select: TC-001-Login-Valid
5. Click: + Add Journey
6. Select: TC-002-View-Projects
7. Click: + Add Journey
8. Select: TC-003-Create-Project
9. Click: Create Plan
```

### Run All Tests:
```
1. Click: Run Plan
2. Select device: Desktop
3. Select browser: Chrome
4. Click: Start Run

Mabl runs ALL tests one after another!
- Test 1: Login ✅
- Test 2: View Projects ✅
- Test 3: Create Project ✅

Final Report: 3/3 PASSED (100% success!) 🎉
```

---

## 📊 Understanding Test Results

### What You See After Running:

#### ✅ PASSED Test
```
Test: TC-001-Login-Valid
Status: PASSED ✓
Duration: 45 seconds
Steps: 7
Assertions: 2/2 passed
```

Click on it to see:
- Step-by-step screenshots
- What it did
- Verification results

#### ❌ FAILED Test
```
Test: TC-002-View-Projects  
Status: FAILED ✗
Duration: 60 seconds
Steps: 3
Assertions: 1/2 failed
Message: "Element not found: Projects table"
```

Click to see:
- Which step failed
- Screenshot at failure point
- Error message
- How to fix it

---

## 🔧 Common Issues While Recording

### Issue 1: "Element Not Found"
**What it means:** Mabl couldn't find the button you clicked

**Solution:**
- Re-record that step by clicking the element again
- Or edit the step manually with more specific selector

### Issue 2: "Timeout - Page Didn't Load"
**What it means:** Page took too long to load

**Solution:**
- Add a "Wait" step before next action
- Increase wait timeout to 15 seconds
- Check if server is running properly

### Issue 3: "Form Submission Failed"
**What it means:** The form didn't submit correctly

**Solution:**
- Verify all required fields are filled
- Check test data is correct
- Try manually to ensure it works

### Issue 4: "Element Appearing in Different Location"
**What it means:** Element location changed between runs

**Solution:**
- Use more stable selectors (element name, ID)
- Use visual selectors instead of position-based
- Click element properties instead of coordinates

---

## 🎯 Quick Test Checklist

Use this to create your first 5 tests quickly:

### Test 1: Login ✅
- [ ] Create journey "Login-Valid"
- [ ] Record: username + password + click login
- [ ] Add assertion: check page changed
- [ ] Run and verify ✅ PASSED

### Test 2: Projects List ✅
- [ ] Create journey "View-Projects"  
- [ ] Record: navigate to /projects
- [ ] Add assertion: "Projects" text visible
- [ ] Run and verify ✅ PASSED

### Test 3: Create Project ✅
- [ ] Create journey "Create-Project"
- [ ] Record: click create, fill form, submit
- [ ] Add assertion: success message + project in table
- [ ] Run and verify ✅ PASSED

### Test 4: Mobile View ✅
- [ ] Create journey "Mobile-View"
- [ ] Set device to iPhone before recording
- [ ] Record: navigate and interact
- [ ] Add assertion: no horizontal scroll
- [ ] Run and verify ✅ PASSED

### Test 5: Dark Mode ✅
- [ ] Create journey "Dark-Mode"
- [ ] Record: toggle dark mode
- [ ] Add assertion: background color changed
- [ ] Run and verify ✅ PASSED

**Total time: ~45 minutes for all 5 tests** ⏱️

---

## 📸 Real-World Example: Full Login Test

Here's exactly what your screen should show:

### Screenshot 1: Mabl Dashboard
```
┌─ Mabl Dashboard ────────────────────┐
│ + Create                             │
│ ├─ Journey                           │
│ ├─ Plan                              │
│ └─ App                               │
│                                      │
│ Recent Journeys:                     │
│ • TC-001-Login-Valid                 │
│ • TC-002-View-Projects               │
└──────────────────────────────────────┘
```

### Screenshot 2: Click "Create Journey"
```
┌─ Create New Journey ─────────────────┐
│ Name: TC-001-Login-Valid             │
│ Description: Test login flow         │
│ App: InfraCore                       │
│ URL: http://localhost:8000/login     │
│                                      │
│ [Create]  [Cancel]                   │
└──────────────────────────────────────┘
```

### Screenshot 3: Browser Opens (Recording)
```
┌─ Your Website in Browser (Recording)─┐
│                                      │
│ Login Page                           │
│ ┌── Username ─────────┐              │
│ │ admin               │ ← You type   │
│ └─────────────────────┘              │
│                                      │
│ ┌── Password ─────────┐              │
│ │ admin123            │ ← You type   │
│ └─────────────────────┘              │
│                                      │
│    [Login Button]  ← You click       │
│                                      │
│ [Stop Recording] (in Mabl window)    │
└──────────────────────────────────────┘
```

### Screenshot 4: Review Recorded Steps
```
┌─ Recorded Steps ─────────────────────┐
│ Journey: TC-001-Login-Valid          │
│                                      │
│ ✓ Step 1: Navigate to /login         │
│ ✓ Step 2: Click [username input]     │
│ ✓ Step 3: Type "admin"               │
│ ✓ Step 4: Click [password input]     │
│ ✓ Step 5: Type "admin123"            │
│ ✓ Step 6: Click [Login button]       │
│ ✓ Step 7: Wait for page transition   │
│                                      │
│ + Add Assertion                      │
│ [Save] [Run]                         │
└──────────────────────────────────────┘
```

### Screenshot 5: Add Assertion
```
┌─ Add Assertion ──────────────────────┐
│ Type: Text Assertion                 │
│                                      │
│ Click on page to select element:     │
│ ☑ "Projects" (found on page)         │
│                                      │
│ Assertion: Contains text "Projects"  │
│                                      │
│ [Add] [Cancel]                       │
└──────────────────────────────────────┘
```

### Screenshot 6: Test Results
```
┌─ Test Run Results ───────────────────┐
│ Journey: TC-001-Login-Valid          │
│ Status: ✅ PASSED                    │
│                                      │
│ Duration: 45 seconds                 │
│ Steps Executed: 7/7                  │
│ Assertions Passed: 2/2 ✓             │
│                                      │
│                                      │
│ Steps:                               │
│ ✓ Navigate to /login                 │
│ ✓ Click username input               │
│ ✓ Type "admin"                       │
│ ✓ Click password input               │
│ ✓ Type "admin123"                    │
│ ✓ Click Login button                 │
│ ✓ Page redirected to /projects       │
│                                      │
│ Assertions:                          │
│ ✓ Text "Projects" found              │
│ ✓ URL changed to /projects           │
└──────────────────────────────────────┘
```

---

## 💡 Pro Tips While Testing

✅ **Do This:**
- Test one feature at a time
- Add multiple assertions per test
- Wait for AJAX/dynamic content to load
- Use meaningful test names
- Start with happy path (what works)

❌ **Avoid This:**
- Recording too many steps in one test (keep <10 steps)
- Hardcoding values (use variables instead)
- Testing dependent on other test results (independent tests)
- Clicking coordinate positions (click element names)
- Ignoring wait times

---

## 🚀 Next Steps After Successful Testing

Once your first test passes:

1. **Create 3 more tests** (View Projects, Create Project, Mobile View)
   - 15 minutes each = 45 minutes total

2. **Create a Test Plan**
   - Group your 4 tests together
   - Click "Create Plan" 
   - Add all 4 journeys
   - Run plan to execute all at once

3. **Schedule Daily Runs**
   - Plan settings → Schedule
   - Set to run every day at 2 AM
   - Get email with results each morning

4. **Integrate with GitHub** (optional)
   - See MABL_SETUP_GUIDE.md for GitHub Actions integration
   - Tests run on every code push

---

## ❓ FAQ

**Q: Can I test if I'm not logged in?**
A: Yes! Each journey can handle login within itself. Record login as first steps.

**Q: What if element location changes?**
A: Re-record that step. Mabl learns the new location.

**Q: Can I test APIs too?**
A: Yes! Mabl has API testing features, but visual recording covers UI testing.

**Q: How long does a test take to run?**
A: Usually 30-90 seconds depending on page load speed.

**Q: What if my website crashes during test?**
A: Test fails with clear error. Check your logs.

**Q: Can I use my own test data?**
A: Yes! Create variables in Mabl settings. Use {{variable}} in test.

**Q: Do I need to stop my server for testing?**
A: No! Server must keep running. Tests need http://localhost:8000 accessible.

---

## 🎬 Video/Demo Alternative

If visual recording is confusing:
1. Watch Mabl's tutorial: https://www.mabl.com/academy
2. Watch their 5-minute demo
3. Come back and follow this guide

---

## ✅ Completion Checklist

After completing this guide, you should have:

- [ ] Mabl account created
- [ ] First test recorded and passing
- [ ] Second test created
- [ ] Third test created 
- [ ] Test plan created with 3+ tests
- [ ] Full test suite running
- [ ] All tests showing ✅ PASSED
- [ ] Screenshots and results reviewed
- [ ] Ready to add more tests

---

**You're ready to test on Mabl! Start with the Quick Start at the top.** 🚀

Questions? Check these:
- MABL_TEST_CASES.md - For specific test examples
- MABL_SETUP_GUIDE.md - For technical setup details
- MABL_QUICK_START.md - For faster walkthrough

