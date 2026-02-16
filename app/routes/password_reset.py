# app/routes/password_reset.py
# --------------------------------------------------
# Password Reset OTP System
# --------------------------------------------------
# Features:
# - Generate 6-digit OTP
# - Store hashed OTP in database with expiry (5 min)
# - Send OTP via Gmail SMTP
# - Rate limiting (3 requests per hour per user)
# - Proper JSON responses with error handling
# --------------------------------------------------

from __future__ import annotations

import os
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any

import bcrypt
from fastapi import APIRouter, Depends, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.session import get_db
from app.models.user import User
from app.models.password_reset_otp import PasswordResetOTP
from app.utils.email import send_email, EmailSendError

router = APIRouter(prefix="/forgot-password", tags=["Password Reset"])


# =====================================================
# REQUEST SCHEMAS
# =====================================================

class SendOtpRequest(BaseModel):
    email: str


class VerifyOtpRequest(BaseModel):
    email: str
    otp: str


class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str


# =====================================================
# HELPERS
# =====================================================

def generate_otp() -> str:
    """Generate a random 6-digit OTP."""
    return "".join(random.choices(string.digits, k=6))


def hash_otp(otp: str) -> str:
    """Hash OTP using bcrypt."""
    return bcrypt.hashpw(otp.encode(), bcrypt.gensalt()).decode()


def verify_otp(otp: str, otp_hash: str) -> bool:
    """Verify OTP against hash."""
    try:
        return bcrypt.checkpw(otp.encode(), otp_hash.encode())
    except Exception:
        return False


def get_user_by_email_or_username(email_or_username: str, db: Session) -> User | None:
    """Get user by email or username."""
    return db.query(User).filter(
        or_(
            User.email == email_or_username,
            User.username == email_or_username
        )
    ).first()


def check_rate_limit(user_id: int, db: Session) -> tuple[bool, str]:
    """
    Check if user has exceeded rate limit (3 requests per hour).
    Returns: (is_allowed: bool, message: str)
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    # Get user email for the query
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False, "User not found"
    
    recent_requests = db.query(PasswordResetOTP).filter(
        and_(
            PasswordResetOTP.email == user.email,
            PasswordResetOTP.created_at >= one_hour_ago
        )
    ).count()
    
    if recent_requests >= 3:
        return False, "Too many OTP requests. Please try again in an hour."
    
    return True, ""


def cleanup_expired_otps(db: Session) -> None:
    """Delete expired OTPs."""
    db.query(PasswordResetOTP).filter(
        PasswordResetOTP.expires_at < datetime.utcnow()
    ).delete()
    db.commit()


def send_otp_email(to_email: str, otp: str, user_name: str = None) -> bool:
    """Send OTP via email."""
    subject = "InfraCore - Password Reset OTP"
    
    body = f"""Hello {user_name or 'User'},

Your One-Time Password (OTP) for password reset is:

    {otp}

This OTP is valid for 5 minutes.

If you didn't request a password reset, please ignore this email.

---
InfraCore Support Team
This is an automated message. Please do not reply.
"""
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2563eb;">InfraCore - Password Reset</h2>
            <p>Hello {user_name or 'User'},</p>
            <p>Your One-Time Password (OTP) for password reset is:</p>
            
            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                <h1 style="letter-spacing: 5px; color: #111827; margin: 0;">{otp}</h1>
            </div>
            
            <p style="color: #6b7280;">⏱️ This OTP is valid for <strong>5 minutes</strong>.</p>
            
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
            
            <p style="color: #9ca3af; font-size: 12px;">
                If you didn't request a password reset, please ignore this email.
            </p>
            <p style="color: #9ca3af; font-size: 12px; margin-top: 20px;">
                <strong>InfraCore Support Team</strong><br>
                This is an automated message. Please do not reply.
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            from_name="InfraCore Support"
        )
        return True
    except EmailSendError as e:
        print(f"Failed to send OTP email: {e}")
        return False


# =====================================================
# ROUTES
# =====================================================

@router.post("/send-otp")
def send_otp(request: SendOtpRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Send OTP to user's email for password reset.
    
    Request: POST /forgot-password/send-otp
    Body: { "email": "user@example.com" }
    """
    # Clean up expired OTPs
    cleanup_expired_otps(db)
    
    email = request.email.strip().lower() if request.email else ""
    
    if not email:
        return JSONResponse(
            status_code=400,
            content={"error": "Email is required."}
        )
    
    # Find user
    user = get_user_by_email_or_username(email, db)
    
    # Don't reveal if user exists (security best practice)
    if not user:
        return JSONResponse(
            status_code=200,
            content={"message": "If an account exists, an OTP has been sent to the email."}
        )
    
    # Check rate limit
    is_allowed, rate_limit_msg = check_rate_limit(user.id, db)
    if not is_allowed:
        return JSONResponse(
            status_code=429,
            content={"error": rate_limit_msg}
        )
    
    # Generate OTP
    otp = generate_otp()
    otp_hash = hash_otp(otp)
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    # Store in database
    try:
        otp_record = PasswordResetOTP(
            email=user.email,
            otp_hash=otp_hash,
            expires_at=expires_at,
            attempts=0,
            verified_at=None,
            used_at=None
        )
        db.add(otp_record)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error storing OTP: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to generate OTP. Please try again."}
        )
    
    # Send email
    email_sent = send_otp_email(user.email, otp, user.username)
    
    if not email_sent:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to send OTP. Please check email configuration."}
        )
    
    return JSONResponse(
        status_code=200,
        content={"message": "OTP sent successfully. Please check your email."}
    )


@router.post("/verify-otp")
def verify_otp_endpoint(request: VerifyOtpRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Verify OTP sent to user's email.
    
    Request: POST /forgot-password/verify-otp
    Body: { "email": "user@example.com", "otp": "123456" }
    """
    email = request.email.strip().lower() if request.email else ""
    otp = request.otp.strip() if request.otp else ""
    
    if not email or not otp:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and OTP are required."}
        )
    
    # Validate OTP format
    if not otp.isdigit() or len(otp) != 6:
        return JSONResponse(
            status_code=400,
            content={"error": "OTP must be a 6-digit number."}
        )
    
    # Find latest OTP record for this email
    otp_record = db.query(PasswordResetOTP).filter(
        PasswordResetOTP.email == email
    ).order_by(PasswordResetOTP.created_at.desc()).first()
    
    if not otp_record:
        return JSONResponse(
            status_code=400,
            content={"error": "No OTP found. Please request a new one."}
        )
    
    # Check if expired
    if otp_record.expires_at < datetime.utcnow():
        return JSONResponse(
            status_code=400,
            content={"error": "OTP has expired. Please request a new one."}
        )
    
    # Check if already used
    if otp_record.used_at:
        return JSONResponse(
            status_code=400,
            content={"error": "OTP has already been used."}
        )
    
    # Check attempt limit (max 5 attempts)
    if otp_record.attempts >= 5:
        return JSONResponse(
            status_code=400,
            content={"error": "Too many failed attempts. Please request a new OTP."}
        )
    
    # Verify OTP
    if not verify_otp(otp, otp_record.otp_hash):
        otp_record.attempts += 1
        db.commit()
        attempts_left = 5 - otp_record.attempts
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Invalid OTP. {attempts_left} attempts remaining."
            }
        )
    
    # Mark as verified
    otp_record.verified_at = datetime.utcnow()
    db.commit()
    
    return JSONResponse(
        status_code=200,
        content={"message": "OTP verified successfully."}
    )


@router.post("/reset")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Reset user's password after OTP verification.
    
    Request: POST /forgot-password/reset
    Body: { "email": "user@example.com", "new_password": "newpassword123" }
    """
    email = request.email.strip().lower() if request.email else ""
    new_password = request.new_password.strip() if request.new_password else ""
    
    if not email or not new_password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required."}
        )
    
    # Validate password strength
    if len(new_password) < 8:
        return JSONResponse(
            status_code=400,
            content={"error": "Password must be at least 8 characters long."}
        )
    
    # Find latest OTP record
    otp_record = db.query(PasswordResetOTP).filter(
        PasswordResetOTP.email == email
    ).order_by(PasswordResetOTP.created_at.desc()).first()
    
    if not otp_record or not otp_record.verified_at:
        return JSONResponse(
            status_code=400,
            content={"error": "OTP not verified. Please verify OTP first."}
        )
    
    # Check if expired
    if otp_record.expires_at < datetime.utcnow():
        return JSONResponse(
            status_code=400,
            content={"error": "OTP has expired. Please request a new OTP."}
        )
    
    # Check if already used
    if otp_record.used_at:
        return JSONResponse(
            status_code=400,
            content={"error": "This OTP has already been used."}
        )
    
    # Find user
    user = get_user_by_email_or_username(email, db)
    if not user:
        return JSONResponse(
            status_code=400,
            content={"error": "User not found."}
        )
    
    # Update password
    try:
        import bcrypt
        
        # Truncate password to 72 bytes (bcrypt limit)
        password_bytes = new_password[:72].encode('utf-8')
        # Ensure we don't have partial UTF-8 sequences
        while len(password_bytes) > 72:
            new_password = new_password[:-1]
            password_bytes = new_password[:72].encode('utf-8')
        
        print(f"Hashing password (length: {len(new_password)}, bytes: {len(password_bytes)})...")
        new_password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode()
        print(f"Password hashed successfully")
        
        # Use raw SQL to update password (more reliable than ORM)
        from sqlalchemy import text
        print(f"Updating password via SQL...")
        result = db.execute(
            text("UPDATE users SET password_hash = :hash WHERE email = :email"),
            {"hash": new_password_hash, "email": email}
        )
        print(f"Updated {result.rowcount} user(s)")
        
        # Mark OTP as used
        otp_record.used_at = datetime.utcnow()
        print(f"Marking OTP as used")
        
        print(f"Committing to database...")
        db.commit()
        print(f"Password reset successful!")
        
    except Exception as e:
        db.rollback()
        print(f"Error resetting password: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to reset password. Please try again."}
        )
    
    return JSONResponse(
        status_code=200,
        content={"message": "Password reset successfully. You can now login with your new password."}
    )

