import hashlib


def hash_password(password: str) -> str:
    """
    Hash password using SHA-256 (development-safe).
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password by comparing SHA-256 hashes.
    """
    return hash_password(plain_password) == hashed_password
