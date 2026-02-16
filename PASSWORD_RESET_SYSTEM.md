# InfraCore Password Reset OTP System

## Overview

Complete OTP (One-Time Password) based password reset system with email verification, rate limiting, and security best practices.

## Features

✅ **Security**
- 6-digit random OTP generation
- Bcrypt hashing of OTPs before database storage
- Rate limiting: 3 OTP requests per hour per user
- OTP expiry: 5 minutes
- Failed attempt tracking: 5 attempts max per OTP
- Password strength validation: minimum 8 characters

✅ **User Experience**
- 3-step wizard interface
- Dark/light mode toggle
- Password strength meter
- Real-time validation
- Clear error messages
- Email or username login

✅ **Email Integration**
- Gmail SMTP via app/utils/email.py
- Professional HTML email templates
- Automatic OTP delivery
- Error handling and logging

## Architecture

### Backend Components

#### 1. **Router: `app/routes/password_reset.py`**
Three main endpoints:

- `POST /forgot-password/send-otp`
  - Input: `{ "email": "user@example.com" }`
  - Validates user exists
  - Checks rate limit (3/hour)
  - Generates 6-digit OTP
  - Hashes with bcrypt
  - Sends email
  - Returns: `{ "message": "OTP sent" }`

- `POST /forgot-password/verify-otp`
  - Input: `{ "email": "user@example.com", "otp": "123456" }`
  - Validates OTP format (6 digits)
  - Checks expiry (5 min)
  - Verifies bcrypt hash
  - Tracks failed attempts (max 5)
  - Returns: `{ "message": "OTP verified" }`

- `POST /forgot-password/reset`
  - Input: `{ "email": "user@example.com", "new_password": "password123" }`
  - Validates OTP was verified first
  - Validates password strength (8+ chars)
  - Hashes password with bcrypt
  - Updates user record
  - Marks OTP as used
  - Returns: `{ "message": "Password reset successfully" }`

#### 2. **Model: `app/models/password_reset_otp.py`**
Database table for tracking OTPs:

```python
class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otp"
    
    id: int (primary key)
    email: str (user's email)
    otp_hash: str (bcrypt hash of OTP)
    expires_at: datetime (expiry time)
    attempts: int (failed attempts counter)
    verified_at: datetime (when OTP was verified)
    used_at: datetime (when OTP was used for reset)
    created_at: datetime (creation timestamp)
```

#### 3. **Email Service: `app/utils/email.py`**
SMTP integration for sending OTPs:

```python
send_email(
    to_email: str,
    subject: str,
    body: str,
    from_name: str = "InfraCore Support"
)
```

### Frontend Components

#### 1. **Template: `app/templates/forgot_password.html`**
Three-step wizard with modern UI/UX:

**Step 1: Enter Email/Username**
- Email or username input
- Send OTP button
- Error messages

**Step 2: Verify OTP**
- 6-digit OTP input field
- Numeric format only
- Attempt counter
- Back button

**Step 3: Reset Password**
- New password input
- Confirm password input
- Password strength meter (3 bars)
- Back button
- Reset button

**Dark Mode**
- CSS variables for theming
- localStorage persistence
- Smooth transitions

### Data Flow

```
┌─────────────────────────────────────────────────────┐
│ User clicks "Reset Password" on Login page          │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ Frontend: Forgot Password Page                      │
│ - Step 1: Enter email/username                      │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼ (POST /forgot-password/send-otp)
┌─────────────────────────────────────────────────────┐
│ Backend: send_otp()                                 │
│ 1. Verify user exists                               │
│ 2. Check rate limit (3/hour)                        │
│ 3. Generate 6-digit OTP                             │
│ 4. Hash with bcrypt                                 │
│ 5. Store in DB (expires in 5 min)                   │
│ 6. Send email with OTP                              │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ Email Sent via Gmail SMTP                           │
│ To: user@example.com                                │
│ Subject: InfraCore - Password Reset OTP             │
│ Body: Your OTP is [6-digit code]                    │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ Frontend: Step 2 - Verify OTP                       │
│ - User enters OTP from email                        │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼ (POST /forgot-password/verify-otp)
┌─────────────────────────────────────────────────────┐
│ Backend: verify_otp_endpoint()                      │
│ 1. Validate format (6 digits)                       │
│ 2. Check not expired                                │
│ 3. Check not already used                           │
│ 4. Compare with bcrypt hash                         │
│ 5. Mark verified_at timestamp                       │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ Frontend: Step 3 - Enter New Password               │
│ - Password strength meter (real-time)               │
│ - Confirm password validation                       │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼ (POST /forgot-password/reset)
┌─────────────────────────────────────────────────────┐
│ Backend: reset_password()                           │
│ 1. Verify OTP was marked verified                   │
│ 2. Validate password strength (8+ chars)            │
│ 3. Hash password with bcrypt                        │
│ 4. Update user.hashed_password                      │
│ 5. Mark OTP as used                                 │
│ 6. Commit transaction                               │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ Success: User redirected to Login page              │
│ Message: "Password reset successfully"              │
└─────────────────────────────────────────────────────┘
```

## Testing Guide

### Prerequisites
1. Server running: `python main.py` or `.venv\Scripts\python main.py`
2. Database initialized with seed data
3. Gmail SMTP credentials configured in `.env`:
   - `SMTP_HOST=smtp.gmail.com`
   - `SMTP_PORT=587`
   - `SMTP_USERNAME=your-email@gmail.com`
   - `SMTP_PASSWORD=your-app-password`

### Test Case 1: Successful Password Reset

**Setup:**
- Use an existing user: `admin` / existing password
- Have access to the user's email

**Steps:**
1. Go to `http://localhost:8000/forgot-password`
2. Enter email or username: `admin`
3. Click "Send OTP"
   - ✓ Should see: "OTP sent successfully"
   - ✓ Check email for OTP
4. Enter OTP in Step 2
5. Click "Verify OTP"
   - ✓ Should see: "OTP verified successfully"
6. Enter new password (min 8 chars)
7. Confirm password
8. Click "Reset Password"
   - ✓ Should see: "Password reset successfully"
   - ✓ Redirected to login after 2 seconds
9. Login with new password
   - ✓ Should successfully login

**Expected Database State:**
- `password_reset_otp` table has new record
- `verified_at` is set to current timestamp
- `used_at` is set to current timestamp
- User's `hashed_password` is updated

### Test Case 2: Rate Limiting

**Steps:**
1. Try sending OTP 4 times within 1 hour
2. First 3 should succeed
3. 4th attempt should fail with:
   - ✓ Error: "Too many OTP requests. Please try again in an hour."
   - ✓ HTTP 429 (Too Many Requests)

### Test Case 3: OTP Expiry

**Steps:**
1. Send OTP
2. Wait 5+ minutes
3. Try to verify OTP
   - ✓ Should fail with: "OTP has expired. Please request a new one."

### Test Case 4: Invalid OTP

**Steps:**
1. Send OTP
2. Try entering wrong OTP (5 times)
3. After 5 attempts:
   - ✓ Error: "Too many failed attempts. Please request a new OTP."
4. 6th attempt should also fail

### Test Case 5: Weak Password

**Steps:**
1. Complete OTP verification
2. Try entering password shorter than 8 chars
3. Should show error (with strength meter at weak level)
4. Should not allow submission

### Test Case 6: Dark Mode

**Steps:**
1. Go to forgot password page
2. Click moon icon (top right)
   - ✓ Page switches to dark mode
3. Refresh page
   - ✓ Dark mode persists (localStorage)
4. Click sun icon
   - ✓ Switches to light mode
5. Refresh page
   - ✓ Light mode persists

### Test Case 7: Email Not Found

**Steps:**
1. Enter non-existent email
2. Click "Send OTP"
   - ✓ Should still say "If an account exists, an OTP has been sent"
   - ✓ Security: doesn't reveal if user exists

### Test Case 8: OTP Already Used

**Steps:**
1. Send OTP and verify
2. Reset password successfully
3. Try using same OTP again (if not expired)
   - ✓ Error: "OTP has already been used"

## Database Queries

### Check OTP Records
```sql
SELECT * FROM password_reset_otp 
ORDER BY created_at DESC 
LIMIT 10;
```

### Check Failed Attempts
```sql
SELECT email, attempts, created_at 
FROM password_reset_otp 
WHERE attempts > 0 
ORDER BY created_at DESC;
```

### Check Rate Limiting
```sql
SELECT email, COUNT(*) as requests 
FROM password_reset_otp 
WHERE created_at > datetime('now', '-1 hour')
GROUP BY email 
HAVING COUNT(*) >= 3;
```

### Cleanup Expired OTPs
```sql
DELETE FROM password_reset_otp 
WHERE expires_at < datetime('now');
```

## Configuration

### Environment Variables (`.env`)

```env
# Gmail SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=InfraCore Support

# Database
DATABASE_URL=sqlite:///./infra.db
```

### Email Template Variables

The email template uses:
- `{otp}` - Formatted 6-digit OTP
- `{user_name}` - User's name
- `{minutes}` - OTP validity (5 min)

## Security Considerations

✅ **Implemented**
- OTP hashing with bcrypt (never stored in plain text)
- Rate limiting per user (3/hour)
- Attempt counting (max 5 failures)
- OTP expiry (5 minutes)
- Password strength validation
- User existence not revealed
- HTTPS recommended for production
- Session-based security

⚠️ **Production Recommendations**
- Use HTTPS/TLS for all API calls
- Store SMTP credentials in secure vault
- Move from SQLite to PostgreSQL/MySQL
- Add Redis for distributed rate limiting
- Implement IP-based rate limiting as backup
- Add SMS OTP as alternative to email
- Monitor suspicious activity (multiple requests)
- Regular security audits

## Troubleshooting

### Email Not Sending

**Check:**
1. Gmail credentials in `.env` are correct
2. Gmail app password (not regular password)
3. Server logs for SMTP errors
4. Gmail security settings allow "Less secure app access"

**Debug:**
```python
# Test email sending
from app.utils.email import send_email
send_email(
    to_email="test@example.com",
    subject="Test",
    body="Testing email functionality"
)
```

### OTP Not Received

**Check:**
1. Email sent successfully (check server logs)
2. Check spam/junk folder
3. Correct email address registered for user
4. Email not been deleted during OTP creation

### Password Reset Fails

**Check:**
1. OTP was verified (check `verified_at` in DB)
2. OTP not already used (check `used_at`)
3. OTP not expired
4. Password meets requirements (8+ chars)

### Rate Limiting Issues

**Check:**
1. User's previous OTP requests: `SELECT * FROM password_reset_otp WHERE email='user@example.com' AND created_at > datetime('now', '-1 hour')`
2. Clear old OTPs: Manual deletion from database
3. Restart server to reset in-memory counters (if applicable)

## API Response Examples

### Success: Send OTP
```json
{
  "message": "OTP sent successfully. Please check your email."
}
```

### Error: Rate Limit
```json
{
  "error": "Too many OTP requests. Please try again in an hour."
}
```

### Error: Invalid OTP
```json
{
  "error": "Invalid OTP. 3 attempts remaining."
}
```

### Success: Password Reset
```json
{
  "message": "Password reset successfully. You can now login with your new password."
}
```

## Files Modified/Created

1. ✅ Created: `app/routes/password_reset.py` (308 lines)
2. ✅ Updated: `app/main.py` (added router import and registration)
3. ✅ Updated: `app/templates/forgot_password.html` (changed API content-type to JSON)
4. ✅ Existing: `app/models/password_reset_otp.py` (uses existing model)
5. ✅ Existing: `app/utils/email.py` (uses existing SMTP service)

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2025-02-14 | 1.0 | Initial OTP password reset system |
| | | - 3-step wizard UI |
| | | - Rate limiting (3/hour) |
| | | - Email OTP delivery |
| | | - Bcrypt hashing |
| | | - Dark/light mode |

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review server logs: `tail -f` on app output
3. Check database directly for debugging
4. Verify SMTP credentials in `.env`
