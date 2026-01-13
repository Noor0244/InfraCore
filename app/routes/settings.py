from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.settings_service import get_int_setting, set_setting
from app.utils.flash import flash
from app.utils.template_filters import register_template_filters

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)

@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    # Defaults for the warning/update system
    lookahead_days = get_int_setting(db, user_id=int(user["id"]), key="alerts.lookahead_days", default=30)
    due_soon_days = get_int_setting(db, user_id=int(user["id"]), key="alerts.due_soon_days", default=7)
    max_rows = get_int_setting(db, user_id=int(user["id"]), key="alerts.max_rows", default=30)

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "title": "Settings",
            "user": user,
            "lookahead_days": lookahead_days,
            "due_soon_days": due_soon_days,
            "max_rows": max_rows,
        }
    )


@router.post("/settings")
async def save_settings(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    form = await request.form()

    if str(form.get("reset_alerts") or "").strip() == "1":
        set_setting(db, user_id=int(user["id"]), key="alerts.lookahead_days", value=str(30))
        set_setting(db, user_id=int(user["id"]), key="alerts.due_soon_days", value=str(7))
        set_setting(db, user_id=int(user["id"]), key="alerts.max_rows", value=str(30))
        db.commit()
        flash(request, "Alert settings reset to defaults", "success")
        return RedirectResponse("/settings", status_code=302)

    def _to_int(name: str, default: int, min_v: int, max_v: int) -> int:
        raw = str(form.get(name) or "").strip()
        try:
            v = int(float(raw))
        except Exception:
            v = int(default)
        v = max(min_v, min(max_v, v))
        return v

    lookahead_days = _to_int("lookahead_days", 30, 1, 365)
    due_soon_days = _to_int("due_soon_days", 7, 0, 60)
    max_rows = _to_int("max_rows", 30, 5, 200)

    set_setting(db, user_id=int(user["id"]), key="alerts.lookahead_days", value=str(lookahead_days))
    set_setting(db, user_id=int(user["id"]), key="alerts.due_soon_days", value=str(due_soon_days))
    set_setting(db, user_id=int(user["id"]), key="alerts.max_rows", value=str(max_rows))
    db.commit()

    flash(request, "Settings saved", "success")
    return RedirectResponse("/settings", status_code=302)
