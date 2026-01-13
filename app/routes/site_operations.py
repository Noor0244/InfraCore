from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

@router.get("/site-operations", response_class=HTMLResponse)
async def site_operations(request: Request):
    return templates.TemplateResponse(
        "site_operations.html",
        {"request": request, "title": "Site Operations"}
    )
