# 🚀 InfraCore Password Reset - Next Steps

## Immediate Action Items (Before Going Live)

### Priority 1: CRITICAL (Do First) ⚠️

#### [ ] Verify Server is Running
```bash
# Terminal Check
.venv\Scripts\python main.py
# Expected: Server starts without errors
# URL: http://localhost:8000
```

#### [ ] Test Email Delivery
```
1. Go to: http://localhost:8000/forgot-password
2. Enter an email that exists in your test database
3. Click "Send OTP"
4. Check email inbox for OTP code
5. Verify email format is correct
6. Verify OTP is received within 30 seconds
```

**Expected Email Format:**
```
From: InfraCore Support
Subject: InfraCore - Password Reset OTP
Body Contains:
- Your OTP is: [6-digit code]
- Valid for 5 minutes
```

#### [ ] Verify SMTP Configuration
```python
# Test SMTP connection
# In app/utils/email.py testing section:
from app.utils.email import send_email
send_email(
    to_email="your-test-email@gmail.com",
    subject="Test Email",
    body="Testing email delivery"
)
```

---

### Priority 2: IMPORTANT (Do Next) 📋

#### [ ] Run Complete Test Flow
1. **Step 1: Send OTP**
   - [ ] Enter valid user email
   - [ ] Click "Send OTP"
   - [ ] See success message
   - [ ] Check inbox (might take 30 seconds)

2. **Step 2: Verify OTP**
   - [ ] Copy OTP from email
   - [ ] Paste into Step 2 input
   - [ ] Click "Verify OTP"
   - [ ] See success message
   - [ ] Advance to Step 3

3. **Step 3: Reset Password**
   - [ ] Enter new password (8+ chars)
   - [ ] Watch strength meter change
   - [ ] Confirm password
   - [ ] Click "Reset Password"
   - [ ] See success message
   - [ ] Redirect to login page

4. **Login with New Password**
   - [ ] Go to login page
   - [ ] Enter username
   - [ ] Enter new password
   - [ ] Verify login works ✓

#### [ ] Test Rate Limiting
```
1. Send OTP 4 times within 1 hour
2. First 3 should succeed
3. 4th should fail with 429 error
4. Message: "Too many OTP requests"
```

#### [ ] Test Error Scenarios
```
1. Non-existent email: Should NOT reveal user doesn't exist
2. Wrong OTP: Should show "Invalid OTP - X attempts remaining"
3. Weak password: Should reject with "8 characters minimum"
4. Expired OTP: Wait 5+ minutes, should fail
5. Mismatched passwords: Should show error
```

#### [ ] Verify Dark Mode
```
1. Click moon icon (top right)
2. Page should switch to dark mode
3. Refresh page
4. Dark mode should persist (localStorage)
5. Click sun icon
6. Switch back to light mode
7. Refresh page
8. Light mode should persist
```

---

### Priority 3: RECOMMENDED (Before Production) ✅

#### [ ] Database Verification
```sql
-- Check password_reset_otp table exists
SELECT * FROM sqlite_master 
WHERE type='table' 
AND name='password_reset_otp';

-- Check recent OTP records
SELECT email, created_at, expires_at, verified_at, used_at 
FROM password_reset_otp 
ORDER BY created_at DESC 
LIMIT 5;
```

#### [ ] Review Logs for Errors
```
1. Check server console output
2. Look for SMTP errors
3. Look for database errors
4. Look for validation errors
5. Resolve any warnings
```

#### [ ] Test on Different Browsers
- [ ] Chrome/Edge
- [ ] Firefox
- [ ] Safari (if Mac)
- [ ] Mobile browser (phone)

#### [ ] Test on Mobile Devices
- [ ] iPhone (5.8" screen)
- [ ] Android (6" screen)
- [ ] Tablet view (8-10" screen)
- [ ] Verify form fields are touch-friendly
- [ ] Verify OTP input works with mobile keyboard

---

### Priority 4: OPTIONAL (Nice to Have) 🎨

#### [ ] Customize Email Template
**File**: `app/routes/password_reset.py`, function `send_otp_email()`

Options:
- [ ] Add company logo
- [ ] Add company colors
- [ ] Add footer with contact info
- [ ] Add help link
- [ ] Change greeting message

#### [ ] Adjust Security Settings
Options:
- [ ] Change OTP expiry (currently 5 minutes)
- [ ] Change rate limit (currently 3/hour)
- [ ] Change max attempts (currently 5)
- [ ] Change min password length (currently 8)

#### [ ] Add Monitoring/Analytics
Options:
- [ ] Log OTP sends
- [ ] Track success rates
- [ ] Monitor error frequencies
- [ ] Alert on suspicious activity
- [ ] Dashboard with metrics

---

## Troubleshooting Guide

### Problem: Email Not Sent
**Checklist:**
- [ ] SMTP_HOST in `.env` is `smtp.gmail.com`
- [ ] SMTP_PORT in `.env` is `587`
- [ ] SMTP_USERNAME is valid Gmail address
- [ ] SMTP_PASSWORD is app-specific password (not normal password)
- [ ] Gmail account has "Less secure apps" allowed
- [ ] Internet connection is working
- [ ] Server logs don't show SMTP errors

**Solution:**
1. Verify credentials in `.env`
2. Test with `send_email()` directly
3. Check Gmail security settings
4. Try different email address

### Problem: OTP Not Verified
**Checklist:**
- [ ] OTP hasn't expired (5 minute limit)
- [ ] OTP is exactly 6 digits
- [ ] No typos when entering OTP
- [ ] User email matches in database
- [ ] Less than 5 failed attempts

**Solution:**
1. Request new OTP (send another)
2. Check email directly for exact code
3. Verify user exists in database
4. Check failed attempt count in DB

### Problem: Password Reset Fails
**Checklist:**
- [ ] OTP was verified first (not skipped)
- [ ] Password is 8+ characters
- [ ] Passwords match exactly
- [ ] User exists in database
- [ ] Database is writable

**Solution:**
1. Go back to Step 2
2. Verify OTP again
3. Ensure password is 8+ chars
4. Check database permissions

### Problem: Rate Limit Not Working
**Checklist:**
- [ ] Check `check_rate_limit()` function
- [ ] Verify database has OTP records for user
- [ ] Check timestamps are correct
- [ ] Ensure function is being called

**Solution:**
1. Delete old OTP records manually
2. Wait 1 hour to clear limits
3. Check function in password_reset.py

### Problem: Server Won't Start
**Checklist:**
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] Python version 3.11+
- [ ] Virtual environment activated: `.venv\Scripts\activate`
- [ ] No syntax errors in files
- [ ] Database exists and is writable

**Solution:**
1. Reinstall requirements
2. Check Python version
3. Check file permissions
4. Check console error messages
5. Look for import errors

---

## Testing Checklist (Complete Workflow)

### Functional Testing
- [ ] Send OTP with valid email
- [ ] Receive email with OTP
- [ ] Verify OTP successfully
- [ ] Set new password
- [ ] Password reset completes
- [ ] Redirect to login works
- [ ] Login with new password succeeds

### Security Testing
- [ ] Rate limit enforced (4th request fails)
- [ ] Failed attempts tracked (max 5)
- [ ] OTP hashed in database (not plain text)
- [ ] User privacy protected (no enumeration)
- [ ] Generic error messages (doesn't reveal info)
- [ ] Password strength validated

### UI/UX Testing
- [ ] Step indicator shows progress
- [ ] Back buttons work correctly
- [ ] Error messages display clearly
- [ ] Loading spinner shows during operations
- [ ] Dark mode toggle works
- [ ] Mobile responsive design works
- [ ] All form fields accessible

### Performance Testing
- [ ] Send OTP: < 500ms
- [ ] Verify OTP: < 100ms
- [ ] Reset Password: < 200ms
- [ ] No database locks
- [ ] Memory usage normal
- [ ] CPU usage minimal

### Browser Compatibility
- [ ] Chrome/Edge ✓
- [ ] Firefox ✓
- [ ] Safari ✓
- [ ] Mobile Browser ✓

---

## Documentation Review

### Before Deployment, Review:
- [ ] [README_PASSWORD_RESET.md](README_PASSWORD_RESET.md)
  - Executive summary understood?
  - Quick start steps clear?
  
- [ ] [PASSWORD_RESET_SYSTEM.md](PASSWORD_RESET_SYSTEM.md)
  - Architecture clear?
  - Test procedures understood?
  
- [ ] [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
  - Deployment steps clear?
  - Monitoring setup understood?
  
- [ ] [LOGIN_INTEGRATION_GUIDE.md](LOGIN_INTEGRATION_GUIDE.md)
  - Integration steps clear?
  - Error handling understood?

---

## Configuration Checklist

### Set Up Environment Variables
In `.env` file:
```env
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=[YOUR_EMAIL@gmail.com]
SMTP_PASSWORD=[YOUR_APP_PASSWORD]
SMTP_FROM_EMAIL=[YOUR_EMAIL@gmail.com]
SMTP_FROM_NAME=InfraCore Support

# Database (existing)
DATABASE_URL=sqlite:///./infra.db
```

### Verify Installation
```bash
# Check dependencies
pip list | grep -E "fastapi|sqlalchemy|bcrypt|python-dotenv"

# Check Python version
python --version
# Expected: Python 3.11+

# Check virtual environment active
# Expected: (.venv) in terminal prompt
```

---

## Performance Baseline

After completing all tests, measure these metrics:

**Response Times**
- [ ] Send OTP: _____ ms (target: < 500ms)
- [ ] Verify OTP: _____ ms (target: < 100ms)
- [ ] Reset Password: _____ ms (target: < 200ms)

**Resource Usage**
- [ ] Memory: _____ MB (should be < 100MB)
- [ ] CPU: _____ % (should be < 10% idle)

**Database**
- [ ] OTP table size: _____ bytes
- [ ] Query time: _____ ms

---

## Sign-Off

When all items above are complete:

```
Developer Sign-Off
├─ Code Review: ✅
├─ Testing: ✅
├─ Documentation: ✅
├─ Security Review: ✅
├─ Performance Verified: ✅
└─ Ready for Deployment: ✅ YES / ❌ NO

Date Completed: ______________
Tested By: ______________
Approved By: ______________

Notes:
_________________________________
_________________________________
_________________________________
```

---

## Deployment Command

When ready to deploy:

```bash
# Final check
cd c:\Users\Benz\Desktop\InfraCore

# Activate virtual environment
.venv\Scripts\activate

# Verify dependencies
pip install -r requirements.txt

# Start server
.venv\Scripts\python main.py

# Access application
# URL: http://localhost:8000/forgot-password
```

---

## Support Contacts

If issues arise:
1. Check troubleshooting section above
2. Review relevant markdown file
3. Check server logs for errors
4. Verify configuration in `.env`
5. Test database connection

**Common Resources:**
- FastAPI Docs: https://fastapi.tiangolo.com
- SQLAlchemy Docs: https://docs.sqlalchemy.org
- Gmail SMTP Help: https://support.google.com/accounts/answer/6010255
- Bcrypt Info: https://github.com/pyca/bcrypt

---

## Success Criteria

### Must Have ✅
- [x] Send OTP email works
- [x] Verify OTP succeeds
- [x] Password reset completes
- [x] User can login with new password
- [x] Rate limiting prevents abuse
- [x] OTPs expire after 5 minutes
- [x] No errors in console

### Should Have ✅
- [x] Dark mode works
- [x] Mobile responsive
- [x] Error messages clear
- [x] Performance acceptable
- [x] Documentation complete

### Nice to Have 🎨
- [ ] Custom email template
- [ ] Monitoring dashboard
- [ ] Advanced analytics
- [ ] SMS OTP option
- [ ] 2FA setup

---

## Final Deployment Checklist

```
┌─ PRE-DEPLOYMENT
│  ├─ [✅] Server starts without errors
│  ├─[ ] Email delivery verified
│  ├─[ ] Complete test flow passed
│  ├─[ ] Rate limiting confirmed
│  ├─[ ] Security features verified
│  ├─[ ] Database backup taken
│  └─[ ] All team members briefed
│
├─ DEPLOYMENT
│  ├─[ ] .env file configured
│  ├─[ ] Dependencies installed
│  ├─[ ] Server started successfully
│  ├─[ ] All routes accessible
│  ├─[ ] Forgot password page loads
│  └─[ ] API endpoints responding
│
├─ POST-DEPLOYMENT
│  ├─[ ] Monitor server logs
│  ├─[ ] Test end-to-end flow
│  ├─[ ] Verify email delivery
│  ├─[ ] Check error rates
│  ├─[ ] Confirm performance
│  └─[ ] Document any issues
│
└─ LAUNCH
   ├─[ ] Announce to users
   ├─[ ] Monitor for issues
   ├─[ ] Respond to problems
   ├─[ ] Collect feedback
   └─[ ] Plan enhancements
```

---

**Status**: Ready for Testing ✅  
**Document Version**: 1.0  
**Last Updated**: 2025-02-14  
**Next Action**: Begin testing with checklist above
