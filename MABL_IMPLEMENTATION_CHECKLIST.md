# ✅ Mabl Test Implementation Checklist

## 📋 Complete Mabl Setup Checklist

### Phase 1: Account Setup (30 minutes)

- [ ] **Create Mabl Account**
  - Go to https://www.mabl.com
  - Sign up (free tier available)
  - Create organization
  - Verify email

- [ ] **Install Browser Extension**
  - Go to Mabl Dashboard
  - Settings → Download Recorder
  - Install Chrome/Firefox extension
  - Login to extension

- [ ] **Create App in Mabl**
  - Dashboard → Create App
  - Name: `InfraCore`
  - URL: `http://localhost:8000`
  - Save

- [ ] **Verify Server Running**
  - Check: `http://localhost:8000/login`
  - Should see login page
  - No errors in console

---

### Phase 2: Create Core Tests (2-3 hours)

#### 🔐 Authentication Tests (30 minutes)

- [ ] **TC-001: Login - Valid**
  - [ ] Create journey named `TC-001-Login-Valid`
  - [ ] Record: Username + Password + Click Login
  - [ ] Add assertions: Page title, Projects visible
  - [ ] Save & Test run successful

- [ ] **TC-002: Login - Invalid**
  - [ ] Create journey `TC-002-Login-Invalid`
  - [ ] Use invalid credentials
  - [ ] Assert error message appears
  - [ ] Save & Test run

- [ ] **TC-003: Empty Fields**
  - [ ] Journey `TC-003-Empty-Fields`
  - [ ] Try empty username/password
  - [ ] Assert validation messages
  - [ ] Save & Test run

- [ ] **TC-004: Logout**
  - [ ] Journey `TC-004-Logout`
  - [ ] Login first (or use prerequisite)
  - [ ] Click logout
  - [ ] Assert redirect to login
  - [ ] Save & Test run

#### 📋 Project Management (40 minutes)

- [ ] **TC-010: View Projects**
  - [ ] Journey `TC-010-View-Projects`
  - [ ] Navigate to /projects
  - [ ] Assert table visible
  - [ ] Assert columns present
  - [ ] Save & Test run

- [ ] **TC-011: Create Project**
  - [ ] Journey `TC-011-Create-Project`
  - [ ] Fill form with test data
  - [ ] Submit form
  - [ ] Assert in projects list
  - [ ] Create variables for reusable data
  - [ ] Save & Test run

- [ ] **TC-012: Edit Project**
  - [ ] Journey `TC-012-Edit-Project`
  - [ ] Find project, click edit
  - [ ] Modify fields
  - [ ] Save changes
  - [ ] Assert changes visible
  - [ ] Save & Test run

- [ ] **TC-013: Delete Project**
  - [ ] Journey `TC-013-Delete-Project`
  - [ ] Click delete
  - [ ] Confirm deletion
  - [ ] Assert removed from list
  - [ ] Save & Test run

- [ ] **TC-014: Archive Project**
  - [ ] Journey `TC-014-Archive-Project`
  - [ ] Click archive button
  - [ ] Verify in archived list
  - [ ] Save & Test run

- [ ] **TC-015: Unarchive Project**
  - [ ] Journey `TC-015-Unarchive-Project`
  - [ ] View archived projects
  - [ ] Restore archived project
  - [ ] Verify in active list
  - [ ] Save & Test run

#### 📱 Responsive Design (45 minutes)

- [ ] **TC-020: Mobile Phone View**
  - [ ] Journey `TC-020-Mobile-Phone`
  - [ ] Set device: iPhone 12 (375px)
  - [ ] Test navigation on mobile
  - [ ] Assert no horizontal scroll
  - [ ] Assert touch targets visible
  - [ ] Assert sidebar menu works
  - [ ] Save & Test run

- [ ] **TC-021: Tablet View**
  - [ ] Journey `TC-021-Tablet`
  - [ ] Set device: iPad (768px)
  - [ ] Navigate pages
  - [ ] Assert 2-column layout
  - [ ] Assert sidebar visible
  - [ ] Save & Test run

- [ ] **TC-022: Desktop View**
  - [ ] Journey `TC-022-Desktop`
  - [ ] Set device: 1920px width
  - [ ] Navigate full site
  - [ ] Assert proper desktop layout
  - [ ] Assert all features available
  - [ ] Save & Test run

#### 🎨 Theme & UI (20 minutes)

- [ ] **TC-030: Dark Mode Toggle**
  - [ ] Journey `TC-030-Dark-Mode`
  - [ ] Click dark mode button
  - [ ] Assert colors change
  - [ ] Refresh page
  - [ ] Assert dark mode persists
  - [ ] Add visual assertions
  - [ ] Save & Test run

- [ ] **TC-031: Light Mode**
  - [ ] Journey `TC-031-Light-Mode`
  - [ ] Toggle to light mode
  - [ ] Assert colors light
  - [ ] Check text contrast
  - [ ] Refresh and verify persistence
  - [ ] Save & Test run

#### ✔️ Forms & Validation (20 minutes)

- [ ] **TC-040: Form Validation**
  - [ ] Journey `TC-040-Form-Validation`
  - [ ] Submit empty form
  - [ ] Assert validation messages
  - [ ] Fill required fields
  - [ ] Assert errors clear
  - [ ] Submit complete form
  - [ ] Assert success
  - [ ] Save & Test run

---

### Phase 3: Create Test Plans (20 minutes)

- [ ] **Plan: Smoke Tests (Critical)**
  - [ ] Include: TC-001, TC-010, TC-011, TC-020
  - [ ] Description: `Core functionality tests`
  - [ ] Save

- [ ] **Plan: Authentication**
  - [ ] Include: TC-001, TC-002, TC-003, TC-004
  - [ ] Save

- [ ] **Plan: Projects**
  - [ ] Include: TC-010 through TC-015
  - [ ] Save

- [ ] **Plan: Responsive**
  - [ ] Include: TC-020, TC-021, TC-022
  - [ ] Save

- [ ] **Plan: All Tests**
  - [ ] Include: All journeys
  - [ ] Save

---

### Phase 4: Configuration (30 minutes)

- [ ] **Create Variables**
  - [ ] `admin_username` = `admin`
  - [ ] `admin_password` = `admin123`
  - [ ] `test_project_name` = `Test Project {{today}}`
  - [ ] `test_email` = `testuser@example.com`

- [ ] **Configure Environments**
  - [ ] Development: `http://localhost:8000`
  - [ ] (Optional) Staging: `http://staging.example.com`
  - [ ] (Optional) Production: `http://example.com`

- [ ] **Set Run Preferences**
  - [ ] Default browser: Chrome
  - [ ] Default device: Desktop
  - [ ] Report format: Detailed
  - [ ] Retry failed tests: Enabled

---

### Phase 5: Initial Test Runs (1 hour)

- [ ] **Run All Smoke Tests**
  - [ ] Execute: Smoke Tests plan
  - [ ] Review results
  - [ ] Fix any failures
  - [ ] Document issues
  - [ ] Success rate: ≥ 90%

- [ ] **Run Authentication Plan**
  - [ ] Execute tests
  - [ ] Verify login flows
  - [ ] Success rate: 100%

- [ ] **Run Projects Plan**
  - [ ] Execute tests
  - [ ] Verify CRUD operations
  - [ ] Success rate: ≥ 95%

- [ ] **Run Responsive Plan**
  - [ ] Execute tests
  - [ ] Verify mobile/tablet/desktop
  - [ ] Success rate: 100%

- [ ] **Run All Tests**
  - [ ] Full suite execution
  - [ ] Generate report
  - [ ] Success rate: ≥ 85%

---

### Phase 6: CI/CD Integration (Optional - 30 minutes)

- [ ] **GitHub Actions Setup**
  - [ ] Get Mabl API key
  - [ ] Add to GitHub secrets: `MABL_API_KEY`
  - [ ] Create `.github/workflows/mabl-tests.yml`
  - [ ] Configure workflow
  - [ ] Test: Push to trigger tests
  - [ ] Verify: Tests run in CI

- [ ] **Jenkins Setup** (if using Jenkins)
  - [ ] Get API key
  - [ ] Create pipeline job
  - [ ] Configure Mabl integration
  - [ ] Test execution
  - [ ] Verify results in Jenkins

- [ ] **Schedule Automatic Tests**
  - [ ] In Mabl: Plans → Schedule
  - [ ] Set daily run: 2:00 AM
  - [ ] Set weekly run: Sunday 2:00 AM
  - [ ] Enable email reports

---

### Phase 7: Documentation (20 minutes)

- [ ] **Create Test Index**
  - [ ] List all 10+ test cases
  - [ ] Include test ID, name, purpose
  - [ ] Link to test runs

- [ ] **Document Test Data**
  - [ ] Test users: admin, testuser
  - [ ] Test projects: Test Project [date]
  - [ ] Test credentials

- [ ] **Document Failures**
  - [ ] If tests fail, document:
    - [ ] Which test failed
    - [ ] What was expected
    - [ ] What actually happened
    - [ ] Screenshot
    - [ ] How to fix

- [ ] **Create Runbook**
  - [ ] How to run tests manually
  - [ ] How to run in CI/CD
  - [ ] How to add new tests
  - [ ] How to troubleshoot failures

---

### Phase 8: Maintenance (Ongoing)

- [ ] **Weekly Review**
  - [ ] [ ] Check test results
  - [ ] [ ] Review any failures
  - [ ] [ ] Update tests if UI changed
  - [ ] [ ] Document findings

- [ ] **Monthly Expansion**
  - [ ] [ ] Add 5-10 new tests
  - [ ] [ ] Cover new features
  - [ ] [ ] Expand edge cases
  - [ ] [ ] Improve coverage

- [ ] **Quarterly Optimization**
  - [ ] [ ] Review test effectiveness
  - [ ] [ ] Remove redundant tests
  - [ ] [ ] Update documentation
  - [ ] [ ] Plan next phase

---

## 📊 Progress Tracking

### Quick Stats
- **Tests Created**: ___/40
- **Tests Passing**: ___/40
- **Pass Rate**: ___%
- **Time Invested**: ___ hours
- **Last Updated**: ___

### Detailed Breakdown

| Category | Count | Status | Notes |
|----------|-------|--------|-------|
| Authentication | 4 | ⬜ | |
| Project Mgmt | 6 | ⬜ | |
| Responsive | 3 | ⬜ | |
| Theme/UI | 2 | ⬜ | |
| Forms | 2 | ⬜ | |
| **TOTAL** | **17** | | |

### Legend:
- ⬜ Not Started
- 🟨 In Progress  
- ✅ Complete
- ❌ Failed (needs fix)

---

## 🎯 Success Criteria

By end of this implementation, you should have:

- ✅ 15+ working test cases
- ✅ 90%+ pass rate initially
- ✅ 5+ test plans
- ✅ Automated daily runs scheduled
- ✅ CI/CD pipeline integrated
- ✅ Complete test documentation
- ✅ Team trained on test execution
- ✅ Regression test coverage for critical flows

---

## 💡 Pro Tips

### Time Savers:
1. Use variables instead of hardcoding data
2. Create tests during development, not after
3. Group related assertions together
4. Use visual recording for complex interactions
5. Keep test names descriptive and consistent

### Common Mistakes to Avoid:
1. ❌ Don't use dynamic IDs in selectors (browsers change them)
2. ❌ Don't rely on page element order (can change with updates)
3. ❌ Don't create super-long tests (break into multiple tests)
4. ❌ Don't forget to wait for AJAX/dynamic content
5. ❌ Don't ignore maintenance (update when UI changes)

### Best Practices:
1. ✅ One assertion per step when possible
2. ✅ Use wait statements for dynamic content
3. ✅ Test happy path AND error cases
4. ✅ Keep tests independent (can run in any order)
5. ✅ Review and update monthly

---

## 📞 Troubleshooting

### Test Won't Record
**Solution:** 
- Verify server is running: `http://localhost:8000`
- Check browser extension is logged in
- Clear browser cache
- Try different browser

### Element Not Found
**Solution:**
- Re-record the step
- Inspect element to verify selector
- Use more specific CSS selector
- Update to use element name/label

### Timeout Issues
**Solution:**
- Increase wait timeout (set to 15 seconds)
- Add explicit wait step before element
- Check if element is behind modal/overlay
- Verify element is visible in browser

### Variables Not Working
**Solution:**
- Check variable name is spelled correctly
- Verify variable is in curly brackets: `{{var}}`
- Make sure variable is defined in Settings
- Test variable replacement in simple test first

---

## 📞 Resources

### Mabl Documentation
- Official Docs: https://docs.mabl.com/
- Video Tutorials: https://www.mabl.com/academy
- API Reference: https://api.mabl.com/docs

### Quick Links
- Mabl Dashboard: https://app.mabl.com
- Mabl Support: support@mabl.com
- Community Forum: https://community.mabl.com

### Your InfraCore Resources
- Complete Test Cases: `MABL_TEST_CASES.md`
- Setup Guide: `MABL_SETUP_GUIDE.md`
- Quick Start: `MABL_QUICK_START.md`

---

## ✅ Next Steps

1. **This Week**: Complete Phase 1 (Account Setup) ✨
2. **Next Week**: Complete Phase 2a (Authentication Tests) 🔐
3. **Week 3**: Complete Phase 2b-2c (Project & Responsive) 📱
4. **Week 4**: Complete Phases 3-5 (Plans & Runs) 🎯
5. **Week 5**: Complete Phase 6 (CI/CD Integration) 🚀
6. **Ongoing**: Phase 7 & 8 (Maintenance) 🔧

---

**Happy Testing! 🚀**

Questions? Check the detailed guides:
- Need detailed setup? → `MABL_SETUP_GUIDE.md`
- Need test scenarios? → `MABL_TEST_CASES.md`
- Need quick examples? → `MABL_QUICK_START.md`

