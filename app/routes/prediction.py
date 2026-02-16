from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.db.session import get_db
from app.models.project import Project
from app.models.project_user import ProjectUser
from app.models.activity import Activity
from app.models.prediction_log import PredictionLog
from app.services.prediction_service import calculate_predictions, dumps_compact
from app.services.settings_service import get_int_setting
from app.services.update_alerts_service import AlertConfig, compute_project_update_alerts


router = APIRouter(tags=["Prediction"])
templates = Jinja2Templates(directory="app/templates")


def _ensure_project_access(db: Session, project_id: int, user: dict | None) -> Project | None:
    if not user:
        return None

    base = (
        db.query(Project)
        .outerjoin(ProjectUser, Project.id == ProjectUser.project_id)
        .filter(
            Project.id == project_id,
            Project.is_active == True,
            Project.status == "active",
            Project.completed_at.is_(None),
        )
    )

    if user.get("role") in {"admin", "superadmin"}:
        return base.first()

    return (
        base.filter(
            or_(
                Project.created_by == user.get("id"),
                ProjectUser.user_id == user.get("id"),
            )
        )
        .distinct()
        .first()
    )


@router.get("/projects/{project_id}/prediction", response_class=HTMLResponse)
def prediction_page(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=302)

    project = _ensure_project_access(db, project_id, user)
    if not project:
        return RedirectResponse("/dashboard", status_code=302)

    activities = (
        db.query(Activity)
        .filter(Activity.project_id == project_id)
        .order_by(func.lower(Activity.name).asc())
        .all()
    )

    project_type = (project.project_type or "").strip() or "Building"
    is_road = project_type.lower() == "road"

    lookahead_days = get_int_setting(db, user_id=int(user.get("id")), key="alerts.lookahead_days", default=30)
    due_soon_days = get_int_setting(db, user_id=int(user.get("id")), key="alerts.due_soon_days", default=7)
    max_rows = get_int_setting(db, user_id=int(user.get("id")), key="alerts.max_rows", default=30)
    cfg = AlertConfig(
        lookahead_days=int(lookahead_days),
        due_soon_days=int(due_soon_days),
        max_rows=int(max_rows),
    )
    next_requirements = compute_project_update_alerts(db=db, project_id=int(project_id), cfg=cfg)

    return templates.TemplateResponse(
        "prediction.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "project_id": project_id,
            "project_type": project_type,
            "is_road": is_road,
            "activities": activities,
            "next_requirements": next_requirements,
        },
    )


@router.post("/projects/{project_id}/prediction/calc")
async def prediction_calc(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    project = _ensure_project_access(db, project_id, user)
    if not project:
        return JSONResponse({"error": "forbidden"}, status_code=403)

    payload = {}
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}

    mode = (payload.get("mode") or "Inventory").strip()
    inputs = payload.get("inputs") or {}
    if not isinstance(inputs, dict):
        inputs = {}

    project_type = (project.project_type or "").strip() or "Building"

    result = calculate_predictions(
        db=db,
        project_id=project_id,
        project_type=project_type,
        mode=mode,
        inputs=inputs,
    )

    # Audit log (best-effort)
    try:
        log = PredictionLog(
            project_id=project_id,
            user_id=user.get("id"),
            project_type=project_type,
            mode=mode,
            inputs_json=dumps_compact({"mode": mode, "inputs": inputs}),
            outputs_json=dumps_compact(result),
            action_taken=None,
            created_at=datetime.utcnow(),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        result["log_id"] = log.id
    except Exception:
        db.rollback()

    return result


@router.get("/projects/{project_id}/prediction/history")
def prediction_history(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    project = _ensure_project_access(db, project_id, user)
    if not project:
        return JSONResponse({"error": "forbidden"}, status_code=403)

    rows = (
        db.query(PredictionLog)
        .filter(PredictionLog.project_id == project_id)
        .order_by(PredictionLog.created_at.desc())
        .limit(25)
        .all()
    )

    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "mode": r.mode,
                "project_type": r.project_type,
                "action_taken": r.action_taken,
            }
        )

    return {"items": out}


@router.post("/projects/{project_id}/prediction/action")
async def prediction_action(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    project = _ensure_project_access(db, project_id, user)
    if not project:
        return JSONResponse({"error": "forbidden"}, status_code=403)

    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}

    log_id = payload.get("log_id")
    action_taken = (payload.get("action_taken") or "").strip()
    if not log_id or not action_taken:
        return JSONResponse({"error": "invalid"}, status_code=400)

    row = (
        db.query(PredictionLog)
        .filter(PredictionLog.id == int(log_id), PredictionLog.project_id == project_id)
        .first()
    )
    if not row:
        return JSONResponse({"error": "not_found"}, status_code=404)

    row.action_taken = action_taken[:80]
    db.add(row)
    db.commit()

    return {"status": "ok"}
