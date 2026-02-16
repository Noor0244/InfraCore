# 🧪 Mabl Test Cases for InfraCore

## Overview
Complete test case documentation for InfraCore application using Mabl visual testing platform.

---

## Test Scenario 1: User Authentication & Login

### Test Case 1.1: Valid Login
**Objective**: Verify user can successfully login with valid credentials

**Steps**:
1. Navigate to `http://localhost:8000/login`
2. Enter valid username in "Username" field
3. Enter valid password in "Password" field
4. Click "Login" button
5. Verify redirect to dashboard/projects page
6. Verify sidebar displays username and role

**Expected Result**: 
- ✅ User logged in successfully
- ✅ Dashboard loads with user data
- ✅ Sidebar shows "ADMIN" or user role

**Test Data**:
- Username: `admin`
- Password: `admin123`

---

### Test Case 1.2: Invalid Login
**Objective**: Verify login fails with invalid credentials

**Steps**:
1. Navigate to `http://localhost:8000/login`
2. Enter invalid username
3. Enter invalid password
4. Click "Login" button
5. Verify error message appears

**Expected Result**:
- ✅ Error message displayed
- ✅ User stays on login page
- ✅ No redirect to dashboard

---

### Test Case 1.3: Empty Fields Login
**Objective**: Verify login form validation

**Steps**:
1. Navigate to `http://localhost:8000/login`
2. Leave username field empty
3. Leave password field empty
4. Click "Login" button
5. Verify form validation message

**Expected Result**:
- ✅ Validation message shown
- ✅ Form not submitted

---

### Test Case 1.4: Logout
**Objective**: Verify user can logout successfully

**Steps**:
1. Login with valid credentials
2. Navigate to profile/settings section
3. Click "Logout" button
4. Verify redirect to login page
5. Try to access protected page (should redirect to login)

**Expected Result**:
- ✅ User logged out
- ✅ Redirect to login page
- ✅ Session cleared

---

## Test Scenario 2: Project Management

### Test Case 2.1: View All Projects
**Objective**: Verify user can view list of all projects

**Steps**:
1. Login with valid credentials
2. Navigate to `/projects`
3. Verify project list loads
4. Count number of projects displayed
5. Verify project columns: Name, Status, Actions

**Expected Result**:
- ✅ Projects list displays
- ✅ All columns visible (Name, Status, Actions)
- ✅ Projects sorted correctly
- ✅ Status badges visible (Active/Archived)

---

### Test Case 2.2: Create New Project
**Objective**: Verify user can create a new project

**Steps**:
1. Login and navigate to Projects page
2. Click "Create New Project" or "+" button
3. Fill project form:
   - Project Name: "Test Project"
   - Description: "Test Description"
   - Location: "Test Location"
   - Budget: 100000
4. Click "Create" button
5. Verify success message
6. Verify new project appears in list

**Expected Result**:
- ✅ Project created successfully
- ✅ Success message shown
- ✅ New project in list
- ✅ Project status is "Active"

**Test Data**:
```
Project Name: Test Project [timestamp]
Description: Automated test project
Location: Test Location
Budget: 100000
Start Date: Today
```

---

### Test Case 2.3: Edit Project
**Objective**: Verify user can edit existing project

**Steps**:
1. Login and navigate to Projects
2. Click "Edit" button for a project
3. Modify project fields:
   - Name: "Updated Test Project"
   - Description: "Updated Description"
4. Click "Save" button
5. Verify success message
6. Verify changes reflected in list

**Expected Result**:
- ✅ Project updated successfully
- ✅ Changes saved and visible
- ✅ No data loss
- ✅ Timestamp updated

---

### Test Case 2.4: Delete Project
**Objective**: Verify user can delete a project

**Steps**:
1. Login and navigate to Projects
2. Click "Delete" button for a project
3. Verify confirmation dialog appears
4. Click "Confirm" to delete
5. Verify project removed from list
6. Verify success message

**Expected Result**:
- ✅ Confirmation dialog shown
- ✅ Project deleted after confirmation
- ✅ Project no longer in list
- ✅ Success message displayed

---

### Test Case 2.5: Archive Project
**Objective**: Verify user can archive an active project

**Steps**:
1. Login and navigate to Projects (Active view)
2. Locate an active project
3. Click "Archive" button
4. Verify confirmation message
5. Navigate to Archived projects view
6. Verify project now appears in Archived list

**Expected Result**:
- ✅ Project archived successfully
- ✅ Removed from Active list
- ✅ Appears in Archived list
- ✅ Status changed to "Archived"

---

### Test Case 2.6: Unarchive Project
**Objective**: Verify user can restore an archived project

**Steps**:
1. Login and navigate to Projects
2. Click "Archived" toggle/button
3. Verify Archived projects list appears
4. Click "Restore" or "Unarchive" for a project
5. Verify success message
6. Navigate back to Active projects
7. Verify restored project in Active list

**Expected Result**:
- ✅ Project restored successfully
- ✅ Removed from Archived list
- ✅ Appears in Active list
- ✅ Status changed back to "Active"

---

### Test Case 2.7: Validate Project Form Fields
**Objective**: Verify project form field validation

**Steps**:
1. Navigate to Create Project form
2. Try to submit with empty required fields
3. Verify validation messages appear
4. Enter very long text in Name field (>255 chars)
5. Verify character limit validation
6. Try to enter negative budget
7. Verify budget validation

**Expected Result**:
- ✅ Required field validation shown
- ✅ Character limit enforced
- ✅ Number validation working
- ✅ Form cannot submit with invalid data

---

## Test Scenario 3: Navigation & Sidebar

### Test Case 3.1: Sidebar Navigation
**Objective**: Verify sidebar navigation works correctly

**Steps**:
1. Login and view dashboard
2. Verify sidebar displays
3. Click each sidebar menu item:
   - Dashboard
   - Projects
   - Material Vendor (if admin)
   - Settings
   - Profile
4. Verify correct page loads for each menu

**Expected Result**:
- ✅ All menu items clickable
- ✅ Correct pages load
- ✅ Active menu highlighted
- ✅ No broken links

---

### Test Case 3.2: Mobile Sidebar Toggle
**Objective**: Verify sidebar toggle on mobile view

**Steps**:
1. Open browser DevTools (F12)
2. Enable device emulation (Ctrl+Shift+M)
3. Select mobile device (iPhone 12, 375px width)
4. Verify sidebar is hidden on mobile
5. Click menu toggle button (hamburger icon)
6. Verify sidebar slides in
7. Click outside sidebar or close button
8. Verify sidebar slides out

**Expected Result**:
- ✅ Sidebar hidden on mobile by default
- ✅ Toggle button visible
- ✅ Sidebar slides smoothly
- ✅ Close button works
- ✅ Content readable after sidebar closes

---

### Test Case 3.3: Breadcrumb Navigation
**Objective**: Verify breadcrumb navigation exists and works

**Steps**:
1. Navigate to nested page (e.g., Projects → Edit → Details)
2. Verify breadcrumb trail visible
3. Click each breadcrumb link
4. Verify correct page loads
5. Verify breadcrumb updates

**Expected Result**:
- ✅ Breadcrumb displayed correctly
- ✅ All links functional
- ✅ Navigation history preserved

---

## Test Scenario 4: Forms & Data Entry

### Test Case 4.1: Create Project Form - All Fields
**Objective**: Verify all form fields present and functional

**Steps**:
1. Navigate to Create Project form
2. Verify all fields present:
   - Project Name (text input)
   - Description (textarea)
   - Location (text input)
   - Budget (number input)
   - Start Date (date picker)
   - End Date (date picker)
   - Status (dropdown)
3. Fill each field with valid data
4. Submit form
5. Verify all data saved correctly

**Expected Result**:
- ✅ All fields present
- ✅ All fields functional
- ✅ Data validation working
- ✅ Form submits successfully
- ✅ Data persists in database

---

### Test Case 4.2: Date Field Validation
**Objective**: Verify date picker works correctly

**Steps**:
1. Open date field for Start Date
2. Verify calendar picker appears
3. Select a date
4. Verify date populated correctly
5. Try to select End Date before Start Date
6. Verify validation message

**Expected Result**:
- ✅ Date picker functional
- ✅ Dates selected correctly
- ✅ Date format correct
- ✅ Validation prevents invalid date ranges

---

### Test Case 4.3: Dropdown Selection
**Objective**: Verify dropdown menus work

**Steps**:
1. Open Status dropdown
2. Verify all options visible: Active, Draft, Completed
3. Select each option
4. Verify selection saves
5. Reopen dropdown
6. Verify previously selected option highlighted

**Expected Result**:
- ✅ Dropdown opens/closes smoothly
- ✅ All options visible
- ✅ Selection saved
- ✅ Selection persists on page reload

---

### Test Case 4.4: Form Error Handling
**Objective**: Verify form shows appropriate error messages

**Steps**:
1. Navigate to form
2. Leave required fields empty
3. Click Submit
4. Verify error messages appear for each required field
5. Fill some fields
6. Verify only relevant errors shown
7. Fix all errors
8. Verify errors disappear as fields filled

**Expected Result**:
- ✅ Error messages clear and helpful
- ✅ Errors shown for correct fields
- ✅ Errors disappear when fixed
- ✅ Success only when all valid

---

## Test Scenario 5: Dark Mode & Theme

### Test Case 5.1: Dark Mode Toggle
**Objective**: Verify dark/light mode switching

**Steps**:
1. Login to application
2. Verify current theme (light by default)
3. Look for dark mode toggle
4. Toggle to dark mode
5. Verify entire page switches to dark colors
6. Verify text readable on dark background
7. Refresh page
8. Verify dark mode persists

**Expected Result**:
- ✅ Dark mode toggle visible
- ✅ Colors change appropriately
- ✅ Text contrast maintained
- ✅ All elements themed correctly
- ✅ Preference persists on refresh

**Dark Mode Colors Should Show**:
- Background: Dark gray/black (#0f172a)
- Text: Light gray/white (#e5e7eb)
- Borders: Dark gray (#1f2937)
- Cards: Slightly lighter than background (#1e293b)

---

### Test Case 5.2: Light Mode
**Objective**: Verify light mode display

**Steps**:
1. Enable light mode
2. Verify all colors switch to light theme
3. Verify text readable on light background
4. Check contrast ratios
5. Refresh and verify persistence

**Expected Result**:
- ✅ Light colors applied
- ✅ Text dark enough to read
- ✅ Contrast acceptable (WCAG AA)
- ✅ No layout shifts

---

### Test Case 5.3: System Preference Detection
**Objective**: Verify app respects system dark mode setting

**Steps**:
1. On OS, set to dark mode preference
2. Open application in new browser
3. Verify app starts in dark mode
4. Change OS to light mode
5. Verify app switches to light mode

**Expected Result**:
- ✅ System preference detected
- ✅ App theme matches system
- ✅ Changes reflected automatically

---

## Test Scenario 6: Responsive Design

### Test Case 6.1: Mobile View - Phone (375px)
**Objective**: Verify layout on small phone screen

**Steps**:
1. Open DevTools (F12)
2. Enable device emulation (Ctrl+Shift+M)
3. Select iPhone 12 (375px)
4. Navigate through pages
5. Verify:
   - No horizontal scroll
   - Text readable
   - Buttons tappable (44px minimum)
   - Forms stack vertically
   - Images responsive
   - Tables convert to card layout

**Expected Result**:
- ✅ All content visible without horizontal scroll
- ✅ Font sizes readable (14px+)
- ✅ Touch targets 44px minimum
- ✅ Forms single-column
- ✅ Tables display as cards with data-labels
- ✅ Navigation accessible

---

### Test Case 6.2: Tablet View - Portrait (768px)
**Objective**: Verify layout on tablet in portrait

**Steps**:
1. Select iPad (768px) in device emulation
2. Verify layout optimized for tablet
3. Verify:
   - 2-column form layout
   - Tables show in normal format
   - Sidebar visible
   - Spacing comfortable
   - Touch targets 48px

**Expected Result**:
- ✅ Tablet-optimized layout
- ✅ 2-column forms
- ✅ Normal tables
- ✅ Proper spacing
- ✅ Easy to interact with

---

### Test Case 6.3: Tablet View - Landscape (1024px)
**Objective**: Verify layout on tablet landscape

**Steps**:
1. Select tablet landscape mode
2. Verify layout adjusts
3. Verify:
   - Wider viewport
   - Multi-column forms
   - Sidebar always visible
   - Tables fully visible
   - No truncation

**Expected Result**:
- ✅ Landscape optimized
- ✅ Full use of width
- ✅ All elements visible
- ✅ No truncation

---

### Test Case 6.4: Desktop View (1920px)
**Objective**: Verify layout on full desktop

**Steps**:
1. Select high-res desktop (1920px)
2. Verify layout
3. Verify:
   - Max-width applied (not stretching)
   - Sidebar visible
   - Forms properly spaced
   - Tables readable
   - No excessive whitespace

**Expected Result**:
- ✅ Desktop optimized
- ✅ Content centered
- ✅ Spacing appropriate
- ✅ Professional appearance

---

### Test Case 6.5: Touch Interaction on Mobile
**Objective**: Verify all touch targets are tappable

**Steps**:
1. Enable mobile device (375px)
2. Measure touch target sizes
3. Verify buttons: 44px minimum
4. Verify form fields: 44px minimum
5. Verify links: 44px minimum
6. Verify spacing between targets: 8px minimum

**Expected Result**:
- ✅ All buttons 44px+
- ✅ All fields 44px+
- ✅ All links 44px+
- ✅ No accidental double-taps needed

---

## Test Scenario 7: Data Tables & Lists

### Test Case 7.1: Projects Table on Desktop
**Objective**: Verify table displays correctly on desktop

**Steps**:
1. Navigate to Projects page on desktop (1920px)
2. Verify table displays with columns:
   - Project Name
   - Status
   - Created Date
   - Budget
   - Actions
3. Verify data displayed correctly
4. Verify table scrollable if needed
5. Verify row hover effects work

**Expected Result**:
- ✅ All columns visible
- ✅ Data readable
- ✅ Hover effects visible
- ✅ Not truncated

---

### Test Case 7.2: Projects Table on Mobile
**Objective**: Verify table converts to card layout on mobile

**Steps**:
1. Navigate to Projects page on mobile (375px)
2. Verify table not displayed as traditional table
3. Verify data shows as cards, each row one card
4. Verify `data-label` shows field names:
   - "Project Name: Test Project"
   - "Status: Active"
   - "Actions: Edit Delete"
5. Verify cards stacked vertically
6. Verify scrollable horizontally (not overflowing)

**Expected Result**:
- ✅ No horizontal scroll
- ✅ Card-based layout
- ✅ Data labels visible
- ✅ All data present
- ✅ Actions buttons visible

---

### Test Case 7.3: Table Sorting
**Objective**: Verify table columns sortable

**Steps**:
1. Navigate to table page
2. Click column header (if sortable)
3. Verify data sorts by that column
4. Click again to reverse sort
5. Verify sort arrow indicator

**Expected Result**:
- ✅ Data sorts correctly
- ✅ Sort direction indicated
- ✅ Multiple sorts possible

---

### Test Case 7.4: Table Pagination
**Objective**: Verify table pagination works

**Steps**:
1. Navigate to table with many rows
2. Verify pagination controls visible
3. Change items per page (if available)
4. Verify display count changes
5. Click next page
6. Verify new data loads
7. Click previous page
8. Verify correct data shown

**Expected Result**:
- ✅ Pagination controls work
- ✅ Page navigation smooth
- ✅ Correct data on each page
- ✅ No data duplication

---

## Test Scenario 8: User Management

### Test Case 8.1: View Users List (Admin)
**Objective**: Verify admin can view all users

**Steps**:
1. Login as admin
2. Navigate to Admin > Users
3. Verify user list displays
4. Verify columns: Username, Email, Role, Status
5. Verify all users visible
6. Verify sorting/filtering works

**Expected Result**:
- ✅ User list displays
- ✅ All columns present
- ✅ User data correct
- ✅ Admin functions available

---

### Test Case 8.2: Create New User (Admin)
**Objective**: Verify admin can create new user

**Steps**:
1. Login as admin
2. Navigate to Users
3. Click "Create User" button
4. Fill form:
   - Username: `testuser`
   - Email: `test@example.com`
   - Password: `TempPass123!`
   - Role: "User"
5. Click "Create" button
6. Verify success message
7. Verify user in users list

**Expected Result**:
- ✅ User created successfully
- ✅ User login works with new credentials
- ✅ User has correct role
- ✅ User can access assigned features

---

### Test Case 8.3: Edit User
**Objective**: Verify admin can edit user

**Steps**:
1. Login as admin
2. Navigate to Users
3. Click Edit for a user
4. Modify details:
   - Email changed to `newemail@example.com`
   - Role changed to "Editor"
5. Click "Save"
6. Verify success message
7. Verify changes reflected

**Expected Result**:
- ✅ User details updated
- ✅ Changes visible in list
- ✅ New role takes effect
- ✅ User still can login

---

### Test Case 8.4: Delete User
**Objective**: Verify admin can delete user

**Steps**:
1. Login as admin
2. Navigate to Users
3. Click Delete for a user
4. Verify confirmation dialog
5. Click "Confirm Delete"
6. Verify user removed from list
7. Verify deleted user cannot login

**Expected Result**:
- ✅ Confirmation shown
- ✅ User deleted
- ✅ Removed from list
- ✅ Cannot login after deletion

---

## Test Scenario 9: Data Validation

### Test Case 9.1: Email Validation
**Objective**: Verify email fields validated

**Steps**:
1. Open form with email field
2. Enter invalid email: `notanemail`
3. Try to submit
4. Verify error message
5. Enter valid email: `test@example.com`
6. Verify no error

**Expected Result**:
- ✅ Invalid emails rejected
- ✅ Valid emails accepted
- ✅ Error messages helpful

---

### Test Case 9.2: Number Validation
**Objective**: Verify number fields validated

**Steps**:
1. Navigate to form with number field (budget)
2. Enter text: `abcd`
3. Verify not accepted or error shown
4. Enter negative number: `-100`
5. Verify rejected
6. Enter valid number: `50000`
7. Verify accepted

**Expected Result**:
- ✅ Non-numbers rejected
- ✅ Negative numbers rejected
- ✅ Valid numbers accepted

---

### Test Case 9.3: Required Field Validation
**Objective**: Verify required fields enforced

**Steps**:
1. Open form with required fields
2. Leave required fields empty
3. Try to submit
4. Verify error for each empty required field
5. Fill required fields
6. Verify errors clear

**Expected Result**:
- ✅ Required fields enforced
- ✅ Clear error messages
- ✅ Cannot submit incomplete form

---

### Test Case 9.4: Character Length Validation
**Objective**: Verify character limits enforced

**Steps**:
1. Open form field with length limit
2. Try to enter text exceeding limit
3. Verify text cannot be entered or error shown
4. Enter text at/below limit
5. Verify accepted

**Expected Result**:
- ✅ Character limit enforced
- ✅ Cannot exceed maximum
- ✅ Clear feedback

---

## Test Scenario 10: Error Handling

### Test Case 10.1: 404 Error Page
**Objective**: Verify 404 page displays correctly

**Steps**:
1. Navigate to non-existent page: `/nonexistent`
2. Verify 404 error page displays
3. Verify error message clear: "Page not found"
4. Verify home/back navigation link present
5. Click link to return

**Expected Result**:
- ✅ 404 page shows
- ✅ Message clear
- ✅ Navigation back available

---

### Test Case 10.2: Server Error Handling
**Objective**: Verify app handles server errors gracefully

**Steps**:
1. Trigger server error (if possible)
2. Verify error message shown
3. Verify page doesn't crash
4. Verify user can navigate
5. Verify retry or home link present

**Expected Result**:
- ✅ Error displayed clearly
- ✅ App doesn't crash
- ✅ Navigation available
- ✅ User can recover

---

### Test Case 10.3: Network Error Handling
**Objective**: Verify app handles network errors

**Steps**:
1. Simulate network failure (DevTools > Network > Offline)
2. Try to load page
3. Verify error message
4. Turn network back on
5. Verify page loads

**Expected Result**:
- ✅ Offline error shown
- ✅ Graceful degradation
- ✅ Recovery works

---

## Test Scenario 11: Accessibility

### Test Case 11.1: Keyboard Navigation
**Objective**: Verify site navigable via keyboard

**Steps**:
1. Navigate website using only Tab key
2. Verify all clickable elements reachable
3. Verify focus visible (outline/highlight)
4. Use Enter to activate buttons
5. Use arrow keys in dropdowns

**Expected Result**:
- ✅ All elements keyboard accessible
- ✅ Focus visible
- ✅ Logical tab order
- ✅ Keyboard shortcuts work

---

### Test Case 11.2: Color Contrast
**Objective**: Verify sufficient color contrast

**Steps**:
1. Open accessibility checker (WebAIM Contrast)
2. Check all text against background
3. Verify WCAG AA compliance (4.5:1 for normal text, 3:1 for large text)
4. Check both light and dark modes

**Expected Result**:
- ✅ Normal text: 4.5:1 contrast minimum
- ✅ Large text: 3:1 contrast minimum
- ✅ Both light and dark modes compliant

---

### Test Case 11.3: Screen Reader Compatibility
**Objective**: Verify screen reader can access content

**Steps**:
1. Enable screen reader (NVDA, JAWS, or VoiceOver)
2. Navigate through page
3. Verify all text read correctly
4. Verify buttons/links identified as such
5. Verify form labels associated with inputs
6. Verify headings structure correct

**Expected Result**:
- ✅ All text readable
- ✅ Elements properly labeled
- ✅ Proper heading hierarchy
- ✅ No orphaned text

---

### Test Case 11.4: Focus Management
**Objective**: Verify focus management for modals/alerts

**Steps**:
1. Open a modal dialog
2. Verify focus moves to modal
3. Verify Tab stays within modal
4. Verify can close modal with Escape key
5. Verify focus returns to trigger element

**Expected Result**:
- ✅ Focus trapped in modal
- ✅ Escape closes modal
- ✅ Focus returns correctly

---

## Test Scenario 12: Performance

### Test Case 12.1: Page Load Time
**Objective**: Verify pages load within acceptable time

**Steps**:
1. Open DevTools Performance tab
2. Navigate to main pages
3. Measure load time for:
   - Dashboard
   - Projects list
   - Create project form
4. Record times in report

**Expected Result**:
- ✅ Dashboard: < 2 seconds
- ✅ Projects list: < 1.5 seconds
- ✅ Forms: < 1 second
- Mobile: < 3 seconds

---

### Test Case 12.2: Lighthouse Audit
**Objective**: Verify performance score

**Steps**:
1. Open DevTools
2. Go to Lighthouse tab
3. Run audit on mobile
4. Run audit on desktop
5. Check scores:
   - Performance
   - Accessibility
   - Best Practices
   - SEO

**Expected Result**:
- ✅ Performance: 80+
- ✅ Accessibility: 90+
- ✅ Best Practices: 80+
- ✅ SEO: 80+

---

### Test Case 12.3: Scroll Performance
**Objective**: Verify smooth scrolling (60 FPS)

**Steps**:
1. Open DevTools Performance
2. Record while scrolling through page
3. Verify no jank
4. Check frame rate: should be 60 FPS
5. Check for layout shifts

**Expected Result**:
- ✅ Smooth 60 FPS scrolling
- ✅ No jank or stutter
- ✅ No layout shifts

---

## Critical Test Cases - Priority 1

These are the most important tests to run:

### 🔴 Must Test
1. **Login/Logout** - Core functionality
2. **Create Project** - Main feature
3. **Edit Project** - Main feature
4. **Delete Project** - Destructive action
5. **Form Validation** - Data integrity
6. **Mobile View (375px)** - Responsive design
7. **Dark Mode Toggle** - UI consistency
8. **Touch Targets (44px)** - Mobile accessibility
9. **Data Persistence** - After refresh
10. **Error Handling** - User experience

---

## Test Execution Checklist

### Before Testing
- [ ] Environment set up (server running on `localhost:8000`)
- [ ] Test data created
- [ ] Mabl project created
- [ ] Browser compatibility confirmed
- [ ] Device list prepared

### During Testing
- [ ] Document any failures with screenshots
- [ ] Note browser/device details
- [ ] Record actual vs expected results
- [ ] Check console for errors
- [ ] Test with multiple browsers

### After Testing
- [ ] Review all test results
- [ ] Create bug reports for failures
- [ ] Run failed tests again
- [ ] Update test cases if needed
- [ ] Generate test report

---

## Test Data

### Default Test User
```
Username: admin
Password: admin123
Role: SUPERADMIN
```

### Test Project Data
```
Name: Test Project - [Date]
Description: This is a test project
Location: Test City
Budget: 100000
Start Date: 2026-02-17
End Date: 2026-12-31
Status: Active
```

### Test User Data
```
Username: testuser001
Email: testuser001@example.com
Password: TestPass123!
Role: User
```

---

## Browser Test Matrix

Run tests across these browsers/devices:

| Browser | Desktop | Mobile | Tablet |
|---------|---------|--------|--------|
| Chrome | ✓ | ✓ | ✓ |
| Firefox | ✓ | ✓ | ✓ |
| Safari | ✓ | ✓ | ✓ |
| Edge | ✓ | - | - |

---

## Device Test Matrix

| Device | Width | Height | DPI | Priority |
|--------|-------|--------|-----|----------|
| iPhone 12 | 390px | 844px | 2x | High |
| iPhone 14 Pro Max | 430px | 932px | 3x | High |
| Pixel 6 | 412px | 915px | 2.75x | High |
| iPad | 768px | 1024px | 2x | Medium |
| iPad Pro | 1024px | 1366px | 2x | Medium |
| Desktop | 1920px | 1080px | 1x | High |

---

**Status**: Ready for Mabl Test Creation
**Test Cases**: 50+
**Scenarios**: 12
**Priority**: All marked

