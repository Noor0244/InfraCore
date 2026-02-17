from __future__ import annotations

import hashlib
import secrets

import bcrypt

from app.utils.email import EmailSendError, send_email


def hash_password(password: str) -> str:
    pw = (password or "").encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    if password_hash.startswith("$2"):
        try:
            pw = (password or "").encode("utf-8")[:72]
            return bcrypt.checkpw(pw, password_hash.encode("utf-8"))
        except Exception:
            return False
    return hashlib.sha256((password or "").encode("utf-8")).hexdigest() == password_hash


def generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def send_otp_email(to_email: str, otp: str) -> None:
    subject = "InfraCore Password Reset OTP"
    body = (
        f"Your InfraCore OTP is: {otp}\n\n"
        "This OTP is valid for 10 minutes and can be used only once."
    )
    send_email(to_email=to_email, subject=subject, body=body)
