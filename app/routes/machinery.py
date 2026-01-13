from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.machinery_service import get_machinery

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/machinery", response_class=HTMLResponse)
async def machinery(request: Request):
    return templates.TemplateResponse(
        "machinery.html",
        {"request": request, "title": "Machinery", "machinery": get_machinery()}
    )
