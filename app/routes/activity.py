from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.activity_service import get_recent_activities

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/activity", response_class=HTMLResponse)
def activity_page(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if user is None or user["role"] != "admin":
        return RedirectResponse("/dashboard", status_code=302)

    logs = get_recent_activities(db)

    return templates.TemplateResponse(
        "activity.html",
        {
            "request": request,
            "user": user,
            "logs": logs,
        }
    )
