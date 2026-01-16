# app/routes/design_data.py
# --------------------------------------------------
# Design Data Routes (Alignment, Levels, etc.)
# InfraCore
# --------------------------------------------------

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.project_alignment import ProjectAlignmentPoint
from app.models.project_user import ProjectUser
from fastapi.templating import Jinja2Templates

from app.utils.flash import flash   # ✅ ADD THIS


router = APIRouter(prefix="/projects", tags=["Design Data"])
templates = Jinja2Templates(directory="app/templates")


# ---------------- DB DEPENDENCY ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- PROJECT ACCESS GUARD ----------------
def get_project_access(db, project_id, user):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None, None

    if user["role"] in {"admin", "superadmin"}:
        return project, "admin"

    if project.created_by == user["id"]:
        return project, "owner"

    pu = (
        db.query(ProjectUser)
        .filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == user["id"]
        )
        .first()
    )

    if pu:
        return project, pu.role_in_project

    return None, None


# =================================================
# DESIGN DATA OVERVIEW (WITH ALIGNMENT SUMMARY)
# =================================================
@router.get("/{project_id}/design-data", response_class=HTMLResponse)
def design_data_overview(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    project, role = get_project_access(db, project_id, user)

    if not project:
        return RedirectResponse("/projects", status_code=302)

    summary = (
        db.query(
            func.count(ProjectAlignmentPoint.id),
            func.min(ProjectAlignmentPoint.chainage_m),
            func.max(ProjectAlignmentPoint.chainage_m),
        )
        .filter(ProjectAlignmentPoint.project_id == project_id)
        .one()
    )

    alignment_summary = None
    if summary[0] > 0:
        count, start_m, end_m = summary

        def fmt(ch):
            return f"{ch // 1000}+{ch % 1000:03d}"

        alignment_summary = {
            "count": count,
            "start": fmt(start_m),
            "end": fmt(end_m),
        }

    return templates.TemplateResponse(
        "projects/design_data.html",
        {
            "request": request,
            "project": project,
            "role": role,
            "user": user,
            "alignment_summary": alignment_summary,
        }
    )


# =================================================
# AUTO-GENERATE ALIGNMENT POINTS BY INTERVAL
# =================================================
@router.post("/{project_id}/design-data/alignment/generate")
def generate_alignment_points(
    project_id: int,
    request: Request,
    interval_m: int = Form(...),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    project, role = get_project_access(db, project_id, user)

    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "Unauthorized action", "error")
        return RedirectResponse("/projects", status_code=302)

    if interval_m not in (10, 25, 50):
        flash(request, "Invalid alignment interval selected", "error")
        return RedirectResponse(
            f"/projects/{project_id}/design-data/alignment",
            status_code=302
        )

    if not project.chainage_start or not project.chainage_end:
        flash(request, "Project chainage not defined", "error")
        return RedirectResponse(
            f"/projects/{project_id}/design-data/alignment",
            status_code=302
        )

    try:
        start_m = int(project.chainage_start.replace("+", ""))
        end_m = int(project.chainage_end.replace("+", ""))
    except ValueError:
        flash(request, "Invalid chainage format", "error")
        return RedirectResponse(
            f"/projects/{project_id}/design-data/alignment",
            status_code=302
        )

    existing = {
        pt.chainage_m
        for pt in db.query(ProjectAlignmentPoint.chainage_m)
        .filter(ProjectAlignmentPoint.project_id == project_id)
        .all()
    }

    new_points = []
    for ch in range(start_m, end_m + 1, interval_m):
        if ch in existing:
            continue

        new_points.append(
            ProjectAlignmentPoint(
                project_id=project_id,
                chainage_m=ch,
                northing=0.0,
                easting=0.0,
                ogl=0.0,
                frl=0.0,
            )
        )

    if new_points:
        db.bulk_save_objects(new_points)
        db.commit()
        flash(request, "Alignment points generated successfully", "success")

    return RedirectResponse(
        f"/projects/{project_id}/design-data/alignment",
        status_code=302
    )


# =================================================
# UPDATE SINGLE ALIGNMENT POINT (WITH FLASH)
# =================================================
@router.post("/{project_id}/design-data/alignment/{point_id}/update")
def update_alignment_point(
    project_id: int,
    point_id: int,
    request: Request,
    ogl: float = Form(...),
    frl: float = Form(...),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    project, role = get_project_access(db, project_id, user)

    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "Unauthorized action", "error")
        return RedirectResponse("/projects", status_code=302)

    point = (
        db.query(ProjectAlignmentPoint)
        .filter(
            ProjectAlignmentPoint.id == point_id,
            ProjectAlignmentPoint.project_id == project_id
        )
        .first()
    )

    if not point:
        flash(request, "Alignment point not found", "error")
        return RedirectResponse(
            f"/projects/{project_id}/design-data/alignment",
            status_code=302
        )

    # ---------------- RULE 1: CUT / FILL LIMIT ----------------
    MAX_CUT_FILL = 10.0

    if abs(frl - ogl) > MAX_CUT_FILL:
        flash(
            request,
            "FRL exceeds maximum cut/fill limit (±10 m)",
            "error"
        )
        return RedirectResponse(
            f"/projects/{project_id}/design-data/alignment",
            status_code=302
        )

    # ---------------- RULE 2: GRADIENT CHECK ----------------
    MAX_GRADIENT_PERCENT = 5.0

    neighbors = (
        db.query(ProjectAlignmentPoint)
        .filter(
            ProjectAlignmentPoint.project_id == project_id,
            ProjectAlignmentPoint.id != point_id
        )
        .order_by(ProjectAlignmentPoint.chainage_m)
        .all()
    )

    for nb in neighbors:
        delta_chainage = abs(point.chainage_m - nb.chainage_m)
        if delta_chainage == 0:
            continue

        gradient = abs((frl - nb.frl) / delta_chainage) * 100

        if gradient > MAX_GRADIENT_PERCENT:
            flash(
                request,
                "Gradient between chainages exceeds 5%",
                "error"
            )
            return RedirectResponse(
                f"/projects/{project_id}/design-data/alignment",
                status_code=302
            )

    # ---------------- SAVE ----------------
    point.ogl = ogl
    point.frl = frl
    db.commit()

    flash(request, "Alignment point updated successfully", "success")

    return RedirectResponse(
        f"/projects/{project_id}/design-data/alignment",
        status_code=302
    )
# =================================================
# BULK FRL ASSIGNMENT (RANGE-BASED)
# =================================================
@router.post("/{project_id}/design-data/alignment/bulk-frl")
def bulk_frl_assignment(
    project_id: int,
    request: Request,
    start_chainage: int = Form(...),
    end_chainage: int = Form(...),
    frl_start: float = Form(...),
    frl_end: float = Form(...),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    project, role = get_project_access(db, project_id, user)

    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "Unauthorized action", "error")
        return RedirectResponse("/projects", status_code=302)

    if start_chainage >= end_chainage:
        flash(request, "Invalid chainage range", "error")
        return RedirectResponse(
            f"/projects/{project_id}/design-data/alignment",
            status_code=302
        )

    points = (
        db.query(ProjectAlignmentPoint)
        .filter(
            ProjectAlignmentPoint.project_id == project_id,
            ProjectAlignmentPoint.chainage_m >= start_chainage,
            ProjectAlignmentPoint.chainage_m <= end_chainage,
        )
        .order_by(ProjectAlignmentPoint.chainage_m)
        .all()
    )

    if len(points) < 2:
        flash(request, "Not enough alignment points in range", "error")
        return RedirectResponse(
            f"/projects/{project_id}/design-data/alignment",
            status_code=302
        )

    total_length = end_chainage - start_chainage
    gradient = (frl_end - frl_start) / total_length * 100

    # -------- Gradient rule --------
    MAX_GRADIENT_PERCENT = 5.0
    if abs(gradient) > MAX_GRADIENT_PERCENT:
        flash(
            request,
            f"Gradient {gradient:.2f}% exceeds allowed 5%",
            "error"
        )
        return RedirectResponse(
            f"/projects/{project_id}/design-data/alignment",
            status_code=302
        )

    # -------- Apply FRL --------
    for pt in points:
        delta = pt.chainage_m - start_chainage
        pt.frl = frl_start + (frl_end - frl_start) * (delta / total_length)

    db.commit()

    flash(
        request,
        f"FRL assigned successfully (Gradient {gradient:.2f}%)",
        "success"
    )

    return RedirectResponse(
        f"/projects/{project_id}/design-data/alignment",
        status_code=302
    )
