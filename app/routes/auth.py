from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import bcrypt
import hashlib

from app.db.session import SessionLocal
from app.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.
    Supports both bcrypt (new) and SHA256 (legacy) formats.
    """
    try:
        # Try bcrypt first (new format)
        password_bytes = plain_password[:72].encode('utf-8')
        # Ensure valid UTF-8 boundaries
        while len(password_bytes) > 72:
            plain_password = plain_password[:-1]
            password_bytes = plain_password[:72].encode('utf-8')
        
        if bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8')):
            return True
    except Exception:
        pass
    
    # Fall back to SHA256 (legacy format for backward compatibility)
    try:
        sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
        if sha256_hash == hashed_password:
            return True
    except Exception:
        pass
    
    return False

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str | None = None):
    return templates.TemplateResponse(
        "login.html", {"request": request, "user": None, "next": next}
    )

@router.post("/login")
def login_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str | None = Form(None),
    db: Session = Depends(get_db),
):
    # Trim whitespace from input
    username = username.strip()
    password = password.strip()
    
    user = None
    
    # Try by username first (exact match)
    user = db.query(User).filter(User.username == username).first()
    
    # Try by email if not found by username (case-insensitive)
    if not user and "@" in username:
        # Get all users with email and check case-insensitively in Python
        all_users = db.query(User).filter(User.email != None).all()
        for u in all_users:
            if u.email and u.email.lower() == username.lower():
                user = u
                break
    
    # Verify user exists and is active
    if not user or not user.is_active:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "user": None, "error": "Invalid username/email or password"},
        )
    
    # Verify password (supports both bcrypt and SHA256)
    if not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "user": None, "error": "Invalid username/email or password"},
        )

    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
    }

    # Redirect back to the originally requested page when provided.
    # Only allow relative, same-site paths.
    if next:
        n = str(next).strip()
        if n.startswith("/") and ("://" not in n) and ("\\" not in n):
            return RedirectResponse(n, status_code=302)

    return RedirectResponse("/reports", status_code=302)

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)
