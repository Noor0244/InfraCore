# OTP Password Reset (InfraCore)

This project uses a 6-digit OTP flow for password resets. No links are sent.

## SMTP Configuration
Set these environment variables:
- SMTP_HOST
- SMTP_PORT (default: 587)
- SMTP_USER
- SMTP_PASS
- SMTP_FROM (optional)
- SMTP_TLS (true/false, default true)

## Endpoints
- POST /forgot-password/send-otp (email)
- POST /forgot-password/verify-otp (email + otp)
- POST /forgot-password/reset (email + new password)

## OTP Rules
- 6-digit secure random code
- Stored as hash
- Expires in 10 minutes
- Single-use
- Tracks attempts (max 5)
- Responses do not reveal if email exists
