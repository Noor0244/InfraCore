from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
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

def hash_password(p: str):
    return hashlib.sha256(p.encode()).hexdigest()

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html", {"request": request, "user": None}
    )

@router.post("/login")
def login_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or user.password != hash_password(password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "user": None, "error": "Invalid credentials"},
        )

    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
    }

    return RedirectResponse("/reports", status_code=302)

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)
