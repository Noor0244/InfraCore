from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

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


@router.get("/", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db)):
    session_user = request.session.get("user")

    if session_user is None:
        return RedirectResponse("/login", status_code=302)

    if session_user.get("role") != "admin":
        return RedirectResponse("/reports", status_code=302)

    users = db.query(User).order_by(User.username).all()

    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "user": session_user,
            "users": users,
        },
    )
