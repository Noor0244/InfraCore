from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.labour_service import get_labour

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/labour", response_class=HTMLResponse)
async def labour(request: Request):
    return templates.TemplateResponse(
        "labour.html",
        {"request": request, "title": "Labour", "labour": get_labour()}
    )
