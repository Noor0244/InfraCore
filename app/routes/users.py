
# OTP logic is now handled in main app with robust bcrypt, expiry, and attempt logic.
# This router no longer provides a /forgot-password/send-otp endpoint.

from fastapi import APIRouter

router = APIRouter()

# ...existing code...
