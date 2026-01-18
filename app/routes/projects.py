# app/routes/projects.py
# --------------------------------------------------
# Project CRUD + Management (ROLE-SECURED)
# InfraCore
# --------------------------------------------------

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import bcrypt
import logging
import json

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.project_user import ProjectUser
from app.models.project_alignment import ProjectAlignmentPoint
from app.models.user import User
from app.utils.flash import flash
from app.utils.audit_logger import log_action, model_to_dict
from app.utils.road_classification import (
    get_classification_metadata,
    get_presets_for_engineering_type,
)

from app.utils.project_type_presets import (
    get_presets_for_project_type,
    serialize_presets,
)
from app.utils.activity_material_presets import get_activity_material_links, serialize_links
from app.utils.road_preset_engine import get_road_preset
from app.utils.template_filters import register_template_filters
from app.utils.dates import parse_date_ddmmyyyy_or_iso

from app.services.project_wizard_service import get_state as wizard_get_state, deactivate as wizard_deactivate
from app.services.stretch_service import apply_activities_to_stretches
from app.models.road_stretch import RoadStretch
from app.models.stretch_activity import StretchActivity
from app.models.stretch_material import StretchMaterial
from app.models.stretch_material_exclusion import StretchMaterialExclusion
from app.utils.stretch_generation import chainage_from_meters
from app.utils.stretch_generation import generate_stretch_segments

# Material model used by presets
from app.models.material import Material

# Other models that reference projects - ensure we delete dependents safely
from app.models.activity import Activity
from app.models.project_activity import ProjectActivity
from app.models.planned_material import PlannedMaterial
from app.models.activity_material import ActivityMaterial
from app.models.material_usage_daily import MaterialUsageDaily
from app.models.material_usage import MaterialUsage
from app.models.material_stock import MaterialStock
from app.models.activity_progress import ActivityProgress
from app.models.daily_entry import DailyEntry
from app.models.material_vendor import MaterialVendor
from app.models.procurement_log import ProcurementLog
from app.models.prediction_log import PredictionLog

from app.models.daily_work_report import DailyWorkReport
from app.models.daily_work_activity import DailyWorkActivity
from app.models.daily_work_material import DailyWorkMaterial
from app.models.daily_work_labour import DailyWorkLabour
from app.models.daily_work_machinery import DailyWorkMachinery
from app.models.daily_work_delay import DailyWorkDelay
from app.models.daily_work_qc import DailyWorkQC
from app.models.daily_work_upload import DailyWorkUpload

from app.utils.material_lead_time import (
    compute_expected_delivery_date,
    evaluate_delivery_risk,
    resolve_effective_lead_time_days,
    compute_reorder_suggestion,
)

from app.utils.road_classification import get_presets_for_engineering_type

from app.utils.id_codes import activity_code_allocator

# Helper: create project activity presets for road projects
def _create_road_activity_presets(db: Session, project: Project):
    if not project or project.project_type != 'Road':
        return

    road_type_text = (project.road_type or "")
    if not road_type_text:
        return

    # Match flexible pavement variants (case-insensitive partial match)
    if 'flexible' not in road_type_text.lower():
        return

    activities = [
        "Clearing & Grubbing",
        "Subgrade Preparation",
        "Granular Sub-Base (GSB)",
        "Wet Mix Macadam (WMM)",
        "Prime Coat",
        "Dense Bituminous Macadam (DBM)",
        "Bituminous Concrete (BC)",
        "Road Marking & Finishing",
    ]

    next_act_code = activity_code_allocator(db, Activity, project_id=int(project.id), width=6, project_width=6)

    for name in activities:
        # create Activity if missing
        act = (
            db.query(Activity)
            .filter(Activity.project_id == project.id, Activity.name == name)
            .first()
        )
        if not act:
            act = Activity(name=name, is_standard=True, project_id=project.id)
            act.code = next_act_code()
            db.add(act)
            db.flush()  # assign id without committing

        # create ProjectActivity mapping if missing
        pa = (
            db.query(ProjectActivity)
            .filter(ProjectActivity.project_id == project.id, ProjectActivity.activity_id == act.id)
            .first()
        )
        if not pa:
            pa = ProjectActivity(
                project_id=project.id,
                activity_id=act.id,
                planned_quantity=0,
                unit="unit",
                start_date=project.planned_start_date,
                end_date=project.planned_end_date,
            )
            db.add(pa)


def _ensure_project_road_presets(db: Session, project: Project) -> None:
    if not project or project.project_type != "Road":
        return

    has_project_activities = (
        db.query(ProjectActivity)
        .filter(ProjectActivity.project_id == int(project.id))
        .first()
        is not None
    )
    has_planned_materials = (
        db.query(PlannedMaterial)
        .filter(
            PlannedMaterial.project_id == int(project.id),
            PlannedMaterial.stretch_id == None,  # noqa: E711
        )
        .first()
        is not None
    )

    if has_project_activities and has_planned_materials:
        return

    road_category = (getattr(project, "road_category", None) or getattr(project, "road_type", None) or "").strip()
    engineering_type = (getattr(project, "road_engineering_type", None) or getattr(project, "road_type", None) or "").strip()

    road_preset = get_road_preset(
        road_category=road_category,
        road_engineering_type=engineering_type,
        road_extras_json=getattr(project, "road_extras_json", None),
        db=db,
    )

    if road_preset:
        activities = list(road_preset.activities or [])
        activity_defs = list(road_preset.activity_defs or [])
        materials = list(road_preset.materials or [])
        links = list(road_preset.links or [])
    else:
        preset = get_presets_for_engineering_type(engineering_type)
        activities = list(preset.get("activities", []))
        activity_defs = [{"name": n, "activity_scope": "STRETCH"} for n in activities]
        materials = list(preset.get("materials", []))
        links = list(get_activity_material_links("Road", engineering_type))

    activity_defs_by_name: dict[str, dict] = {}
    for d in activity_defs:
        if not isinstance(d, dict):
            continue
        n = str(d.get("name") or "").strip()
        if not n:
            continue
        activity_defs_by_name[n.lower()] = d

    next_act_code = activity_code_allocator(db, Activity, project_id=int(project.id), width=6, project_width=6)

    for act_name in activities:
        name = str(act_name or "").strip()
        if not name:
            continue
        act = (
            db.query(Activity)
            .filter(Activity.project_id == int(project.id), Activity.name == name)
            .first()
        )
        if not act:
            act = Activity(
                name=name,
                is_standard=True,
                project_id=int(project.id),
                code=next_act_code(),
            )
            db.add(act)
            db.flush()

        d = activity_defs_by_name.get(name.lower())
        scope = "STRETCH"
        if isinstance(d, dict):
            raw_scope = d.get("activity_scope")
            if raw_scope is None:
                raw_scope = d.get("scope")
            scope_candidate = str(raw_scope or "").strip().upper()
            if scope_candidate in {"COMMON", "STRETCH"}:
                scope = scope_candidate

        pa_exists = (
            db.query(ProjectActivity)
            .filter(
                ProjectActivity.project_id == int(project.id),
                ProjectActivity.activity_id == int(act.id),
            )
            .first()
        )
        if not pa_exists:
            db.add(
                ProjectActivity(
                    project_id=int(project.id),
                    activity_id=int(act.id),
                    planned_quantity=0.0,
                    unit=str(getattr(act, "display_unit", None) or "unit"),
                    start_date=project.planned_start_date,
                    end_date=project.planned_end_date,
                    activity_scope=scope,
                )
            )
        else:
            try:
                pa_exists.activity_scope = scope
                db.add(pa_exists)
            except Exception:
                pass

    for m in materials:
        mat_name = str(getattr(m, "name", None) or "").strip()
        if not mat_name:
            continue
        unit = str(getattr(m, "default_unit", None) or "unit").strip() or "unit"
        allowed_units = list(getattr(m, "allowed_units", None) or [])
        allowed_units = [str(u or "").strip() for u in allowed_units if str(u or "").strip()]
        if not allowed_units:
            allowed_units = [unit]
        if unit not in allowed_units:
            allowed_units.insert(0, unit)

        mat = db.query(Material).filter(Material.name == mat_name).first()
        if not mat:
            mat = Material(
                name=mat_name,
                unit=unit,
                standard_unit=unit,
                allowed_units=json.dumps(allowed_units),
            )
            db.add(mat)
            db.commit()
            db.refresh(mat)

        pm_exists = (
            db.query(PlannedMaterial)
            .filter(
                PlannedMaterial.project_id == int(project.id),
                PlannedMaterial.material_id == int(mat.id),
                PlannedMaterial.stretch_id == None,  # noqa: E711
            )
            .first()
        )
        if not pm_exists:
            db.add(
                PlannedMaterial(
                    project_id=int(project.id),
                    material_id=int(mat.id),
                    stretch_id=None,
                    unit=unit,
                    allowed_units=json.dumps(allowed_units),
                    planned_quantity=Decimal("0"),
                )
            )

    db.commit()

    # Create activity-material links
    for link in links:
        try:
            act_name = str(getattr(link, "activity", None) or "").strip()
            mat_def = getattr(link, "material", None)
            mat_name = str(getattr(mat_def, "name", None) or "").strip()
            rate = float(getattr(link, "consumption_rate", None) or 0)
        except Exception:
            continue
        if not act_name or not mat_name:
            continue

        act = (
            db.query(Activity)
            .filter(Activity.project_id == int(project.id), Activity.name == act_name)
            .first()
        )
        mat = db.query(Material).filter(Material.name == mat_name).first()
        if not act or not mat:
            continue

        exists = (
            db.query(ActivityMaterial)
            .filter(
                ActivityMaterial.activity_id == int(act.id),
                ActivityMaterial.material_id == int(mat.id),
            )
            .first()
        )
        if not exists:
            db.add(
                ActivityMaterial(
                    activity_id=int(act.id),
                    material_id=int(mat.id),
                    consumption_rate=rate,
                )
            )

    db.commit()


router = APIRouter(prefix="/projects", tags=["Projects"])
templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)


def hash_password(password: str) -> str:
    pw = (password or "").encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")

logger = logging.getLogger(__name__)



# ---------------- DB DEPENDENCY ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- ROAD-TYPE PRESETS (JSON) ----------------
@router.get("/road-presets")
def road_presets(
    request: Request,
    engineering_type: str | None = None,
    road_category: str | None = None,
    road_extras_json: str | None = None,
    db: Session = Depends(get_db),
):
    """Return standard presets for a given road engineering type.

    Supports a data-driven engine keyed by Road Category + Engineering Type.
    Falls back to legacy engineering-type-only presets.
    """
    result = get_road_preset(
        road_category=road_category,
        road_engineering_type=engineering_type,
        road_extras_json=road_extras_json,
        db=db,
    )

    if result:
        return {
            "preset_key": result.preset_key,
            "road_category": (road_category or "").strip(),
            "engineering_type": (engineering_type or "").strip(),
            "activities": list(result.activities),
            # Rich activity defs for UI (keeps scope/category metadata)
            "activity_preset_defs": list(result.activity_defs or []),
            "materials": [
                {
                    "name": m.name,
                    "default_unit": m.default_unit,
                    "allowed_units": list(m.allowed_units),
                }
                for m in (result.materials or [])
            ],
            # Optional extra (UI-safe): activity→material suggestions
            "activity_material_links": serialize_links(result.links or []),
        }

    preset = get_presets_for_engineering_type(engineering_type)
    materials = preset.get("materials", [])
    return {
        "engineering_type": (engineering_type or "").strip(),
        "activities": list(preset.get("activities", [])),
        "materials": [
            {
                "name": m.name,
                "default_unit": m.default_unit,
                "allowed_units": list(m.allowed_units),
            }
            for m in materials
        ],
    }


@router.get("/classification-metadata")
def classification_metadata(request: Request):
    """UI helper endpoint. Keeps template free of hard-coded classification lists."""
    return get_classification_metadata()


@router.get("/type-presets")
def type_presets(request: Request, project_type: str | None = None):
    """Return standard presets for a non-road Project Type (Building/Bridge/Flyover/Utility...)."""
    preset = get_presets_for_project_type(project_type)
    data = serialize_presets(preset)
    return {
        "project_type": (project_type or "").strip(),
        "activities": data.get("activities", []),
        "materials": data.get("materials", []),
    }

# ---------------- PROJECT ACCESS GUARD ----------------
def get_project_access(db, project_id, user):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None, None
    # If there's no authenticated user, just return project with no role
    if not user:
        return project, None

    # System admin has full access
    if user.get("role") in {"admin", "superadmin"}:
        return project, "admin"

    # Creator is owner
    if project.created_by == user.get("id"):
        return project, "owner"

    # Check explicit project membership
    pu = (
        db.query(ProjectUser)
        .filter(
            ProjectUser.project_id == project_id,
            ProjectUser.user_id == user.get("id")
        )
        .first()
    )

    if pu:
        return project, pu.role_in_project

    # Not a member — allow read-only viewing for logged-in users
    return project, "viewer"

# =================================================
# LIST PROJECTS
# =================================================
@router.get("", response_class=HTMLResponse)
def projects_page(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    base = (
        db.query(Project)
        .outerjoin(ProjectUser, Project.id == ProjectUser.project_id)
        .filter(
            Project.is_active == True,
            Project.status == "active",
            Project.completed_at.is_(None),
        )
    )

    # Keep the UI clean from seed/test/preset projects (matches Daily Execution behavior)
    base = base.filter(
        ~func.lower(Project.name).like("%preset%"),
        ~func.lower(Project.name).like("%test%"),
    )

    if user.get("role") in {"admin", "superadmin"}:
        projects = base.distinct().order_by(Project.id.desc()).all()
    else:
        projects = (
            base.filter(
                (Project.created_by == user["id"]) |
                (ProjectUser.user_id == user["id"])
            )
            .distinct()
            .order_by(Project.id.desc())
            .all()
        )

    return templates.TemplateResponse(
        "projects.html",
        {"request": request, "projects": projects, "user": user}
    )

# =================================================
# MANAGE PROJECTS
# =================================================
@router.get("/manage", response_class=HTMLResponse)
def manage_projects_page(request: Request, view: str | None = "active", db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    query = db.query(Project)

    # Admin can manage all projects; others manage their own.
    if user.get("role") not in {"admin", "superadmin"}:
        query = query.filter(Project.created_by == user["id"])

    if view == "archived":
        query = query.filter(Project.is_active == False)
    else:
        query = query.filter(Project.is_active == True)

    projects = query.order_by(Project.created_at.desc()).all()

    return templates.TemplateResponse(
        "projects_manage.html",
        {"request": request, "projects": projects, "view": view, "user": user}
    )

# =================================================
# CREATE PROJECT
# =================================================
@router.get("/new", response_class=HTMLResponse)
def new_project_page(request: Request):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login?next=/projects/new", status_code=302)

    all_users: list[User] = []
    if user.get("role") in ["admin", "superadmin", "manager"]:
        db = SessionLocal()
        try:
            all_users = (
                db.query(User)
                .filter(User.is_active == True)  # noqa: E712
                .order_by(User.username.asc())
                .all()
            )
        except Exception:
            all_users = []
        finally:
            db.close()

    return templates.TemplateResponse(
        "projects/new_project.html",
        {
            "request": request,
            "user": user,
            "all_users": all_users,
            # Bootstrap classification lists into the HTML to avoid an initial
            # client-side fetch that can hang and keep the page "loading".
            "classification_metadata": get_classification_metadata(),
        },
    )


@router.post("/create-user")
def create_user_from_project_page(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str | None = Form(None),
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login?next=/projects/new", status_code=302)

    if user.get("role") not in {"admin", "superadmin"}:
        flash(request, "Admin access required", "warning")
        return RedirectResponse("/projects/new", status_code=302)

    role = str(role or "").strip().lower()
    allowed_roles = {"admin", "manager", "user", "viewer"}
    if role not in allowed_roles:
        flash(request, "Invalid role selected", "error")
        return RedirectResponse("/projects/new", status_code=302)

    uname = str(username or "").strip()
    if not uname:
        flash(request, "Username is required", "error")
        return RedirectResponse("/projects/new", status_code=302)

    existing = db.query(User).filter(func.lower(User.username) == uname.lower()).first()
    if existing:
        flash(request, "Username already exists", "error")
        return RedirectResponse("/projects/new", status_code=302)

    db.add(
        User(
            username=uname,
            password_hash=hash_password(password),
            email=(email or None),
            role=role,
            is_active=True,
        )
    )
    db.commit()

    flash(request, "User created successfully", "success")
    return RedirectResponse("/projects/new", status_code=302)


@router.get("/create-user")
def create_user_from_project_page_get(request: Request):
    return RedirectResponse("/projects/new", status_code=302)

@router.post("/create")
def create_project_form(
    request: Request,
    wizard_id: int | None = Form(None),
    stretch_enabled: str | None = Form(None),
    stretch_method: str | None = Form(None),
    stretch_number_of_stretches: int | None = Form(None),
    stretch_length_m: int | None = Form(None),
    stretch_segments_json: str | None = Form(None),
    # Restore required fields; keep road-specific optional with conditional validation
    name: str = Form(...),
    # Basic fields
    project_code: str | None = Form(None),
    client_authority: str | None = Form(None),
    contractor: str | None = Form(None),
    consultant_pmc: str | None = Form(None),

    # Road-specific fields (classification)
    road_category: str | None = Form(None),
    road_engineering_type: str | None = Form(None),
    # Backward compatibility (older forms)
    road_type: str | None = Form(None),
    road_width: float | None = Form(None),
    carriageway_width: float | None = Form(None),
    shoulder_type: str | None = Form(None),
    median_type: str | None = Form(None),
    road_length_km: float | None = Form(None),
    road_construction_type: str | None = Form(None),

    # Road metadata (optional)
    road_name: str | None = Form(None),
    lane_configuration: str | None = Form(None),
    road_pavement_type: str | None = Form(None),
    terrain_type: str | None = Form(None),
    # Preset selections (optional; only used for Road projects)
    activity_presets: list[str] | None = Form(None),
    material_presets: list[str] | None = Form(None),
    # Editable preset payloads from UI (preferred when present)
    activity_presets_json: str | None = Form(None),
    activity_preset_defs_json: str | None = Form(None),
    material_presets_json: str | None = Form(None),
    material_preset_defs_json: str | None = Form(None),
    project_team_json: str | None = Form(None),
    road_extras_json: str | None = Form(None),
    # Concrete-specific (conditional when road_type == 'Concrete Road')
    pavement_type: str | None = Form(None),
    slab_thickness_mm: int | None = Form(None),
    grade_of_concrete: str | None = Form(None),
    joint_spacing_m: float | None = Form(None),
    dowel_diameter_mm: int | None = Form(None),
    tie_bar_diameter_mm: int | None = Form(None),

    # Location
    country: str = Form(...),
    state: str | None = Form(None),
    district: str | None = Form(None),
    city: str = Form(...),
    chainage_start: str | None = Form(None),
    chainage_end: str | None = Form(None),
    planned_start_date: str = Form(...),
    planned_end_date: str = Form(...),
    project_type: str = Form(...),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login?next=/projects/new", status_code=302)

    default_start = date.today()
    default_end = default_start + timedelta(days=1)
    try:
        planned_start_date = parse_date_ddmmyyyy_or_iso(planned_start_date)
    except Exception:
        planned_start_date = default_start
        flash(request, "Project start date invalid; defaulted to today.", "warning")
    try:
        planned_end_date = parse_date_ddmmyyyy_or_iso(planned_end_date)
    except Exception:
        planned_end_date = default_end
        flash(request, "Project end date invalid; defaulted to tomorrow.", "warning")

    if planned_end_date <= planned_start_date:
        planned_end_date = planned_start_date + timedelta(days=1)
        flash(request, "Project end date adjusted to be after start date.", "warning")

    def _truthy(val) -> bool:
        if val is None:
            return False
        if isinstance(val, bool):
            return bool(val)
        s = str(val).strip().lower()
        return s in {"1", "true", "yes", "y", "on"}

    validated_segments: list[dict] = []
    validated_total_length_m: int | None = None
    warnings: list[str] = []
    allow_stretch_create = True

    def add_warning(msg: str) -> None:
        warnings.append(msg)


    # Robust lane count parsing from lane_configuration
    def parse_lane_count(lc: str | None) -> int | None:
        if not lc:
            return None
        lc = lc.strip().upper().replace(' ', '')
        # Handle formats like 2L, 4L, 2X2, 3X3, 2X2L, 4L DIVIDED
        import re
        # Remove words like 'DIVIDED', 'MEDIAN', etc.
        lc = re.sub(r'(DIVIDED|MEDIAN|WITH.*)', '', lc)
        # 2L, 4L, 6L
        m = re.match(r'^(\d+)L$', lc)
        if m:
            return int(m.group(1))
        # 2x2, 3x3, 2X2L, 3X3L
        m = re.match(r'^(\d+)X(\d+)(L)?$', lc)
        if m:
            return int(m.group(1)) * int(m.group(2))
        # Just a number
        m = re.match(r'^(\d+)$', lc)
        if m:
            return int(m.group(1))
        return None

    derived_lanes = parse_lane_count(lane_configuration)

    # Validate conditional requirements
    if project_type == 'Road':
        missing = []
        # Prefer new classification fields
        effective_road_category = (road_category or road_type or '').strip()
        effective_engineering_type = (road_engineering_type or '').strip()

        if not effective_road_category:
            missing.append('Road Category')
        if not effective_engineering_type:
            missing.append('Road Engineering Type')
        if missing:
            logger.warning("Create Project warning (missing road fields): %s", ", ".join(missing))
            add_warning(f"Missing road fields: {', '.join(missing)}. You can update later.")

        if planned_end_date <= planned_start_date:
            add_warning("Project end date should be after start date. Please review timeline.")

        # Strict non-wizard stretch validation
        if not wizard_id:
            if not _truthy(stretch_enabled):
                add_warning("Stretch system is disabled; project will be created without stretches.")
                allow_stretch_create = False

            if not (stretch_segments_json or "").strip():
                add_warning("Stretch segments missing; project will be created without stretches.")
                allow_stretch_create = False

            try:
                segments_raw = json.loads(stretch_segments_json)
            except Exception:
                add_warning("Invalid stretch segments payload; project will be created without stretches.")
                allow_stretch_create = False
                segments_raw = []

            if not isinstance(segments_raw, list) or not segments_raw:
                add_warning("Stretch segments missing; project will be created without stretches.")
                allow_stretch_create = False

            total_length_m = int(round(float(road_length_km or 0.0) * 1000.0))
            if total_length_m <= 0 and segments_raw:
                try:
                    last_end = max(int(s.get("end_m") or 0) for s in segments_raw if isinstance(s, dict))
                    total_length_m = int(last_end)
                except Exception:
                    total_length_m = 0
            if total_length_m <= 0:
                add_warning("Road length (km) not set; project will be created without stretches.")
                allow_stretch_create = False

            validated_total_length_m = total_length_m
            seen_codes: set[str] = set()

            for item in segments_raw[:500]:
                if not isinstance(item, dict):
                    continue

                try:
                    seq = int(item.get("sequence_no") or item.get("sequence") or (len(validated_segments) + 1))
                except Exception:
                    seq = len(validated_segments) + 1

                code = str(item.get("stretch_code") or item.get("code") or f"S{seq:02d}").strip() or f"S{seq:02d}"
                name = str(item.get("stretch_name") or item.get("name") or f"Stretch {seq}").strip() or f"Stretch {seq}"

                try:
                    start_m = int(item.get("start_m"))
                    end_m = int(item.get("end_m"))
                except Exception:
                    add_warning("Invalid stretch segment meters; some stretches skipped.")
                    continue

                ps_raw = item.get("planned_start_date") or item.get("start_date")
                pe_raw = item.get("planned_end_date") or item.get("end_date")
                if not ps_raw or not pe_raw:
                    add_warning("Missing stretch planned dates; using project dates for that stretch.")
                    ps_raw = planned_start_date
                    pe_raw = planned_end_date

                try:
                    seg_planned_start = parse_date_ddmmyyyy_or_iso(str(ps_raw))
                    seg_planned_end = parse_date_ddmmyyyy_or_iso(str(pe_raw))
                except Exception:
                    add_warning("Invalid stretch planned dates; using project dates.")
                    seg_planned_start = planned_start_date
                    seg_planned_end = planned_end_date

                if seg_planned_end < seg_planned_start:
                    add_warning("Stretch planned end date was before start date; corrected to start date.")
                    seg_planned_end = seg_planned_start

                if seg_planned_start < planned_start_date:
                    add_warning("Stretch start was before project start; clamped.")
                    seg_planned_start = planned_start_date
                if seg_planned_end > planned_end_date:
                    add_warning("Stretch end was after project end; clamped.")
                    seg_planned_end = planned_end_date

                if start_m < 0 or end_m <= start_m:
                    add_warning("Invalid stretch chainage range; stretch skipped.")
                    continue

                if code.lower() in seen_codes:
                    add_warning("Duplicate stretch code detected; stretch skipped.")
                    continue
                seen_codes.add(code.lower())

                seg_acts_raw = item.get("activities") or item.get("stretch_activities") or []
                seg_mats_raw = item.get("materials") or item.get("stretch_materials") or []

                seg_acts: list[dict] = []
                if isinstance(seg_acts_raw, list):
                    for a in seg_acts_raw[:500]:
                        if not isinstance(a, dict):
                            continue
                        an = str(a.get("name") or a.get("activity") or "").strip()
                        if not an:
                            continue
                        include = a.get("include")
                        if include is None:
                            include = a.get("enabled")
                        include_b = bool(include) if include is not None else True
                        if not include_b:
                            seg_acts.append({"name": an, "include": False})
                            continue

                        act_ps_raw = a.get("planned_start_date")
                        act_pe_raw = a.get("planned_end_date")
                        if not act_ps_raw or not act_pe_raw:
                            add_warning(f"Activity '{an}' missing dates; using stretch dates.")
                            act_ps_raw = seg_planned_start
                            act_pe_raw = seg_planned_end
                        try:
                            act_ps = parse_date_ddmmyyyy_or_iso(str(act_ps_raw))
                            act_pe = parse_date_ddmmyyyy_or_iso(str(act_pe_raw))
                        except Exception:
                            add_warning(f"Invalid planned dates for activity '{an}'; using stretch dates.")
                            act_ps = seg_planned_start
                            act_pe = seg_planned_end
                        if act_pe < act_ps:
                            add_warning(f"Activity '{an}' end date was before start date; corrected.")
                            act_pe = act_ps
                        if act_ps < seg_planned_start:
                            add_warning(f"Activity '{an}' start before stretch; clamped.")
                            act_ps = seg_planned_start
                        if act_pe > seg_planned_end:
                            add_warning(f"Activity '{an}' end after stretch; clamped.")
                            act_pe = seg_planned_end

                        hrs_raw = a.get("planned_duration_hours")
                        if hrs_raw is None:
                            hrs_raw = a.get("duration_hours")
                        hrs_val = None
                        if hrs_raw is not None and str(hrs_raw).strip() != "":
                            try:
                                hrs_val = float(hrs_raw)
                            except Exception:
                                hrs_val = None

                        planned_start_time = a.get("start_time", None)
                        planned_end_time = a.get("end_time", None)
                        if planned_start_time is not None:
                            planned_start_time = str(planned_start_time).strip() or None
                        if planned_end_time is not None:
                            planned_end_time = str(planned_end_time).strip() or None

                        seg_acts.append(
                            {
                                "name": an,
                                "include": True,
                                "planned_start_date": act_ps,
                                "planned_end_date": act_pe,
                                "planned_duration_hours": hrs_val,
                                "start_time": planned_start_time,
                                "end_time": planned_end_time,
                            }
                        )

                seg_mats: list[dict] = []
                if isinstance(seg_mats_raw, list):
                    for m in seg_mats_raw[:500]:
                        if not isinstance(m, dict):
                            continue
                        mn = str(m.get("name") or m.get("material") or "").strip()
                        if not mn:
                            continue
                        include = m.get("include")
                        if include is None:
                            include = m.get("enabled")
                        include_b = bool(include) if include is not None else True
                        qty_raw = m.get("quantity")
                        if qty_raw is None:
                            qty_raw = m.get("planned_quantity")

                        qty_val = None
                        if include_b:
                            if qty_raw is None or str(qty_raw).strip() == "":
                                qty_val = None
                            else:
                                try:
                                    qty_val = Decimal(str(qty_raw))
                                except InvalidOperation:
                                    add_warning(f"Invalid quantity for material '{mn}'; material skipped.")
                                    continue
                                if qty_val < 0:
                                    add_warning(f"Material '{mn}' quantity cannot be negative; material skipped.")
                                    continue
                                if qty_val.as_tuple().exponent < -5:
                                    add_warning(f"Material '{mn}' quantity supports max 5 decimals; material skipped.")
                                    continue

                        seg_mats.append({"name": mn, "include": include_b, "quantity": qty_val})

                validated_segments.append(
                    {
                        "sequence_no": seq,
                        "stretch_code": code,
                        "stretch_name": name,
                        "start_m": start_m,
                        "end_m": end_m,
                        "length_m": int(end_m - start_m),
                        "planned_start_date": seg_planned_start,
                        "planned_end_date": seg_planned_end,
                        "activities": seg_acts,
                        "materials": seg_mats,
                    }
                )

            validated_segments = sorted(validated_segments, key=lambda s: int(s.get("sequence_no") or 0))
            if not validated_segments:
                add_warning("No valid stretch segments; project will be created without stretches.")
                allow_stretch_create = False

            last_end = None
            for seg in validated_segments:
                if last_end is None and int(seg["start_m"]) != 0:
                    add_warning("First stretch does not start at 0; stretch creation skipped.")
                    allow_stretch_create = False
                    break
                if last_end is not None and int(seg["start_m"]) != int(last_end):
                    add_warning("Stretch segments are not continuous; stretch creation skipped.")
                    allow_stretch_create = False
                    break
                last_end = int(seg["end_m"])

            if allow_stretch_create and int(last_end or 0) != int(total_length_m):
                add_warning("Stretch segments do not match total length; stretch creation skipped.")
                allow_stretch_create = False

    # For non-road projects, provide safe defaults for non-nullable DB columns
    # Store legacy `road_type` as the selected Road Category for compatibility.
    safe_road_type = (road_category or road_type or project_type or "Road")
    safe_lanes = derived_lanes or 0
    safe_road_width = road_width or 0.0
    if not road_length_km and validated_total_length_m:
        road_length_km = float(validated_total_length_m) / 1000.0
    safe_road_length_km = road_length_km or 0.0

    project = Project(
        name=name,
        project_code=project_code or None,
        client_authority=client_authority or None,
        contractor=contractor or None,
        consultant_pmc=consultant_pmc or None,
        road_type=safe_road_type,
        project_type=project_type,
        road_construction_type=road_construction_type or None,
        road_name=(road_name or None),
        lane_configuration=(lane_configuration or None),
        road_pavement_type=(road_pavement_type or None),
        terrain_type=(terrain_type or None),
        concrete_pavement_type=(pavement_type or None),
        slab_thickness_mm=slab_thickness_mm,
        grade_of_concrete=(grade_of_concrete or None),
        joint_spacing_m=joint_spacing_m,
        dowel_diameter_mm=dowel_diameter_mm,
        tie_bar_diameter_mm=tie_bar_diameter_mm,
        road_category=(road_category or safe_road_type) or None,
        road_engineering_type=(road_engineering_type or None),
        road_extras_json=road_extras_json or None,
        lanes=derived_lanes or 0,
        road_width=safe_road_width,
        carriageway_width=carriageway_width or None,
        shoulder_type=shoulder_type or None,
        median_type=median_type or None,
        road_length_km=safe_road_length_km,
        country=country,
        state=state or None,
        district=district or None,
        city=city,
        chainage_start=chainage_start or None,
        chainage_end=chainage_end or None,
        planned_start_date=planned_start_date,
        planned_end_date=planned_end_date,
        created_by=user["id"],
        is_active=True,
        status="active",
    )

    db.add(project)
    try:
        db.commit()
        # Refresh to get id
        db.refresh(project)
    except Exception as exc:
        db.rollback()
        logger.exception("Create Project failed during commit")
        flash(request, f"Failed to create project: {str(exc)}", "error")
        return RedirectResponse('/projects/new', status_code=302)

    # Audit: Project CREATE (best-effort)
    log_action(
        db=db,
        request=request,
        action="CREATE",
        entity_type="Project",
        entity_id=project.id,
        description="Project created",
        old_value=None,
        new_value=model_to_dict(project),
    )

    if warnings:
        for msg in warnings[:10]:
            flash(request, msg, "warning")

    # Auto-create activity presets for certain road construction types
    try:
        _create_road_activity_presets(db, project)
        db.commit()
    except Exception:
        db.rollback()

    # Preset insertion
    def _safe_parse_json_list(raw: str | None) -> list[str]:
        if not raw:
            return []
        try:
            value = json.loads(raw)
            if isinstance(value, list):
                return [str(v) for v in value]
        except Exception:
            return []
        return []

    def _safe_parse_json_material_defs(raw: str | None) -> list[dict]:
        if not raw:
            return []
        try:
            value = json.loads(raw)
            if isinstance(value, list):
                out: list[dict] = []
                for item in value[:500]:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name") or "").strip()
                    if not name:
                        continue
                    # support both keys
                    unit = str(item.get("default_unit") or item.get("unit") or "unit").strip() or "unit"
                    allowed_raw = item.get("allowed_units")
                    allowed: list[str] = []
                    if isinstance(allowed_raw, list):
                        allowed = [str(u or "").strip() for u in allowed_raw]
                        allowed = [u for u in allowed if u]
                    if not allowed:
                        allowed = [unit]
                    if unit not in allowed:
                        allowed.insert(0, unit)
                    out.append({
                        "name": name[:150],
                        "default_unit": unit[:50],
                        "allowed_units": allowed[:50],
                    })
                return out
        except Exception:
            return []
        return []

    def _safe_parse_json_activity_defs(raw: str | None) -> list[dict]:
        if not raw:
            return []
        try:
            value = json.loads(raw)
            if isinstance(value, list):
                out: list[dict] = []
                for item in value[:500]:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name") or "").strip()
                    if not name:
                        continue
                    start_time = str(item.get("start_time") or "").strip() or None
                    end_time = str(item.get("end_time") or "").strip() or None
                    enabled = bool(item.get("enabled", True))

                    raw_scope = item.get("activity_scope")
                    if raw_scope is None:
                        raw_scope = item.get("scope")
                    scope = str(raw_scope or "").strip().upper() or None
                    if scope not in {"COMMON", "STRETCH"}:
                        scope = None

                    phase = str(item.get("phase") or "").strip() or None
                    out.append(
                        {
                            "name": name[:150],
                            "start_time": start_time[:10] if start_time else None,
                            "end_time": end_time[:10] if end_time else None,
                            "enabled": enabled,
                            "activity_scope": scope,
                            "phase": phase[:80] if phase else None,
                        }
                    )
                return out
        except Exception:
            return []
        return []

    def _safe_parse_project_team(raw: str | None) -> list[dict]:
        if not raw:
            return []
        try:
            value = json.loads(raw)
            if isinstance(value, list):
                out: list[dict] = []
                for item in value[:200]:
                    if not isinstance(item, dict):
                        continue
                    try:
                        uid = int(item.get("user_id") or 0)
                    except Exception:
                        uid = 0
                    role_in_project = str(item.get("role_in_project") or "member").strip() or "member"
                    if uid <= 0:
                        continue
                    out.append({"user_id": uid, "role_in_project": role_in_project[:50]})
                return out
        except Exception:
            return []
        return []

    def _sanitize_names(values: list[str], max_items: int = 200) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for v in values[:max_items]:
            name = (v or "").strip()
            if not name:
                continue
            name = name[:150]
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(name)
        return out

    # Detailed type presets are defined in app/utils/project_type_presets.py

    try:
        if project_type == "Road":
            # If wizard provides a concrete preset_key, snapshot it for admin safety checks.
            try:
                if (road_extras_json or "").strip():
                    extras = json.loads(road_extras_json)
                    if isinstance(extras, dict):
                        pk = str(extras.get("preset_key") or "").strip() or None
                        if pk:
                            project.road_preset_key = pk
            except Exception:
                pass

            road_preset = get_road_preset(
                road_category=road_category,
                road_engineering_type=road_engineering_type,
                road_extras_json=road_extras_json,
                db=db,
            )
            preset_def = (
                {"activities": list(road_preset.activities), "materials": list(road_preset.materials)}
                if road_preset
                else get_presets_for_engineering_type(road_engineering_type)
            )
            standard_activity_set = {str(a).strip() for a in preset_def.get("activities", [])}

            next_act_code = activity_code_allocator(db, Activity, project_id=int(project.id), width=6, project_width=6)

            activity_defs = _safe_parse_json_activity_defs(activity_preset_defs_json)
            activity_defs_by_name = {str(d.get("name") or "").strip().lower(): d for d in activity_defs}
            selected_activities_from_defs = [
                str(d.get("name") or "").strip()
                for d in activity_defs
                if bool(d.get("enabled", True)) and str(d.get("name") or "").strip()
            ]

            selected_activities_from_json = _sanitize_names(_safe_parse_json_list(activity_presets_json))
            selected_activities = (
                _sanitize_names(selected_activities_from_defs)
                or selected_activities_from_json
                or (activity_presets or list(preset_def.get("activities", [])))
            )

            for act_name in selected_activities:
                exists = (
                    db.query(Activity)
                    .filter(Activity.project_id == project.id, Activity.name == act_name)
                    .first()
                )
                if not exists:
                    d = activity_defs_by_name.get(str(act_name or "").strip().lower())
                    db.add(
                        Activity(
                            name=act_name,
                            is_standard=(act_name in standard_activity_set),
                            project_id=project.id,
                            code=next_act_code(),
                            default_start_time=(d.get("start_time") if isinstance(d, dict) else None),
                            default_end_time=(d.get("end_time") if isinstance(d, dict) else None),
                        )
                    )

            # Materials: UI sends a JSON list of names (optional). Otherwise fall back to checkbox values.
            preset_materials = preset_def.get("materials", [])
            preset_material_by_name = {
                m.name: {
                    "name": m.name,
                    "default_unit": m.default_unit,
                    "allowed_units": list(m.allowed_units),
                }
                for m in preset_materials
            }

            # Prefer full material defs payload (supports unit editing)
            selected_material_defs_from_json = _safe_parse_json_material_defs(material_preset_defs_json)
            if selected_material_defs_from_json:
                selected_material_defs = selected_material_defs_from_json
            else:
                selected_material_names = _sanitize_names(_safe_parse_json_list(material_presets_json))
                if not selected_material_names:
                    selected_material_names = list(material_presets or [m.name for m in preset_materials])

                selected_material_defs = [
                    preset_material_by_name.get(
                        n,
                        {"name": n, "default_unit": "unit", "allowed_units": ["unit"]},
                    )
                    for n in selected_material_names
                ]

            # Explicit storage of selected presets
            try:
                project.preset_activities_json = json.dumps(selected_activities)
                project.preset_materials_json = json.dumps(selected_material_defs)
                if road_preset and not getattr(project, "road_preset_key", None):
                    project.road_preset_key = getattr(road_preset, "preset_key", None)
                db.add(project)
                db.commit()
            except Exception:
                db.rollback()

            for mdef in selected_material_defs:
                mat_name = str(mdef.get("name") or "").strip()
                if not mat_name:
                    continue
                unit = str(mdef.get("default_unit") or mdef.get("unit") or "unit").strip() or "unit"
                allowed_units = mdef.get("allowed_units")
                if not isinstance(allowed_units, list) or not allowed_units:
                    allowed_units = [unit]
                allowed_units = [str(u or "").strip() for u in allowed_units]
                allowed_units = [u for u in allowed_units if u]
                if unit not in allowed_units:
                    allowed_units.insert(0, unit)

                mat = db.query(Material).filter(Material.name == mat_name).first()
                if not mat:
                    mat = Material(
                        name=mat_name,
                        unit=unit,
                        standard_unit=unit,
                        allowed_units=json.dumps(allowed_units),
                    )
                    db.add(mat)
                    db.commit()
                    db.refresh(mat)
                else:
                    # Do not overwrite existing config unless missing
                    changed = False
                    if getattr(mat, "standard_unit", None) in (None, "") and unit:
                        mat.standard_unit = unit
                        changed = True
                    if getattr(mat, "allowed_units", None) in (None, "") and allowed_units:
                        mat.allowed_units = json.dumps(allowed_units)
                        changed = True
                    if changed:
                        db.add(mat)
                        db.commit()

                pm_exists = (
                    db.query(PlannedMaterial)
                    .filter(
                        PlannedMaterial.project_id == project.id,
                        PlannedMaterial.material_id == mat.id,
                        PlannedMaterial.stretch_id == None,  # noqa: E711
                    )
                    .first()
                )
                if not pm_exists:
                    db.add(
                        PlannedMaterial(
                            project_id=project.id,
                            material_id=mat.id,
                            stretch_id=None,
                            unit=unit,
                            allowed_units=json.dumps(allowed_units),
                            planned_quantity=Decimal("0"),
                        )
                    )
                else:
                    changed_pm = False
                    if not getattr(pm_exists, "unit", None):
                        pm_exists.unit = unit
                        changed_pm = True
                    if not getattr(pm_exists, "allowed_units", None):
                        pm_exists.allowed_units = json.dumps(allowed_units)
                        changed_pm = True
                    if changed_pm:
                        db.add(pm_exists)

            db.commit()

            # ---------------- STRETCH SYSTEM (wizard-driven) ----------------
            # Best-effort: project creation should succeed even if stretch setup fails.
            def _truthy(val) -> bool:
                if val is None:
                    return False
                if isinstance(val, bool):
                    return bool(val)
                s = str(val).strip().lower()
                return s in {"1", "true", "yes", "y", "on"}

            try:
                wizard_state = None
                if wizard_id:
                    wizard_state = wizard_get_state(db, wizard_id=int(wizard_id), user_id=int(user["id"]))

                if wizard_state and _truthy(wizard_state.data.get("stretch_enabled")):
                    segments_raw = wizard_state.data.get("stretch_segments")
                    total_length_m = wizard_state.data.get("stretch_total_length_m")

                    if isinstance(segments_raw, list) and segments_raw:
                        # Ensure ProjectActivity rows exist so StretchActivity mapping can reference them.
                        acts = (
                            db.query(Activity)
                            .filter(Activity.project_id == project.id, Activity.is_active == True)  # noqa: E712
                            .order_by(Activity.id.asc())
                            .all()
                        )
                        for act in acts:
                            d = activity_defs_by_name.get(str(getattr(act, "name", "") or "").strip().lower())
                            scope = "STRETCH"
                            if isinstance(d, dict):
                                raw_scope = d.get("activity_scope")
                                if raw_scope is None:
                                    raw_scope = d.get("scope")
                                scope_candidate = str(raw_scope or "").strip().upper()
                                if scope_candidate in {"COMMON", "STRETCH"}:
                                    scope = scope_candidate

                            pa_exists = (
                                db.query(ProjectActivity)
                                .filter(
                                    ProjectActivity.project_id == project.id,
                                    ProjectActivity.activity_id == act.id,
                                )
                                .first()
                            )
                            if not pa_exists:
                                db.add(
                                    ProjectActivity(
                                        project_id=int(project.id),
                                        activity_id=int(act.id),
                                        planned_quantity=0.0,
                                        unit=str(getattr(act, "display_unit", None) or "unit"),
                                        start_date=project.planned_start_date,
                                        end_date=project.planned_end_date,
                                        activity_scope=scope,
                                    )
                                )
                            else:
                                # Apply scope from preset defs (best-effort)
                                try:
                                    pa_exists.activity_scope = scope
                                    db.add(pa_exists)
                                except Exception:
                                    pass
                        db.commit()

                        # Deactivate any existing stretches for safety (should be none for new projects).
                        db.query(RoadStretch).filter(
                            RoadStretch.project_id == int(project.id),
                            RoadStretch.is_active == True,  # noqa: E712
                        ).update({RoadStretch.is_active: False})

                        # Validate & persist stretches
                        created_stretches = 0
                        seen_codes: set[str] = set()
                        segments: list[dict] = []
                        for item in segments_raw[:500]:
                            if not isinstance(item, dict):
                                continue
                            try:
                                start_m = int(item.get("start_m"))
                                end_m = int(item.get("end_m"))
                            except Exception:
                                continue

                            seq = int(item.get("sequence_no") or (len(segments) + 1))
                            code = str(item.get("stretch_code") or f"ST-{seq:03d}").strip() or f"ST-{seq:03d}"
                            name = str(item.get("stretch_name") or "").strip() or f"Stretch {seq}"

                            ps_raw = item.get("planned_start_date") or item.get("start_date")
                            pe_raw = item.get("planned_end_date") or item.get("end_date")
                            if not ps_raw or not pe_raw:
                                raise ValueError("Each stretch must have planned start and end dates")

                            try:
                                seg_planned_start = parse_date_ddmmyyyy_or_iso(str(ps_raw))
                                seg_planned_end = parse_date_ddmmyyyy_or_iso(str(pe_raw))
                            except Exception:
                                raise ValueError("Invalid stretch planned dates. Use DD/MM/YYYY.")

                            if seg_planned_end < seg_planned_start:
                                raise ValueError("Stretch planned end date must be after start date")

                            if seg_planned_start < planned_start_date or seg_planned_end > planned_end_date:
                                raise ValueError("Stretch dates must be within project dates")

                            if start_m < 0 or end_m <= start_m:
                                raise ValueError("Invalid stretch chainage range")
                            if code.lower() in seen_codes:
                                raise ValueError("Duplicate stretch code")
                            seen_codes.add(code.lower())

                            seg_acts_raw = item.get("activities") or item.get("stretch_activities") or []
                            seg_mats_raw = item.get("materials") or item.get("stretch_materials") or []

                            seg_acts: list[dict] = []
                            if isinstance(seg_acts_raw, list):
                                for a in seg_acts_raw[:500]:
                                    if not isinstance(a, dict):
                                        continue
                                    an = str(a.get("name") or a.get("activity") or "").strip()
                                    if not an:
                                        continue
                                    include = a.get("include")
                                    if include is None:
                                        include = a.get("enabled")
                                    include_b = bool(include) if include is not None else True
                                    if not include_b:
                                        seg_acts.append({"name": an, "include": False})
                                        continue

                                    act_ps_raw = a.get("planned_start_date")
                                    act_pe_raw = a.get("planned_end_date")
                                    if not act_ps_raw or not act_pe_raw:
                                        raise ValueError(f"Activity '{an}' must have planned start and end dates")
                                    try:
                                        act_ps = parse_date_ddmmyyyy_or_iso(str(act_ps_raw))
                                        act_pe = parse_date_ddmmyyyy_or_iso(str(act_pe_raw))
                                    except Exception:
                                        raise ValueError(f"Invalid planned dates for activity '{an}'")
                                    if act_pe < act_ps:
                                        raise ValueError(f"Activity '{an}' end date must be after start date")
                                    if act_ps < seg_planned_start or act_pe > seg_planned_end:
                                        raise ValueError(f"Activity '{an}' dates must be within stretch dates")

                                    hrs_raw = a.get("planned_duration_hours")
                                    if hrs_raw is None:
                                        hrs_raw = a.get("duration_hours")
                                    hrs_val = None
                                    if hrs_raw is not None and str(hrs_raw).strip() != "":
                                        try:
                                            hrs_val = float(hrs_raw)
                                        except Exception:
                                            hrs_val = None

                                    planned_start_time = a.get("start_time", None)
                                    planned_end_time = a.get("end_time", None)
                                    if planned_start_time is not None:
                                        planned_start_time = str(planned_start_time).strip() or None
                                    if planned_end_time is not None:
                                        planned_end_time = str(planned_end_time).strip() or None

                                    seg_acts.append(
                                        {
                                            "name": an,
                                            "include": True,
                                            "planned_start_date": act_ps,
                                            "planned_end_date": act_pe,
                                            "planned_duration_hours": hrs_val,
                                            "start_time": planned_start_time,
                                            "end_time": planned_end_time,
                                        }
                                    )

                            seg_mats: list[dict] = []
                            if isinstance(seg_mats_raw, list):
                                for m in seg_mats_raw[:500]:
                                    if not isinstance(m, dict):
                                        continue
                                    mn = str(m.get("name") or m.get("material") or "").strip()
                                    if not mn:
                                        continue
                                    include = m.get("include")
                                    if include is None:
                                        include = m.get("enabled")
                                    include_b = bool(include) if include is not None else True
                                    qty_raw = m.get("quantity")
                                    if qty_raw is None:
                                        qty_raw = m.get("planned_quantity")

                                    qty_val = None
                                    if include_b:
                                        if qty_raw is None or str(qty_raw).strip() == "":
                                            raise ValueError(f"Material '{mn}' requires a quantity")
                                        try:
                                            qty_val = Decimal(str(qty_raw))
                                        except InvalidOperation:
                                            raise ValueError(f"Invalid quantity for material '{mn}'")
                                        if qty_val < 0:
                                            raise ValueError(f"Material '{mn}' quantity cannot be negative")
                                        if qty_val.as_tuple().exponent < -5:
                                            raise ValueError(f"Material '{mn}' quantity supports max 5 decimal places")

                                    seg_mats.append({"name": mn, "include": include_b, "quantity": qty_val})

                            segments.append(
                                {
                                    "sequence_no": seq,
                                    "stretch_code": code,
                                    "stretch_name": name,
                                    "start_m": start_m,
                                    "end_m": end_m,
                                    "length_m": int(end_m - start_m),
                                    "planned_start_date": seg_planned_start,
                                    "planned_end_date": seg_planned_end,
                                    "activities": seg_acts,
                                    "materials": seg_mats,
                                }
                            )

                        segments = sorted(segments, key=lambda s: int(s.get("sequence_no") or 0))
                        if not segments:
                            raise ValueError("No stretch segments")

                        last_end = None
                        for seg in segments:
                            if last_end is None and int(seg["start_m"]) != 0:
                                raise ValueError("First stretch must start at 0")
                            if last_end is not None and int(seg["start_m"]) != int(last_end):
                                raise ValueError("Stretch segments must be continuous")
                            last_end = int(seg["end_m"])

                        if total_length_m is not None and int(last_end or 0) != int(total_length_m):
                            raise ValueError("Stretch segments do not match total length")

                        for seg in segments:
                            db.add(
                                RoadStretch(
                                    project_id=int(project.id),
                                    stretch_code=str(seg["stretch_code"]),
                                    stretch_name=str(seg["stretch_name"]),
                                    start_chainage=chainage_from_meters(int(seg["start_m"])),
                                    end_chainage=chainage_from_meters(int(seg["end_m"])),
                                    length_m=int(seg["length_m"]),
                                    sequence_no=int(seg["sequence_no"]),
                                    planned_start_date=seg.get("planned_start_date"),
                                    planned_end_date=seg.get("planned_end_date"),
                                    is_active=True,
                                )
                            )
                            created_stretches += 1

                        db.commit()

                        # Create stretch-wise activity rows (best-effort; uses separate DB session internally)
                        try:
                            apply_activities_to_stretches(int(project.id), mode="ALL")
                        except Exception:
                            logger.exception("Stretch activity mapping failed (project_id=%s)", project.id)

                        # Apply per-stretch overrides (best-effort)
                        try:
                            active_stretches = (
                                db.query(RoadStretch)
                                .filter(
                                    RoadStretch.project_id == int(project.id),
                                    RoadStretch.is_active == True,  # noqa: E712
                                )
                                .all()
                            )
                            stretch_by_code = {str(s.stretch_code or "").strip().lower(): s for s in active_stretches}

                            pa_rows = (
                                db.query(ProjectActivity, Activity)
                                .join(Activity, Activity.id == ProjectActivity.activity_id)
                                .filter(ProjectActivity.project_id == int(project.id))
                                .all()
                            )
                            pa_by_name = {str(a.name or "").strip().lower(): pa for (pa, a) in pa_rows if a and (a.name or "").strip()}

                            mat_rows = (
                                db.query(PlannedMaterial, Material)
                                .join(Material, Material.id == PlannedMaterial.material_id)
                                .filter(
                                    PlannedMaterial.project_id == int(project.id),
                                    PlannedMaterial.stretch_id == None,  # noqa: E711
                                )
                                .all()
                            )
                            material_id_by_name = {str(m.name or "").strip().lower(): int(m.id) for (pm, m) in mat_rows if m and (m.name or "").strip()}
                            planned_by_material_id = {int(pm.material_id): pm for (pm, m) in mat_rows if pm}

                            for seg in segments:
                                stretch = stretch_by_code.get(str(seg.get("stretch_code") or "").strip().lower())
                                if not stretch:
                                    continue

                                # Activities: include/exclude + duration hours
                                for ao in (seg.get("activities") or []):
                                    if not isinstance(ao, dict):
                                        continue
                                    aname = str(ao.get("name") or "").strip()
                                    if not aname:
                                        continue
                                    key = aname.lower()
                                    include = bool(ao.get("include"))
                                    hrs = ao.get("planned_duration_hours")
                                    planned_start_time = ao.get("start_time")
                                    planned_end_time = ao.get("end_time")
                                    if planned_start_time is not None:
                                        planned_start_time = str(planned_start_time).strip() or None
                                    if planned_end_time is not None:
                                        planned_end_time = str(planned_end_time).strip() or None

                                    pa = pa_by_name.get(key)
                                    if pa is None and include:
                                        # Create a new STRETCH-scoped activity only for this project (used for this stretch)
                                        new_act = Activity(
                                            project_id=int(project.id),
                                            code=activity_code_allocator(int(project.id), aname),
                                            name=str(aname),
                                            default_start_time=None,
                                            default_end_time=None,
                                            is_standard=False,
                                            is_active=True,
                                        )
                                        db.add(new_act)
                                        db.flush()
                                        new_pa = ProjectActivity(
                                            project_id=int(project.id),
                                            activity_id=int(new_act.id),
                                            planned_quantity=0.0,
                                            unit=str(getattr(new_act, "display_unit", None) or "hours"),
                                            start_date=project.planned_start_date,
                                            end_date=project.planned_end_date,
                                            activity_scope="STRETCH",
                                            default_duration_hours=float(hrs) if hrs is not None else None,
                                        )
                                        db.add(new_pa)
                                        db.flush()
                                        pa = new_pa
                                        pa_by_name[key] = pa

                                    if pa is None:
                                        continue

                                    sa = (
                                        db.query(StretchActivity)
                                        .filter(
                                            StretchActivity.stretch_id == int(stretch.id),
                                            StretchActivity.project_activity_id == int(pa.id),
                                        )
                                        .first()
                                    )

                                    if not include:
                                        if sa is not None:
                                            sa.is_active = False
                                            db.add(sa)
                                        continue

                                    act_start_raw = ao.get("planned_start_date") or seg.get("planned_start_date")
                                    act_end_raw = ao.get("planned_end_date") or seg.get("planned_end_date")
                                    act_start = parse_date_ddmmyyyy_or_iso(str(act_start_raw)) if act_start_raw else None
                                    act_end = parse_date_ddmmyyyy_or_iso(str(act_end_raw)) if act_end_raw else None

                                    if sa is None:
                                        sa = StretchActivity(
                                            stretch_id=int(stretch.id),
                                            project_activity_id=int(pa.id),
                                            planned_start_date=act_start,
                                            planned_end_date=act_end,
                                            planned_duration_hours=float(hrs) if hrs is not None else None,
                                            planned_start_time=planned_start_time,
                                            planned_end_time=planned_end_time,
                                            planned_quantity=None,
                                            actual_quantity=None,
                                            progress_percent=None,
                                            is_active=True,
                                        )
                                        db.add(sa)
                                    else:
                                        sa.is_active = True
                                        sa.planned_start_time = planned_start_time
                                        sa.planned_end_time = planned_end_time
                                        if act_start is not None:
                                            sa.planned_start_date = act_start
                                        if act_end is not None:
                                            sa.planned_end_date = act_end
                                        if hrs is not None:
                                            sa.planned_duration_hours = float(hrs)
                                        db.add(sa)

                                # Materials: store per-stretch quantities + exclusions
                                for mo in (seg.get("materials") or []):
                                    if not isinstance(mo, dict):
                                        continue
                                    mname = str(mo.get("name") or "").strip()
                                    if not mname:
                                        continue
                                    mid = material_id_by_name.get(mname.lower())
                                    if not mid:
                                        continue
                                    include = bool(mo.get("include"))
                                    qty_raw = mo.get("quantity")
                                    if qty_raw is None:
                                        qty_raw = mo.get("planned_quantity")

                                    existing = (
                                        db.query(StretchMaterialExclusion)
                                        .filter(
                                            StretchMaterialExclusion.stretch_id == int(stretch.id),
                                            StretchMaterialExclusion.material_id == int(mid),
                                        )
                                        .first()
                                    )

                                    if include:
                                        if existing is not None:
                                            db.delete(existing)
                                        base_pm = planned_by_material_id.get(int(mid))
                                        if base_pm:
                                            unit_locked = str(getattr(base_pm, "unit", None) or "unit").strip() or "unit"
                                            allowed_locked = base_pm.get_allowed_units() if hasattr(base_pm, "get_allowed_units") else [unit_locked]
                                        else:
                                            unit_locked = "unit"
                                            allowed_locked = [unit_locked]

                                        try:
                                            qty_val = Decimal(str(qty_raw))
                                        except InvalidOperation:
                                            qty_val = Decimal("0")

                                        pm_stretch = (
                                            db.query(PlannedMaterial)
                                            .filter(
                                                PlannedMaterial.project_id == int(project.id),
                                                PlannedMaterial.material_id == int(mid),
                                                PlannedMaterial.stretch_id == int(stretch.id),
                                            )
                                            .first()
                                        )
                                        if not pm_stretch:
                                            pm_stretch = PlannedMaterial(
                                                project_id=int(project.id),
                                                material_id=int(mid),
                                                stretch_id=int(stretch.id),
                                                unit=unit_locked,
                                                allowed_units=json.dumps(allowed_locked),
                                                planned_quantity=qty_val,
                                            )
                                        else:
                                            pm_stretch.planned_quantity = qty_val
                                            pm_stretch.unit = unit_locked
                                            pm_stretch.allowed_units = json.dumps(allowed_locked)
                                        db.add(pm_stretch)
                                    else:
                                        if existing is None:
                                            db.add(
                                                StretchMaterialExclusion(
                                                    stretch_id=int(stretch.id),
                                                    material_id=int(mid),
                                                )
                                            )

                            db.commit()
                        except Exception:
                            db.rollback()
                            logger.exception("Failed to apply per-stretch overrides (project_id=%s)", project.id)

                        flash(request, f"Stretch system enabled: created {created_stretches} stretch(es).", "success")

                # ---------------- STRETCH SYSTEM (non-wizard create form) ----------------
                # Road projects must provide explicit stretch segments (no auto-generation).
                if (not wizard_state) and _truthy(stretch_enabled) and allow_stretch_create:
                    segments = list(validated_segments or [])
                    if not segments:
                        raise ValueError("Stretch segments are required for Road projects")

                    total_length_m2 = int(validated_total_length_m or 0)
                    if total_length_m2 <= 0:
                        raise ValueError("Road length (km) must be set to generate stretches")

                    db.query(RoadStretch).filter(
                        RoadStretch.project_id == int(project.id),
                        RoadStretch.is_active == True,  # noqa: E712
                    ).update({RoadStretch.is_active: False})

                    created_stretches = 0
                    for seg in segments:
                        db.add(
                            RoadStretch(
                                project_id=int(project.id),
                                stretch_code=str(seg["stretch_code"]),
                                stretch_name=str(seg["stretch_name"]),
                                start_chainage=chainage_from_meters(int(seg["start_m"])),
                                end_chainage=chainage_from_meters(int(seg["end_m"])),
                                length_m=int(seg["length_m"]),
                                sequence_no=int(seg["sequence_no"]),
                                planned_start_date=seg.get("planned_start_date"),
                                planned_end_date=seg.get("planned_end_date"),
                                is_active=True,
                            )
                        )
                        created_stretches += 1

                    db.commit()

                    # Ensure ProjectActivity rows exist with correct scope so stretch cloning works.
                    try:
                        acts = (
                            db.query(Activity)
                            .filter(Activity.project_id == project.id, Activity.is_active == True)  # noqa: E712
                            .order_by(Activity.id.asc())
                            .all()
                        )
                        for act in acts:
                            d = activity_defs_by_name.get(str(getattr(act, "name", "") or "").strip().lower())
                            scope = "STRETCH"
                            if isinstance(d, dict):
                                raw_scope = d.get("activity_scope")
                                if raw_scope is None:
                                    raw_scope = d.get("scope")
                                scope_candidate = str(raw_scope or "").strip().upper()
                                if scope_candidate in {"COMMON", "STRETCH"}:
                                    scope = scope_candidate

                            pa_exists = (
                                db.query(ProjectActivity)
                                .filter(
                                    ProjectActivity.project_id == project.id,
                                    ProjectActivity.activity_id == act.id,
                                )
                                .first()
                            )
                            if not pa_exists:
                                db.add(
                                    ProjectActivity(
                                        project_id=int(project.id),
                                        activity_id=int(act.id),
                                        planned_quantity=0.0,
                                        unit=str(getattr(act, "display_unit", None) or "unit"),
                                        start_date=project.planned_start_date,
                                        end_date=project.planned_end_date,
                                        activity_scope=scope,
                                    )
                                )
                            else:
                                try:
                                    pa_exists.activity_scope = scope
                                    db.add(pa_exists)
                                except Exception:
                                    pass

                        db.commit()
                    except Exception:
                        db.rollback()

                    try:
                        apply_activities_to_stretches(int(project.id), mode="ALL")
                    except Exception:
                        logger.exception("Stretch activity mapping failed (project_id=%s)", project.id)

                    # Apply per-stretch overrides (best-effort)
                    try:
                        active_stretches = (
                            db.query(RoadStretch)
                            .filter(
                                RoadStretch.project_id == int(project.id),
                                RoadStretch.is_active == True,  # noqa: E712
                            )
                            .all()
                        )
                        stretch_by_code = {str(s.stretch_code or "").strip().lower(): s for s in active_stretches}

                        pa_rows = (
                            db.query(ProjectActivity, Activity)
                            .join(Activity, Activity.id == ProjectActivity.activity_id)
                            .filter(ProjectActivity.project_id == int(project.id))
                            .all()
                        )
                        pa_by_name = {str(a.name or "").strip().lower(): pa for (pa, a) in pa_rows if a and (a.name or "").strip()}

                        mat_rows = (
                            db.query(PlannedMaterial, Material)
                            .join(Material, Material.id == PlannedMaterial.material_id)
                            .filter(
                                PlannedMaterial.project_id == int(project.id),
                                PlannedMaterial.stretch_id == None,  # noqa: E711
                            )
                            .all()
                        )
                        material_id_by_name = {str(m.name or "").strip().lower(): int(m.id) for (pm, m) in mat_rows if m and (m.name or "").strip()}
                        planned_by_material_id = {int(pm.material_id): pm for (pm, m) in mat_rows if pm}

                        for seg in segments:
                            stretch = stretch_by_code.get(str(seg.get("stretch_code") or "").strip().lower())
                            if not stretch:
                                continue

                            # Activities: include/exclude + duration hours
                            for ao in (seg.get("activities") or []):
                                if not isinstance(ao, dict):
                                    continue
                                aname = str(ao.get("name") or "").strip()
                                if not aname:
                                    continue
                                key = aname.lower()
                                include = bool(ao.get("include"))
                                hrs = ao.get("planned_duration_hours")
                                planned_start_time = ao.get("start_time")
                                planned_end_time = ao.get("end_time")
                                if planned_start_time is not None:
                                    planned_start_time = str(planned_start_time).strip() or None
                                if planned_end_time is not None:
                                    planned_end_time = str(planned_end_time).strip() or None

                                pa = pa_by_name.get(key)
                                if pa is None and include:
                                    # Create a new STRETCH-scoped activity only for this project (used for this stretch)
                                    new_act = Activity(
                                        project_id=int(project.id),
                                        code=activity_code_allocator(int(project.id), aname),
                                        name=str(aname),
                                        default_start_time=None,
                                        default_end_time=None,
                                        is_standard=False,
                                        is_active=True,
                                    )
                                    db.add(new_act)
                                    db.flush()
                                    new_pa = ProjectActivity(
                                        project_id=int(project.id),
                                        activity_id=int(new_act.id),
                                        planned_quantity=0.0,
                                        unit=str(getattr(new_act, "display_unit", None) or "hours"),
                                        start_date=project.planned_start_date,
                                        end_date=project.planned_end_date,
                                        activity_scope="STRETCH",
                                        default_duration_hours=float(hrs) if hrs is not None else None,
                                    )
                                    db.add(new_pa)
                                    db.flush()
                                    pa = new_pa
                                    pa_by_name[key] = pa

                                if pa is None:
                                    continue

                                sa = (
                                    db.query(StretchActivity)
                                    .filter(
                                        StretchActivity.stretch_id == int(stretch.id),
                                        StretchActivity.project_activity_id == int(pa.id),
                                    )
                                    .first()
                                )

                                if not include:
                                    if sa is not None:
                                        sa.is_active = False
                                        db.add(sa)
                                    continue

                                act_start_raw = ao.get("planned_start_date") or seg.get("planned_start_date")
                                act_end_raw = ao.get("planned_end_date") or seg.get("planned_end_date")
                                act_start = parse_date_ddmmyyyy_or_iso(str(act_start_raw)) if act_start_raw else None
                                act_end = parse_date_ddmmyyyy_or_iso(str(act_end_raw)) if act_end_raw else None

                                if sa is None:
                                    sa = StretchActivity(
                                        stretch_id=int(stretch.id),
                                        project_activity_id=int(pa.id),
                                        planned_start_date=act_start,
                                        planned_end_date=act_end,
                                        planned_duration_hours=float(hrs) if hrs is not None else None,
                                        planned_start_time=planned_start_time,
                                        planned_end_time=planned_end_time,
                                        planned_quantity=None,
                                        actual_quantity=None,
                                        progress_percent=None,
                                        is_active=True,
                                    )
                                    db.add(sa)
                                else:
                                    sa.is_active = True
                                    sa.planned_start_time = planned_start_time
                                    sa.planned_end_time = planned_end_time
                                    if act_start is not None:
                                        sa.planned_start_date = act_start
                                    if act_end is not None:
                                        sa.planned_end_date = act_end
                                    if hrs is not None:
                                        sa.planned_duration_hours = float(hrs)
                                    db.add(sa)

                            # Materials: store per-stretch quantities + exclusions
                            for mo in (seg.get("materials") or []):
                                if not isinstance(mo, dict):
                                    continue
                                mname = str(mo.get("name") or "").strip()
                                if not mname:
                                    continue
                                mid = material_id_by_name.get(mname.lower())
                                if not mid:
                                    continue
                                include = bool(mo.get("include"))
                                qty_raw = mo.get("quantity")
                                if qty_raw is None:
                                    qty_raw = mo.get("planned_quantity")

                                existing = (
                                    db.query(StretchMaterialExclusion)
                                    .filter(
                                        StretchMaterialExclusion.stretch_id == int(stretch.id),
                                        StretchMaterialExclusion.material_id == int(mid),
                                    )
                                    .first()
                                )

                                if include:
                                    if existing is not None:
                                        db.delete(existing)
                                    base_pm = planned_by_material_id.get(int(mid))
                                    if base_pm:
                                        unit_locked = str(getattr(base_pm, "unit", None) or "unit").strip() or "unit"
                                        allowed_locked = base_pm.get_allowed_units() if hasattr(base_pm, "get_allowed_units") else [unit_locked]
                                    else:
                                        unit_locked = "unit"
                                        allowed_locked = [unit_locked]

                                    try:
                                        qty_val = Decimal(str(qty_raw))
                                    except InvalidOperation:
                                        qty_val = Decimal("0")

                                    pm_stretch = (
                                        db.query(PlannedMaterial)
                                        .filter(
                                            PlannedMaterial.project_id == int(project.id),
                                            PlannedMaterial.material_id == int(mid),
                                            PlannedMaterial.stretch_id == int(stretch.id),
                                        )
                                        .first()
                                    )
                                    if not pm_stretch:
                                        pm_stretch = PlannedMaterial(
                                            project_id=int(project.id),
                                            material_id=int(mid),
                                            stretch_id=int(stretch.id),
                                            unit=unit_locked,
                                            allowed_units=json.dumps(allowed_locked),
                                            planned_quantity=qty_val,
                                        )
                                    else:
                                        pm_stretch.planned_quantity = qty_val
                                        pm_stretch.unit = unit_locked
                                        pm_stretch.allowed_units = json.dumps(allowed_locked)
                                    db.add(pm_stretch)
                                else:
                                    if existing is None:
                                        db.add(
                                            StretchMaterialExclusion(
                                                stretch_id=int(stretch.id),
                                                material_id=int(mid),
                                            )
                                        )

                        db.commit()
                    except Exception:
                        db.rollback()
                        logger.exception("Failed to apply per-stretch overrides (project_id=%s)", project.id)

                    flash(request, f"Stretch system enabled: created {created_stretches} stretch(es).", "success")
            except Exception as e:
                db.rollback()
                logger.exception("Stretch setup failed during project creation (project_id=%s)", project.id)
                flash(request, f"Project created, but stretch setup failed: {str(e) or 'error'}", "warning")

            # Best-effort wizard cleanup
            try:
                if wizard_id:
                    wizard_deactivate(db, wizard_id=int(wizard_id), user_id=int(user["id"]))
                    db.commit()
            except Exception:
                db.rollback()

        elif project_type:
            # Prefer editable presets payloads coming from UI (works for ALL types)
            activity_defs = _safe_parse_json_activity_defs(activity_preset_defs_json)
            activity_defs_by_name = {str(d.get("name") or "").strip().lower(): d for d in activity_defs}
            selected_activities_from_defs = [
                str(d.get("name") or "").strip()
                for d in activity_defs
                if bool(d.get("enabled", True)) and str(d.get("name") or "").strip()
            ]
            selected_activities = _sanitize_names(selected_activities_from_defs) or _sanitize_names(_safe_parse_json_list(activity_presets_json))
            selected_material_defs = _safe_parse_json_material_defs(material_preset_defs_json)

            if not selected_activities and not selected_material_defs:
                # Fallback to project-type standard presets
                preset = serialize_presets(get_presets_for_project_type(project_type))
                selected_activities = _sanitize_names([str(a) for a in (preset.get("activities") or [])])
                selected_material_defs = _safe_parse_json_material_defs(json.dumps(preset.get("materials") or []))

            next_act_code = activity_code_allocator(db, Activity, project_id=int(project.id), width=6, project_width=6)

            # Activities
            standard_activity_set = {a.lower() for a in selected_activities}
            for act_name in selected_activities:
                exists = (
                    db.query(Activity)
                    .filter(Activity.project_id == project.id, Activity.name == act_name)
                    .first()
                )
                if not exists:
                    d = activity_defs_by_name.get(str(act_name or "").strip().lower())
                    db.add(
                        Activity(
                            name=act_name,
                            is_standard=(act_name.lower() in standard_activity_set),
                            project_id=project.id,
                            code=next_act_code(),
                            default_start_time=(d.get("start_time") if isinstance(d, dict) else None),
                            default_end_time=(d.get("end_time") if isinstance(d, dict) else None),
                        )
                    )

            # Store selected presets for audit/future UX (optional)
            try:
                project.preset_activities_json = json.dumps(selected_activities)
                project.preset_materials_json = json.dumps(selected_material_defs)
                db.add(project)
                db.commit()
            except Exception:
                db.rollback()

            # Materials (global material registry + planned material link)
            for mdef in selected_material_defs:
                mat_name = str(mdef.get("name") or "").strip()
                if not mat_name:
                    continue
                unit = str(mdef.get("default_unit") or mdef.get("unit") or "unit").strip() or "unit"
                allowed_units = mdef.get("allowed_units")
                if not isinstance(allowed_units, list) or not allowed_units:
                    allowed_units = [unit]
                allowed_units = [str(u or "").strip() for u in allowed_units]
                allowed_units = [u for u in allowed_units if u]
                if unit not in allowed_units:
                    allowed_units.insert(0, unit)

                mat = db.query(Material).filter(Material.name == mat_name).first()
                if not mat:
                    mat = Material(
                        name=mat_name,
                        unit=unit,
                        standard_unit=unit,
                        allowed_units=json.dumps(allowed_units),
                    )
                    db.add(mat)
                    db.commit()
                    db.refresh(mat)
                else:
                    changed = False
                    if getattr(mat, "standard_unit", None) in (None, "") and unit:
                        mat.standard_unit = unit
                        changed = True
                    if getattr(mat, "allowed_units", None) in (None, "") and allowed_units:
                        mat.allowed_units = json.dumps(allowed_units)
                        changed = True
                    if changed:
                        db.add(mat)
                        db.commit()

                pm_exists = (
                    db.query(PlannedMaterial)
                    .filter(
                        PlannedMaterial.project_id == project.id,
                        PlannedMaterial.material_id == mat.id,
                        PlannedMaterial.stretch_id == None,  # noqa: E711
                    )
                    .first()
                )
                if not pm_exists:
                    db.add(
                        PlannedMaterial(
                            project_id=project.id,
                            material_id=mat.id,
                            stretch_id=None,
                            unit=unit,
                            allowed_units=json.dumps(allowed_units),
                            planned_quantity=Decimal("0"),
                        )
                    )
                else:
                    changed_pm = False
                    if not getattr(pm_exists, "unit", None):
                        pm_exists.unit = unit
                        changed_pm = True
                    if not getattr(pm_exists, "allowed_units", None):
                        pm_exists.allowed_units = json.dumps(allowed_units)
                        changed_pm = True
                    if changed_pm:
                        db.add(pm_exists)

            db.commit()
    except Exception:
        db.rollback()
        logger.exception("Create Project presets failed")

    # Project team membership (optional; best-effort)
    try:
        team = _safe_parse_project_team(project_team_json)
        if team:
            allowed_roles = {"admin", "manager", "member", "viewer"}
            is_system_admin = user.get("role") in {"admin", "superadmin"}
            for item in team:
                uid = int(item.get("user_id") or 0)
                if uid <= 0:
                    continue
                role_in_project = str(item.get("role_in_project") or "member").strip().lower() or "member"
                if role_in_project not in allowed_roles:
                    role_in_project = "member"
                if role_in_project == "admin" and not is_system_admin:
                    role_in_project = "member"

                existing = (
                    db.query(ProjectUser)
                    .filter(ProjectUser.project_id == project.id, ProjectUser.user_id == uid)
                    .first()
                )
                if existing:
                    existing.role_in_project = role_in_project
                    db.add(existing)
                else:
                    db.add(ProjectUser(project_id=project.id, user_id=uid, role_in_project=role_in_project))
            db.commit()
    except Exception:
        db.rollback()

    flash(request, "Project created successfully", "success")

    # If project creation came from the wizard, deactivate that wizard state (best-effort).
    if wizard_id:
        try:
            from app.models.project_wizard import ProjectWizardState

            db.query(ProjectWizardState).filter(
                ProjectWizardState.id == int(wizard_id),
                ProjectWizardState.user_id == int(user.get("id")),
            ).update({ProjectWizardState.is_active: False})
            db.commit()
        except Exception:
            db.rollback()

    return RedirectResponse(f"/projects/{project.id}", status_code=302)

# =================================================
# PROJECT OVERVIEW
# =================================================
def _build_project_preset_snapshot(project) -> dict:
    def _safe_json_dict(raw: str | None) -> dict:
        if not raw:
            return {}
        try:
            value = json.loads(raw)
            if isinstance(value, dict):
                return value
        except Exception:
            return {}
        return {}

    def _safe_json_list(raw: str | None) -> list:
        if not raw:
            return []
        try:
            value = json.loads(raw)
            if isinstance(value, list):
                return value
        except Exception:
            return []
        return []

    extras = _safe_json_dict(getattr(project, "road_extras_json", None))

    preset_key = (getattr(project, "road_preset_key", None) or "").strip() or None
    if not preset_key:
        preset_key = str(extras.get("preset_key") or "").strip() or None

    activity_names: list[str] = []
    for item in _safe_json_list(getattr(project, "preset_activities_json", None)):
        name = str(item or "").strip()
        if name:
            activity_names.append(name)
    activity_names = activity_names[:500]

    material_defs: list[dict] = []
    for item in _safe_json_list(getattr(project, "preset_materials_json", None)):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        unit = str(item.get("default_unit") or item.get("unit") or "unit").strip() or "unit"
        material_defs.append({"name": name[:150], "unit": unit[:50]})
    material_defs = material_defs[:500]

    mapping_pairs_raw = extras.get("activity_material_map")
    mapping_by_activity: dict[str, list[str]] = {}
    if isinstance(mapping_pairs_raw, list):
        for pair in mapping_pairs_raw[:2000]:
            if not isinstance(pair, dict):
                continue
            ac = str(pair.get("activity_code") or "").strip()
            mc = str(pair.get("material_code") or "").strip()
            if not ac or not mc:
                continue
            mapping_by_activity.setdefault(ac, []).append(mc)
        # de-dupe + sort
        for ac, mcs in list(mapping_by_activity.items()):
            uniq = sorted({str(x).strip() for x in mcs if str(x).strip()})
            mapping_by_activity[ac] = uniq

    return {
        "project_type": getattr(project, "project_type", None),
        "road_category": getattr(project, "road_category", None),
        "road_engineering_type": getattr(project, "road_engineering_type", None),
        "preset_key": preset_key,
        "activity_names": activity_names,
        "material_defs": material_defs,
        "mapping_by_activity": dict(sorted(mapping_by_activity.items(), key=lambda kv: kv[0])),
    }


@router.get("/{project_id}", response_class=HTMLResponse)
def project_overview_page(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    project, role = get_project_access(db, project_id, user)

    # If project does not exist, go back to list
    if not project:
        flash(request, "Project not found", "error")
        return RedirectResponse("/projects", status_code=302)

    preset_snapshot = _build_project_preset_snapshot(project)

    return templates.TemplateResponse(
        "projects/overview.html",
        {
            "request": request,
            "project": project,
            "role": role,
            "user": user,
            "preset_snapshot": preset_snapshot,
        }
    )


@router.get("/{project_id}/preset-snapshot.json", response_class=JSONResponse)
def project_preset_snapshot_json(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "Please login to continue"}, status_code=401)

    project, role = get_project_access(db, project_id, user)
    if not project:
        return JSONResponse({"error": "Project not found"}, status_code=404)

    snapshot = _build_project_preset_snapshot(project)
    snapshot["project_id"] = int(project.id)
    snapshot["project_name"] = str(project.name)
    snapshot["access_role"] = role

    return JSONResponse(snapshot)

# =================================================
# ✅ EDIT PROJECT (FIXED)
# =================================================
@router.get("/{project_id}/edit", response_class=HTMLResponse)
def edit_project_page(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    project, role = get_project_access(db, project_id, user)

    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to edit this project.", "error")
        return RedirectResponse("/projects/manage", status_code=302)

    _ensure_project_road_presets(db, project)

    stretches = (
        db.query(RoadStretch)
        .filter(
            RoadStretch.project_id == int(project.id),
            RoadStretch.is_active.isnot(False),
        )
        .order_by(RoadStretch.sequence_no.asc())
        .all()
    )

    # Auto-generate stretches for road projects if none exist
    if not stretches and project.project_type == "Road":
        try:
            total_length_m = int(round(float(project.road_length_km or 0) * 1000.0))
            if total_length_m > 0:
                segments = generate_stretch_segments(total_length_m=total_length_m, number_of_stretches=5)
                for seg in segments:
                    stretch = RoadStretch(
                        project_id=int(project.id),
                        stretch_code=str(seg.get("stretch_code") or ""),
                        stretch_name=str(seg.get("stretch_name") or ""),
                        start_chainage=str(seg.get("start_chainage") or "0+000"),
                        end_chainage=str(seg.get("end_chainage") or "0+000"),
                        length_m=int(seg.get("length_m") or 0),
                        sequence_no=int(seg.get("sequence_no") or 0),
                        planned_start_date=project.planned_start_date,
                        planned_end_date=project.planned_end_date,
                        is_active=True,
                    )
                    db.add(stretch)
                db.commit()
                try:
                    apply_activities_to_stretches(int(project.id), mode="ALL")
                except Exception:
                    logger.exception("Stretch activity mapping failed after auto-generate (project_id=%s)", project.id)

                stretches = (
                    db.query(RoadStretch)
                    .filter(
                        RoadStretch.project_id == int(project.id),
                        RoadStretch.is_active.isnot(False),
                    )
                    .order_by(RoadStretch.sequence_no.asc())
                    .all()
                )
        except Exception:
            logger.exception("Auto-generate stretches failed (project_id=%s)", project.id)

    # Ensure stretch activities exist if project activities are present
    if stretches:
        try:
            existing_sa = (
                db.query(StretchActivity)
                .join(RoadStretch, RoadStretch.id == StretchActivity.stretch_id)
                .filter(RoadStretch.project_id == int(project.id))
                .first()
            )
        except Exception:
            existing_sa = None
        if not existing_sa:
            try:
                apply_activities_to_stretches(int(project.id), mode="ALL")
            except Exception:
                logger.exception("Stretch activity mapping failed on edit page (project_id=%s)", project.id)

    materials_payload: list[dict] = []
    try:
        pm_rows = (
            db.query(PlannedMaterial, Material)
            .join(Material, Material.id == PlannedMaterial.material_id)
            .filter(
                PlannedMaterial.project_id == int(project.id),
                PlannedMaterial.stretch_id == None,  # noqa: E711
            )
            .all()
        )
        for pm, mat in pm_rows:
            allowed_raw = getattr(pm, "allowed_units", None) or getattr(mat, "allowed_units", None) or "[]"
            try:
                allowed_units = json.loads(allowed_raw) if isinstance(allowed_raw, str) else list(allowed_raw or [])
            except Exception:
                allowed_units = []
            allowed_units = [str(u or "").strip() for u in allowed_units if str(u or "").strip()]
            unit = str(getattr(pm, "unit", None) or getattr(mat, "standard_unit", None) or getattr(mat, "unit", None) or "unit").strip() or "unit"
            if not allowed_units:
                allowed_units = [unit]
            if unit not in allowed_units:
                allowed_units.insert(0, unit)
            materials_payload.append({"name": mat.name, "unit": unit, "allowed_units": allowed_units})
    except Exception:
        materials_payload = []

    stretch_payload = []
    for stretch in stretches:
        acts = (
            db.query(StretchActivity, ProjectActivity, Activity)
            .join(ProjectActivity, ProjectActivity.id == StretchActivity.project_activity_id)
            .join(Activity, Activity.id == ProjectActivity.activity_id)
            .filter(StretchActivity.stretch_id == int(stretch.id))
            .order_by(Activity.id.asc())
            .all()
        )
        act_payload = []
        for sa, pa, act in acts:
            act_payload.append(
                {
                    "id": int(sa.id),
                    "name": str(getattr(act, "name", "") or ""),
                    "planned_start_date": sa.planned_start_date.strftime("%d/%m/%Y") if sa.planned_start_date else "",
                    "planned_end_date": sa.planned_end_date.strftime("%d/%m/%Y") if sa.planned_end_date else "",
                }
            )

        stretch_payload.append(
            {
                "id": int(stretch.id),
                "stretch_code": stretch.stretch_code,
                "stretch_name": stretch.stretch_name,
                "planned_start_date": stretch.planned_start_date.strftime("%d/%m/%Y") if stretch.planned_start_date else "",
                "planned_end_date": stretch.planned_end_date.strftime("%d/%m/%Y") if stretch.planned_end_date else "",
                "activities": act_payload,
                "materials": materials_payload,
            }
        )

    return templates.TemplateResponse(
        "edit_project.html",
        {
            "request": request,
            "project": project,
            "user": user,
            "classification_metadata": get_classification_metadata(),
            "stretches_json": json.dumps(stretch_payload),
        }
    )


@router.get("/{project_id}/stretches/edit", response_class=HTMLResponse)
def edit_project_stretches_page(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    project, role = get_project_access(db, project_id, user)

    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to edit stretches.", "error")
        return RedirectResponse("/projects/manage", status_code=302)

    _ensure_project_road_presets(db, project)

    stretches = (
        db.query(RoadStretch)
        .filter(
            RoadStretch.project_id == int(project.id),
            RoadStretch.is_active.isnot(False),
        )
        .order_by(RoadStretch.sequence_no.asc())
        .all()
    )

    # Auto-generate stretches for road projects if none exist
    if not stretches and project.project_type == "Road":
        try:
            total_length_m = int(round(float(project.road_length_km or 0) * 1000.0))
            if total_length_m > 0:
                segments = generate_stretch_segments(total_length_m=total_length_m, number_of_stretches=5)
                for seg in segments:
                    stretch = RoadStretch(
                        project_id=int(project.id),
                        stretch_code=str(seg.get("stretch_code") or ""),
                        stretch_name=str(seg.get("stretch_name") or ""),
                        start_chainage=str(seg.get("start_chainage") or "0+000"),
                        end_chainage=str(seg.get("end_chainage") or "0+000"),
                        length_m=int(seg.get("length_m") or 0),
                        sequence_no=int(seg.get("sequence_no") or 0),
                        planned_start_date=project.planned_start_date,
                        planned_end_date=project.planned_end_date,
                        is_active=True,
                    )
                    db.add(stretch)
                db.commit()
                try:
                    apply_activities_to_stretches(int(project.id), mode="ALL")
                except Exception:
                    logger.exception("Stretch activity mapping failed after auto-generate (project_id=%s)", project.id)

                stretches = (
                    db.query(RoadStretch)
                    .filter(
                        RoadStretch.project_id == int(project.id),
                        RoadStretch.is_active.isnot(False),
                    )
                    .order_by(RoadStretch.sequence_no.asc())
                    .all()
                )
        except Exception:
            logger.exception("Auto-generate stretches failed (project_id=%s)", project.id)

    # Ensure stretch activities exist if project activities are present
    if stretches:
        try:
            existing_sa = (
                db.query(StretchActivity)
                .join(RoadStretch, RoadStretch.id == StretchActivity.stretch_id)
                .filter(RoadStretch.project_id == int(project.id))
                .first()
            )
        except Exception:
            existing_sa = None
        if not existing_sa:
            try:
                apply_activities_to_stretches(int(project.id), mode="ALL")
            except Exception:
                logger.exception("Stretch activity mapping failed on stretch edit page (project_id=%s)", project.id)

    materials_payload: list[dict] = []
    try:
        pm_rows = (
            db.query(PlannedMaterial, Material)
            .join(Material, Material.id == PlannedMaterial.material_id)
            .filter(
                PlannedMaterial.project_id == int(project.id),
                PlannedMaterial.stretch_id == None,  # noqa: E711
            )
            .all()
        )
        for pm, mat in pm_rows:
            allowed_raw = getattr(pm, "allowed_units", None) or getattr(mat, "allowed_units", None) or "[]"
            try:
                allowed_units = json.loads(allowed_raw) if isinstance(allowed_raw, str) else list(allowed_raw or [])
            except Exception:
                allowed_units = []
            allowed_units = [str(u or "").strip() for u in allowed_units if str(u or "").strip()]
            unit = str(getattr(pm, "unit", None) or getattr(mat, "standard_unit", None) or getattr(mat, "unit", None) or "unit").strip() or "unit"
            if not allowed_units:
                allowed_units = [unit]
            if unit not in allowed_units:
                allowed_units.insert(0, unit)
            materials_payload.append({"name": mat.name, "unit": unit, "allowed_units": allowed_units})
    except Exception:
        materials_payload = []

    payload = []
    for stretch in stretches:
        acts = (
            db.query(StretchActivity, ProjectActivity, Activity)
            .join(ProjectActivity, ProjectActivity.id == StretchActivity.project_activity_id)
            .join(Activity, Activity.id == ProjectActivity.activity_id)
            .filter(StretchActivity.stretch_id == int(stretch.id))
            .order_by(Activity.id.asc())
            .all()
        )
        act_payload = []
        for sa, pa, act in acts:
            act_payload.append(
                {
                    "id": int(sa.id),
                    "name": str(getattr(act, "name", "") or ""),
                    "planned_start_date": sa.planned_start_date.strftime("%d/%m/%Y") if sa.planned_start_date else "",
                    "planned_end_date": sa.planned_end_date.strftime("%d/%m/%Y") if sa.planned_end_date else "",
                }
            )

        payload.append(
            {
                "id": int(stretch.id),
                "stretch_code": stretch.stretch_code,
                "stretch_name": stretch.stretch_name,
                "planned_start_date": stretch.planned_start_date.strftime("%d/%m/%Y") if stretch.planned_start_date else "",
                "planned_end_date": stretch.planned_end_date.strftime("%d/%m/%Y") if stretch.planned_end_date else "",
                "activities": act_payload,
                "materials": materials_payload,
            }
        )

    return templates.TemplateResponse(
        "projects/edit_stretches.html",
        {
            "request": request,
            "project": project,
            "user": user,
            "stretches_json": json.dumps(payload),
        }
    )


@router.post("/{project_id}/stretches/update")
def update_project_stretches(
    project_id: int,
    request: Request,
    stretch_segments_json: str = Form(""),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    project, role = get_project_access(db, project_id, user)

    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to edit stretches.", "error")
        return RedirectResponse("/projects/manage", status_code=302)

    try:
        segments = json.loads(stretch_segments_json or "[]")
    except Exception:
        flash(request, "Invalid stretch payload.", "error")
        return RedirectResponse(f"/projects/{project_id}/stretches/edit", status_code=302)

    if not isinstance(segments, list):
        flash(request, "Invalid stretch payload.", "error")
        return RedirectResponse(f"/projects/{project_id}/stretches/edit", status_code=302)

    warnings: list[str] = []

    created_new_stretches = 0
    for seg in segments[:500]:
        if not isinstance(seg, dict):
            continue
        sid = int(seg.get("id") or 0)
        stretch = None
        if sid > 0:
            stretch = (
                db.query(RoadStretch)
                .filter(RoadStretch.id == sid, RoadStretch.project_id == int(project.id))
                .first()
            )

        if not stretch:
            # Create new stretch
            seq = int(seg.get("sequence_no") or 0) or None
            if not seq:
                last_seq = (
                    db.query(func.max(RoadStretch.sequence_no))
                    .filter(RoadStretch.project_id == int(project.id))
                    .scalar()
                    or 0
                )
                seq = int(last_seq) + 1
            code = str(seg.get("stretch_code") or f"ST-{seq:03d}").strip() or f"ST-{seq:03d}"
            name = str(seg.get("stretch_name") or f"Stretch {seq}").strip() or f"Stretch {seq}"

            try:
                start_m = int(seg.get("start_m") or 0)
                end_m = int(seg.get("end_m") or (start_m + int(seg.get("length_m") or 0)))
            except Exception:
                start_m = 0
                end_m = 0

            length_m = max(int(end_m - start_m), 1)
            stretch = RoadStretch(
                project_id=int(project.id),
                stretch_code=code,
                stretch_name=name,
                start_chainage=chainage_from_meters(int(start_m)),
                end_chainage=chainage_from_meters(int(end_m)),
                length_m=length_m,
                sequence_no=int(seq),
                is_active=True,
            )
            db.add(stretch)
            db.flush()
            created_new_stretches += 1

        name = str(seg.get("stretch_name") or "").strip()
        if name:
            stretch.stretch_name = name

        ps_raw = str(seg.get("planned_start_date") or "").strip()
        pe_raw = str(seg.get("planned_end_date") or "").strip()
        try:
            ps = parse_date_ddmmyyyy_or_iso(ps_raw) if ps_raw else None
        except Exception:
            ps = None
            warnings.append(f"Invalid start date for stretch {stretch.stretch_code}")
        try:
            pe = parse_date_ddmmyyyy_or_iso(pe_raw) if pe_raw else None
        except Exception:
            pe = None
            warnings.append(f"Invalid end date for stretch {stretch.stretch_code}")

        if ps:
            stretch.planned_start_date = ps
        if pe:
            stretch.planned_end_date = pe

        if stretch.planned_start_date and stretch.planned_end_date:
            if stretch.planned_end_date < stretch.planned_start_date:
                stretch.planned_end_date = stretch.planned_start_date
                warnings.append(f"Stretch {stretch.stretch_code} end date adjusted to start date")

        # Update stretch activities
        acts = seg.get("activities") or []
        if isinstance(acts, list):
            for a in acts[:1000]:
                if not isinstance(a, dict):
                    continue
                aid = int(a.get("id") or 0)
                if aid <= 0:
                    continue
                sa = db.query(StretchActivity).filter(StretchActivity.id == aid).first()
                if not sa:
                    continue

                aps_raw = str(a.get("planned_start_date") or "").strip()
                ape_raw = str(a.get("planned_end_date") or "").strip()
                try:
                    aps = parse_date_ddmmyyyy_or_iso(aps_raw) if aps_raw else None
                except Exception:
                    aps = None
                    warnings.append("Invalid activity start date; skipped.")
                try:
                    ape = parse_date_ddmmyyyy_or_iso(ape_raw) if ape_raw else None
                except Exception:
                    ape = None
                    warnings.append("Invalid activity end date; skipped.")

                if aps:
                    sa.planned_start_date = aps
                if ape:
                    sa.planned_end_date = ape

                # Clamp to stretch dates
                if stretch.planned_start_date and sa.planned_start_date and sa.planned_start_date < stretch.planned_start_date:
                    sa.planned_start_date = stretch.planned_start_date
                if stretch.planned_end_date and sa.planned_end_date and sa.planned_end_date > stretch.planned_end_date:
                    sa.planned_end_date = stretch.planned_end_date
                if sa.planned_start_date and sa.planned_end_date and sa.planned_end_date < sa.planned_start_date:
                    sa.planned_end_date = sa.planned_start_date

                db.add(sa)

        db.add(stretch)

    db.commit()

    if created_new_stretches:
        try:
            apply_activities_to_stretches(int(project.id), mode="ALL")
        except Exception:
            logger.exception("Stretch activity mapping failed after stretch creation (project_id=%s)", project.id)

    for msg in warnings[:10]:
        flash(request, msg, "warning")
    flash(request, "Stretches updated successfully", "success")
    return RedirectResponse(f"/projects/{project_id}/stretches/edit", status_code=302)

@router.post("/{project_id}/update")
def update_project_form(
    project_id: int,
    request: Request,
    name: str = Form(...),
    # Do not require road_type on update; road_type is treated as read-only once created
    road_type: str | None = Form(None),
    # New classification fields are immutable after creation
    road_category: str | None = Form(None),
    road_engineering_type: str | None = Form(None),
    road_extras_json: str | None = Form(None),
    # Basic fields (optional)
    project_code: str | None = Form(None),
    client_authority: str | None = Form(None),
    contractor: str | None = Form(None),
    consultant_pmc: str | None = Form(None),
    lanes: int = Form(...),
    road_width: float = Form(...),
    road_length_km: float = Form(...),
    carriageway_width: float | None = Form(None),
    shoulder_type: str | None = Form(None),
    median_type: str | None = Form(None),
    country: str = Form(...),
    state: str | None = Form(None),
    district: str | None = Form(None),
    city: str = Form(...),
    chainage_start: str | None = Form(None),
    chainage_end: str | None = Form(None),
    planned_start_date: str = Form(...),
    planned_end_date: str = Form(...),
    project_type: str | None = Form(None),
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    project, role = get_project_access(db, project_id, user)

    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to update this project.", "error")
        return RedirectResponse("/projects/manage", status_code=302)

    try:
        planned_start_date = parse_date_ddmmyyyy_or_iso(planned_start_date)
        planned_end_date = parse_date_ddmmyyyy_or_iso(planned_end_date)
    except Exception:
        flash(request, "Invalid date. Please use DD/MM/YYYY.", "error")
        return RedirectResponse(f"/projects/{project_id}/edit", status_code=302)

    # Strict immutability: never allow classification changes after creation.
    submitted_category = (road_category or "").strip()
    submitted_engineering = (road_engineering_type or "").strip()
    if submitted_category and submitted_category != ((project.road_category or "").strip()):
        flash(request, "Road Category cannot be changed after creation.", "error")
        return RedirectResponse(f"/projects/{project_id}/edit", status_code=302)
    if submitted_engineering and submitted_engineering != ((project.road_engineering_type or "").strip()):
        flash(request, "Road Engineering Type cannot be changed after creation.", "error")
        return RedirectResponse(f"/projects/{project_id}/edit", status_code=302)
    if (road_extras_json or "").strip() and (road_extras_json or "").strip() != ((project.road_extras_json or "").strip()):
        flash(request, "Road classification details are locked after creation.", "error")
        return RedirectResponse(f"/projects/{project_id}/edit", status_code=302)

    old = model_to_dict(project)

    project.name = name
    project.project_code = (project_code or None)
    project.client_authority = (client_authority or None)
    project.contractor = (contractor or None)
    project.consultant_pmc = (consultant_pmc or None)
    # Preserve existing road_type and project_type (immutable)
    # Do NOT overwrite `project.project_type` or `project.road_type` from the form.
    project.lanes = lanes
    project.road_width = road_width
    project.road_length_km = road_length_km
    project.carriageway_width = carriageway_width
    project.shoulder_type = (shoulder_type or None)
    project.median_type = (median_type or None)
    project.country = country
    project.state = (state or None)
    project.district = (district or None)
    project.city = city
    project.chainage_start = (chainage_start or None)
    project.chainage_end = (chainage_end or None)
    project.planned_start_date = planned_start_date
    project.planned_end_date = planned_end_date

    db.commit()

    # Audit: Project UPDATE (best-effort)
    log_action(
        db=db,
        request=request,
        action="UPDATE",
        entity_type="Project",
        entity_id=project.id,
        description="Project updated",
        old_value=old,
        new_value=model_to_dict(project),
    )
    flash(request, "Project updated successfully", "success")
    return RedirectResponse("/projects/manage", status_code=302)


# =================================================
# PROJECT MODULE ROUTES (lightweight guards / redirects)
# Ensure template paths exist to avoid 404s
# =================================================
@router.get("/{project_id}/materials", response_class=HTMLResponse)
def project_materials_page(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    project, role = get_project_access(db, project_id, user)
    if not project:
        flash(request, "Project not found", "error")
        return RedirectResponse("/projects", status_code=302)

    # Planned materials for this project
    planned_rows = (
        db.query(PlannedMaterial)
        .filter(
            PlannedMaterial.project_id == project_id,
            PlannedMaterial.stretch_id == None,  # noqa: E711
        )
        .all()
    )

    planned_materials: list[dict[str, object]] = []
    planned_name_keys: set[str] = set()
    for pm in planned_rows:
        mat = pm.material
        if not mat:
            continue
        planned_materials.append({
            "planned_material_id": int(pm.id),
            "material_id": int(mat.id),
            "name": mat.name,
            "unit": getattr(pm, "unit", None) or getattr(mat, "unit", "") or "",
            "standard_unit": getattr(mat, "standard_unit", None),
            "allowed_units": (pm.get_allowed_units() if hasattr(pm, "get_allowed_units") else (mat.get_allowed_units() if hasattr(mat, "get_allowed_units") else [])),
            "planned_quantity": float(pm.planned_quantity or 0),
        })
        planned_name_keys.add((mat.name or "").strip().lower())

    # Suggested (preset) materials not yet added
    project_type = (project.project_type or "").strip() or "Building"
    preset_material_defs: list[dict[str, object]] = []
    try:
        if project_type.lower() == "road":
            preset_def = get_presets_for_engineering_type(project.road_engineering_type)
            for m in (preset_def.get("materials") or []):
                try:
                    name = str(getattr(m, "name", "") or "").strip()
                    if not name:
                        continue
                    unit = str(getattr(m, "default_unit", "unit") or "unit").strip() or "unit"
                    allowed = list(getattr(m, "allowed_units", []) or [])
                    allowed = [str(u or "").strip() for u in allowed if str(u or "").strip()]
                    if not allowed:
                        allowed = [unit]
                    if unit not in allowed:
                        allowed.insert(0, unit)
                    preset_material_defs.append({"name": name, "default_unit": unit, "allowed_units": allowed})
                except Exception:
                    continue
        else:
            preset = serialize_presets(get_presets_for_project_type(project_type))
            preset_material_defs = list(preset.get("materials") or [])
    except Exception:
        preset_material_defs = []

    suggested_material_defs = []
    for mdef in preset_material_defs:
        name = str(mdef.get("name") or "").strip()
        if not name:
            continue
        if name.strip().lower() in planned_name_keys:
            continue
        suggested_material_defs.append(mdef)

    # Who can edit
    can_edit = role in ["owner", "admin", "manager"]

    return templates.TemplateResponse(
        "project_materials.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "role": role,
            "can_edit": can_edit,
            "planned_materials": planned_materials,
            "suggested_material_defs": suggested_material_defs,
        },
    )


@router.post("/{project_id}/materials/add")
async def project_materials_add(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    project, role = get_project_access(db, project_id, user)
    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to edit project materials.", "error")
        return RedirectResponse(f"/projects/{project_id}/materials", status_code=302)

    form = await request.form()

    # Accept either a selected preset name or custom fields
    preset_name = str(form.get("preset_material_name") or "").strip()
    custom_name = str(form.get("custom_name") or "").strip()
    custom_unit = str(form.get("custom_unit") or "").strip() or "unit"
    custom_allowed = str(form.get("custom_allowed_units") or "").strip()

    mdef: dict[str, object] = {}
    if preset_name:
        # Resolve the selected preset material to a full definition (unit + allowed units)
        pt = (project.project_type or "").strip() or "Building"
        resolved: dict[str, object] | None = None
        try:
            if pt.lower() == "road":
                preset_def = get_presets_for_engineering_type(project.road_engineering_type)
                for m in (preset_def.get("materials") or []):
                    name = str(getattr(m, "name", "") or "").strip()
                    if name.lower() != preset_name.lower():
                        continue
                    unit = str(getattr(m, "default_unit", "unit") or "unit").strip() or "unit"
                    allowed = list(getattr(m, "allowed_units", []) or [])
                    allowed = [str(u or "").strip() for u in allowed if str(u or "").strip()]
                    if not allowed:
                        allowed = [unit]
                    if unit not in allowed:
                        allowed.insert(0, unit)
                    resolved = {"name": name, "default_unit": unit, "allowed_units": allowed}
                    break
            else:
                preset = serialize_presets(get_presets_for_project_type(pt))
                for m in (preset.get("materials") or []):
                    name = str(m.get("name") or "").strip()
                    if name.lower() != preset_name.lower():
                        continue
                    resolved = m
                    break
        except Exception:
            resolved = None

        if resolved:
            mdef = resolved
        else:
            mdef = {"name": preset_name, "default_unit": "unit", "allowed_units": ["unit"]}
    elif custom_name:
        allowed_units = [u.strip() for u in custom_allowed.split(",") if u.strip()] if custom_allowed else [custom_unit]
        if custom_unit not in allowed_units:
            allowed_units.insert(0, custom_unit)
        mdef = {"name": custom_name, "default_unit": custom_unit, "allowed_units": allowed_units}

    mat_name = str(mdef.get("name") or "").strip()
    if not mat_name:
        flash(request, "Please select a preset material or enter a custom material.", "warning")
        return RedirectResponse(f"/projects/{project_id}/materials", status_code=302)

    unit = str(mdef.get("default_unit") or mdef.get("unit") or "unit").strip() or "unit"
    allowed_units = mdef.get("allowed_units")
    if not isinstance(allowed_units, list) or not allowed_units:
        allowed_units = [unit]
    allowed_units = [str(u or "").strip() for u in allowed_units]
    allowed_units = [u for u in allowed_units if u]
    if unit not in allowed_units:
        allowed_units.insert(0, unit)

    try:
        mat = db.query(Material).filter(Material.name == mat_name).first()
        if not mat:
            mat = Material(
                name=mat_name,
                unit=unit,
                standard_unit=unit,
                allowed_units=json.dumps(allowed_units),
            )
            db.add(mat)
            db.commit()
            db.refresh(mat)
        else:
            changed = False
            if getattr(mat, "standard_unit", None) in (None, "") and unit:
                mat.standard_unit = unit
                changed = True
            if getattr(mat, "allowed_units", None) in (None, "") and allowed_units:
                mat.allowed_units = json.dumps(allowed_units)
                changed = True
            if changed:
                db.add(mat)
                db.commit()

        pm_exists = (
            db.query(PlannedMaterial)
            .filter(
                PlannedMaterial.project_id == project.id,
                PlannedMaterial.material_id == mat.id,
                PlannedMaterial.stretch_id == None,  # noqa: E711
            )
            .first()
        )
        if not pm_exists:
            db.add(
                PlannedMaterial(
                    project_id=project.id,
                    material_id=mat.id,
                    stretch_id=None,
                    unit=unit,
                    allowed_units=json.dumps(allowed_units),
                    planned_quantity=Decimal("0"),
                )
            )
            db.commit()
        else:
            changed_pm = False
            if not getattr(pm_exists, "unit", None):
                pm_exists.unit = unit
                changed_pm = True
            if not getattr(pm_exists, "allowed_units", None):
                pm_exists.allowed_units = json.dumps(allowed_units)
                changed_pm = True
            if changed_pm:
                db.add(pm_exists)
                db.commit()

        flash(request, f"Material added: {mat.name}", "success")
    except Exception:
        db.rollback()
        flash(request, "Failed to add material.", "error")

    return RedirectResponse(f"/projects/{project_id}/materials", status_code=302)


@router.post("/{project_id}/materials/update")
async def project_materials_update(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    project, role = get_project_access(db, project_id, user)
    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to edit project materials.", "error")
        return RedirectResponse(f"/projects/{project_id}/materials", status_code=302)

    form = await request.form()
    pm_id = int(form.get("planned_material_id") or 0)
    qty_raw = str(form.get("planned_quantity") or "0").strip()
    try:
        qty = float(qty_raw)
    except Exception:
        qty = 0.0
    if qty < 0:
        qty = 0.0

    pm = (
        db.query(PlannedMaterial)
        .filter(
            PlannedMaterial.id == pm_id,
            PlannedMaterial.project_id == project_id,
            PlannedMaterial.stretch_id == None,  # noqa: E711
        )
        .first()
    )
    if not pm:
        flash(request, "Planned material not found.", "error")
        return RedirectResponse(f"/projects/{project_id}/materials", status_code=302)

    try:
        try:
            pm.planned_quantity = Decimal(str(qty_raw))
        except InvalidOperation:
            pm.planned_quantity = Decimal("0")
        db.add(pm)
        db.commit()
        flash(request, "Planned quantity updated.", "success")
    except Exception:
        db.rollback()
        flash(request, "Failed to update planned quantity.", "error")

    return RedirectResponse(f"/projects/{project_id}/materials", status_code=302)


@router.post("/{project_id}/materials/remove")
async def project_materials_remove(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    project, role = get_project_access(db, project_id, user)
    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to edit project materials.", "error")
        return RedirectResponse(f"/projects/{project_id}/materials", status_code=302)

    form = await request.form()
    pm_id = int(form.get("planned_material_id") or 0)

    pm = (
        db.query(PlannedMaterial)
        .filter(
            PlannedMaterial.id == pm_id,
            PlannedMaterial.project_id == project_id,
            PlannedMaterial.stretch_id == None,  # noqa: E711
        )
        .first()
    )
    if not pm:
        flash(request, "Planned material not found.", "error")
        return RedirectResponse(f"/projects/{project_id}/materials", status_code=302)

    try:
        db.delete(pm)
        db.commit()
        flash(request, "Material removed from project.", "success")
    except Exception:
        db.rollback()
        flash(request, "Failed to remove material.", "error")

    return RedirectResponse(f"/projects/{project_id}/materials", status_code=302)


@router.get("/{project_id}/activity-materials", response_class=HTMLResponse)
def project_activity_materials_page(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    project, role = get_project_access(db, project_id, user)
    if not project:
        flash(request, "Project not found", "error")
        return RedirectResponse("/projects", status_code=302)

    can_edit = role in ["owner", "admin", "manager"]
    can_edit_lead_time = role in ["admin", "manager"] or (user.get("role") in ["admin", "manager"])

    activities = (
        db.query(Activity)
        .filter(Activity.project_id == project_id)
        .order_by(Activity.name.asc())
        .all()
    )

    planned_rows = (
        db.query(PlannedMaterial)
        .filter(
            PlannedMaterial.project_id == project_id,
            PlannedMaterial.stretch_id == None,  # noqa: E711
        )
        .all()
    )
    planned_materials = [pm.material for pm in planned_rows if pm.material]
    planned_materials = sorted(planned_materials, key=lambda m: (m.name or "").lower())

    mappings = (
        db.query(ActivityMaterial, Activity, Material, MaterialVendor)
        .join(Activity, Activity.id == ActivityMaterial.activity_id)
        .join(Material, Material.id == ActivityMaterial.material_id)
        .outerjoin(MaterialVendor, MaterialVendor.id == ActivityMaterial.vendor_id)
        .filter(Activity.project_id == project_id)
        .order_by(Activity.name.asc(), Material.name.asc())
        .all()
    )

    # Schedule baseline (for delivery risk)
    pa_rows = (
        db.query(ProjectActivity)
        .filter(ProjectActivity.project_id == project_id)
        .all()
    )
    start_by_activity_id = {int(pa.activity_id): pa.start_date for pa in pa_rows}
    planned_qty_by_activity_id = {int(pa.activity_id): float(pa.planned_quantity or 0.0) for pa in pa_rows}

    # Vendors by material
    planned_material_ids = sorted({int(m.id) for m in planned_materials})
    vendor_rows = []
    if planned_material_ids:
        vendor_rows = (
            db.query(MaterialVendor)
            .filter(MaterialVendor.material_id.in_(planned_material_ids))
            .order_by(MaterialVendor.is_active.desc(), MaterialVendor.vendor_name.asc())
            .all()
        )
    vendors_by_material_id: dict[int, list[MaterialVendor]] = {}
    vendors_by_material_json: dict[str, list[dict[str, object]]] = {}
    for v in vendor_rows:
        vendors_by_material_id.setdefault(int(v.material_id), []).append(v)
        vendors_by_material_json.setdefault(str(int(v.material_id)), []).append(
            {
                "id": int(v.id),
                "vendor_name": str(v.vendor_name or ""),
                "lead_time_days": int(v.lead_time_days or 0),
                "is_active": bool(v.is_active),
            }
        )

    # Stock by material for reorder suggestion
    stock_rows = []
    if planned_material_ids:
        stock_rows = (
            db.query(MaterialStock)
            .filter(MaterialStock.project_id == project_id, MaterialStock.material_id.in_(planned_material_ids))
            .all()
        )
    stock_by_material_id = {int(s.material_id): s for s in stock_rows}

    mapping_rows: list[dict[str, object]] = []
    mapped_activity_ids: set[int] = set()
    today = date.today()
    for am, act, mat, vendor in mappings:
        activity_start = start_by_activity_id.get(int(act.id))

        vendor_lead = int(getattr(vendor, "lead_time_days", 0) or 0) if vendor else None
        mat_default = getattr(mat, "default_lead_time_days", None)
        mat_legacy = getattr(mat, "lead_time_days", None)

        effective_lead = resolve_effective_lead_time_days(
            lead_time_days_override=getattr(am, "lead_time_days_override", None),
            vendor_lead_time_days=vendor_lead,
            material_default_lead_time_days=mat_default,
            material_legacy_lead_time_days=mat_legacy,
        )

        od = getattr(am, "order_date", None)
        expected = getattr(am, "expected_delivery_date", None) or compute_expected_delivery_date(od, effective_lead)
        check = evaluate_delivery_risk(
            activity_start_date=activity_start,
            order_date=od,
            expected_delivery_date=expected,
            today=today,
        )

        planned_qty = float(planned_qty_by_activity_id.get(int(act.id), 0.0) or 0.0)
        required_qty = planned_qty * float(am.consumption_rate or 0.0)
        stock = stock_by_material_id.get(int(mat.id))
        available = float(getattr(stock, "quantity_available", 0.0) or 0.0) if stock else 0.0
        reorder_hint = compute_reorder_suggestion(
            available_qty=available,
            required_qty=required_qty,
            unit_label=(mat.unit or None),
        )

        mapping_rows.append(
            {
                "id": int(am.id),
                "activity_id": int(act.id),
                "activity": act.name,
                "material_id": int(mat.id),
                "material": mat.name,
                "consumption_rate": float(am.consumption_rate or 0),

                "activity_start_date": activity_start,
                "vendor_id": int(getattr(am, "vendor_id", 0) or 0) or None,
                "vendor_name": getattr(vendor, "vendor_name", None) if vendor else None,
                "order_date": od,
                "lead_time_days": int(effective_lead or 0),
                "lead_time_override": getattr(am, "lead_time_days_override", None),
                "expected_delivery_date": check.expected_delivery_date,
                "material_status": check.status,
                "material_is_risk": bool(check.is_risk),
                "material_days_late": int(check.days_late or 0),

                "available_qty": available,
                "required_qty": required_qty,
                "reorder_hint": reorder_hint,
            }
        )
        mapped_activity_ids.add(int(act.id))

    unmapped_activities = [a for a in activities if int(a.id) not in mapped_activity_ids]

    return templates.TemplateResponse(
        "project_activity_materials.html",
        {
            "request": request,
            "user": user,
            "project": project,
            "role": role,
            "can_edit": can_edit,
            "can_edit_lead_time": can_edit_lead_time,
            "activities": activities,
            "planned_materials": planned_materials,
            "mapping_rows": mapping_rows,
            "unmapped_activities": unmapped_activities,
            "vendors_by_material_id": vendors_by_material_id,
            "vendors_by_material_json": vendors_by_material_json,
            "today": today,
        },
    )


@router.post("/{project_id}/activity-materials/add")
async def project_activity_materials_add(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    project, role = get_project_access(db, project_id, user)
    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to edit activity-material mappings.", "error")
        return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)

    form = await request.form()
    try:
        activity_id = int(form.get("activity_id") or 0)
        material_id = int(form.get("material_id") or 0)
        rate = float(str(form.get("consumption_rate") or "0").strip() or 0)
    except Exception:
        activity_id, material_id, rate = 0, 0, 0.0

    # Optional vendor + lead time planning fields
    try:
        vendor_id = int(form.get("vendor_id") or 0)
    except Exception:
        vendor_id = 0
    vendor_id = vendor_id or None

    order_date_raw = str(form.get("order_date") or "").strip()
    order_date = None
    if order_date_raw:
        try:
            order_date = parse_date_ddmmyyyy_or_iso(order_date_raw)
        except Exception:
            order_date = None

    lt_override_raw = str(form.get("lead_time_days_override") or "").strip()
    lead_time_days_override = None
    if lt_override_raw != "":
        try:
            lead_time_days_override = int(float(lt_override_raw))
        except Exception:
            lead_time_days_override = None
        if lead_time_days_override is not None and lead_time_days_override < 0:
            lead_time_days_override = 0

    activity = db.query(Activity).filter(Activity.id == activity_id, Activity.project_id == project_id).first()
    material = db.query(Material).filter(Material.id == material_id).first()
    if not activity or not material:
        flash(request, "Invalid activity or material.", "error")
        return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)

    existing = (
        db.query(ActivityMaterial)
        .filter(ActivityMaterial.activity_id == activity_id, ActivityMaterial.material_id == material_id)
        .first()
    )
    if existing:
        flash(request, "Mapping already exists.", "warning")
        return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)

    # Resolve vendor/material lead time
    vendor = None
    if vendor_id:
        vendor = db.query(MaterialVendor).filter(MaterialVendor.id == vendor_id, MaterialVendor.material_id == material_id).first()
        if not vendor:
            vendor_id = None

    effective_lt = resolve_effective_lead_time_days(
        lead_time_days_override=lead_time_days_override,
        vendor_lead_time_days=(vendor.lead_time_days if vendor else None),
        material_default_lead_time_days=getattr(material, "default_lead_time_days", None),
        material_legacy_lead_time_days=getattr(material, "lead_time_days", None),
    )
    expected = compute_expected_delivery_date(order_date, effective_lt)

    # Activity start for risk check
    pa = (
        db.query(ProjectActivity)
        .filter(ProjectActivity.project_id == project_id, ProjectActivity.activity_id == activity_id)
        .first()
    )
    activity_start = pa.start_date if pa else None
    check = evaluate_delivery_risk(
        activity_start_date=activity_start,
        order_date=order_date,
        expected_delivery_date=expected,
        today=date.today(),
    )

    try:
        db.add(
            ActivityMaterial(
                activity_id=activity_id,
                material_id=material_id,
                consumption_rate=max(rate, 0.0),
                vendor_id=vendor_id,
                order_date=order_date,
                lead_time_days_override=lead_time_days_override,
                lead_time_days=int(effective_lt or 0),
                expected_delivery_date=check.expected_delivery_date,
                is_material_risk=bool(check.is_risk),
                updated_at=datetime.utcnow(),
            )
        )

        pm_exists = (
            db.query(PlannedMaterial)
            .filter(
                PlannedMaterial.project_id == project_id,
                PlannedMaterial.material_id == material_id,
                PlannedMaterial.stretch_id == None,  # noqa: E711
            )
            .first()
        )
        unit_locked = (getattr(material, "standard_unit", None) or getattr(material, "unit", None) or "unit").strip() or "unit"
        allowed_locked = material.get_allowed_units() if hasattr(material, "get_allowed_units") else [unit_locked]
        allowed_locked = [str(u or "").strip() for u in allowed_locked if str(u or "").strip()]
        if not allowed_locked:
            allowed_locked = [unit_locked]
        if unit_locked not in allowed_locked:
            allowed_locked.insert(0, unit_locked)
        if not pm_exists:
            db.add(
                PlannedMaterial(
                    project_id=project_id,
                    material_id=material_id,
                    stretch_id=None,
                    unit=unit_locked,
                    allowed_units=json.dumps(allowed_locked),
                    planned_quantity=Decimal("0"),
                )
            )
        else:
            changed_pm = False
            if not getattr(pm_exists, "unit", None):
                pm_exists.unit = unit_locked
                changed_pm = True
            if not getattr(pm_exists, "allowed_units", None):
                pm_exists.allowed_units = json.dumps(allowed_locked)
                changed_pm = True
            if changed_pm:
                db.add(pm_exists)

        db.commit()
        flash(request, "Mapping added.", "success")
    except Exception:
        db.rollback()
        flash(request, "Failed to add mapping.", "error")

    return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)


@router.post("/{project_id}/activity-materials/update")
async def project_activity_materials_update(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    project, role = get_project_access(db, project_id, user)
    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to edit activity-material mappings.", "error")
        return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)

    form = await request.form()
    try:
        mapping_id = int(form.get("mapping_id") or 0)
        rate = float(str(form.get("consumption_rate") or "0").strip() or 0)
    except Exception:
        mapping_id, rate = 0, 0.0

    # Optional vendor + lead time planning fields
    try:
        vendor_id = int(form.get("vendor_id") or 0)
    except Exception:
        vendor_id = 0
    vendor_id = vendor_id or None

    order_date_raw = str(form.get("order_date") or "").strip()
    order_date = None
    if order_date_raw:
        try:
            order_date = parse_date_ddmmyyyy_or_iso(order_date_raw)
        except Exception:
            order_date = None

    lt_override_raw = str(form.get("lead_time_days_override") or "").strip()
    lead_time_days_override = None
    if lt_override_raw != "":
        try:
            lead_time_days_override = int(float(lt_override_raw))
        except Exception:
            lead_time_days_override = None
        if lead_time_days_override is not None and lead_time_days_override < 0:
            lead_time_days_override = 0

    row = (
        db.query(ActivityMaterial)
        .join(Activity, Activity.id == ActivityMaterial.activity_id)
        .filter(ActivityMaterial.id == mapping_id, Activity.project_id == project_id)
        .first()
    )
    if not row:
        flash(request, "Mapping not found.", "error")
        return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)

    # Lead time editing: admin/manager only (global or project role)
    can_edit_lead_time = role in ["admin", "manager"] or (user.get("role") in ["admin", "manager"])

    old_snapshot = model_to_dict(row)

    try:
        row.consumption_rate = max(rate, 0.0)

        if can_edit_lead_time:
            # Validate vendor belongs to material
            material = db.query(Material).filter(Material.id == row.material_id).first()
            vendor = None
            if vendor_id:
                vendor = (
                    db.query(MaterialVendor)
                    .filter(MaterialVendor.id == vendor_id, MaterialVendor.material_id == row.material_id)
                    .first()
                )
                if not vendor:
                    vendor_id = None

            effective_lt = resolve_effective_lead_time_days(
                lead_time_days_override=lead_time_days_override,
                vendor_lead_time_days=(vendor.lead_time_days if vendor else None),
                material_default_lead_time_days=getattr(material, "default_lead_time_days", None) if material else None,
                material_legacy_lead_time_days=getattr(material, "lead_time_days", None) if material else None,
            )

            expected = compute_expected_delivery_date(order_date, effective_lt)
            pa = (
                db.query(ProjectActivity)
                .filter(ProjectActivity.project_id == project_id, ProjectActivity.activity_id == row.activity_id)
                .first()
            )
            activity_start = pa.start_date if pa else None
            check = evaluate_delivery_risk(
                activity_start_date=activity_start,
                order_date=order_date,
                expected_delivery_date=expected,
                today=date.today(),
            )

            row.vendor_id = vendor_id
            row.order_date = order_date
            row.lead_time_days_override = lead_time_days_override
            row.lead_time_days = int(effective_lt or 0)
            row.expected_delivery_date = check.expected_delivery_date
            row.is_material_risk = bool(check.is_risk)

        row.updated_at = datetime.utcnow()
        db.add(row)
        db.commit()

        # Audit vendor selection/lead time changes
        new_snapshot = model_to_dict(row)
        if can_edit_lead_time:
            if (old_snapshot.get("vendor_id") != new_snapshot.get("vendor_id")):
                log_action(
                    db=db,
                    request=request,
                    action="UPDATE",
                    entity_type="activity_material",
                    entity_id=row.id,
                    description=f"Vendor selection changed for activity-material mapping #{row.id}",
                    old_value={"mapping": old_snapshot},
                    new_value={"mapping": new_snapshot},
                )
            elif (
                old_snapshot.get("lead_time_days_override") != new_snapshot.get("lead_time_days_override")
                or old_snapshot.get("order_date") != new_snapshot.get("order_date")
                or old_snapshot.get("lead_time_days") != new_snapshot.get("lead_time_days")
            ):
                log_action(
                    db=db,
                    request=request,
                    action="UPDATE",
                    entity_type="activity_material",
                    entity_id=row.id,
                    description=f"Lead time planning updated for activity-material mapping #{row.id}",
                    old_value={"mapping": old_snapshot},
                    new_value={"mapping": new_snapshot},
                )

        flash(request, "Mapping updated.", "success")
    except Exception:
        db.rollback()
        flash(request, "Failed to update mapping.", "error")

    return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)


@router.post("/{project_id}/activity-materials/remove")
async def project_activity_materials_remove(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    project, role = get_project_access(db, project_id, user)
    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to edit activity-material mappings.", "error")
        return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)

    form = await request.form()
    try:
        mapping_id = int(form.get("mapping_id") or 0)
    except Exception:
        mapping_id = 0

    row = (
        db.query(ActivityMaterial)
        .join(Activity, Activity.id == ActivityMaterial.activity_id)
        .filter(ActivityMaterial.id == mapping_id, Activity.project_id == project_id)
        .first()
    )
    if not row:
        flash(request, "Mapping not found.", "error")
        return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)

    try:
        db.delete(row)
        db.commit()
        flash(request, "Mapping removed.", "success")
    except Exception:
        db.rollback()
        flash(request, "Failed to remove mapping.", "error")

    return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)


@router.post("/{project_id}/activity-materials/apply-presets")
def project_activity_materials_apply_presets(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    project, role = get_project_access(db, project_id, user)
    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to apply presets.", "error")
        return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)

    activities = db.query(Activity).filter(Activity.project_id == project_id).all()
    if not activities:
        flash(request, "No activities found for this project.", "warning")
        return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)

    pt = (project.project_type or "").strip() or "Building"

    # Prefer data-driven Road preset mappings when available (category + engineering type + extras)
    links = None
    if pt.lower() == "road":
        preset = get_road_preset(
            road_category=getattr(project, "road_category", None),
            road_engineering_type=getattr(project, "road_engineering_type", None),
            road_extras_json=getattr(project, "road_extras_json", None),
            db=db,
        )
        if preset and preset.links:
            links = list(preset.links)

    if links is None:
        links = get_activity_material_links(pt, getattr(project, "road_engineering_type", None))

    by_activity: dict[str, list] = {}
    for link in links:
        key = (link.activity or "").strip().lower()
        if not key:
            continue
        by_activity.setdefault(key, []).append(link)

    created = 0
    try:
        for act in activities:
            key = (act.name or "").strip().lower()
            if not key or key not in by_activity:
                continue

            for link in by_activity[key]:
                m = link.material
                mat_name = (m.name or "").strip()
                if not mat_name:
                    continue

                unit = (m.default_unit or "unit").strip() or "unit"
                allowed = [str(u or "").strip() for u in (m.allowed_units or []) if str(u or "").strip()]
                if not allowed:
                    allowed = [unit]
                if unit not in allowed:
                    allowed.insert(0, unit)

                material = db.query(Material).filter(Material.name == mat_name).first()
                if not material:
                    material = Material(
                        name=mat_name,
                        unit=unit,
                        standard_unit=unit,
                        allowed_units=json.dumps(allowed),
                    )
                    db.add(material)
                    db.commit()
                    db.refresh(material)
                else:
                    changed = False
                    if getattr(material, "standard_unit", None) in (None, "") and unit:
                        material.standard_unit = unit
                        changed = True
                    if getattr(material, "allowed_units", None) in (None, "") and allowed:
                        material.allowed_units = json.dumps(allowed)
                        changed = True
                    if changed:
                        db.add(material)
                        db.commit()

                pm_exists = (
                    db.query(PlannedMaterial)
                    .filter(
                        PlannedMaterial.project_id == project_id,
                        PlannedMaterial.material_id == material.id,
                        PlannedMaterial.stretch_id == None,  # noqa: E711
                    )
                    .first()
                )
                unit_locked = (getattr(material, "standard_unit", None) or getattr(material, "unit", None) or "unit").strip() or "unit"
                allowed_locked = material.get_allowed_units() if hasattr(material, "get_allowed_units") else [unit_locked]
                allowed_locked = [str(u or "").strip() for u in allowed_locked if str(u or "").strip()]
                if not allowed_locked:
                    allowed_locked = [unit_locked]
                if unit_locked not in allowed_locked:
                    allowed_locked.insert(0, unit_locked)
                if not pm_exists:
                    db.add(
                        PlannedMaterial(
                            project_id=project_id,
                            material_id=material.id,
                            stretch_id=None,
                            unit=unit_locked,
                            allowed_units=json.dumps(allowed_locked),
                            planned_quantity=Decimal("0"),
                        )
                    )
                    db.commit()
                else:
                    changed_pm = False
                    if not getattr(pm_exists, "unit", None):
                        pm_exists.unit = unit_locked
                        changed_pm = True
                    if not getattr(pm_exists, "allowed_units", None):
                        pm_exists.allowed_units = json.dumps(allowed_locked)
                        changed_pm = True
                    if changed_pm:
                        db.add(pm_exists)
                        db.commit()

                exists = (
                    db.query(ActivityMaterial)
                    .filter(ActivityMaterial.activity_id == act.id, ActivityMaterial.material_id == material.id)
                    .first()
                )
                if exists:
                    continue

                db.add(
                    ActivityMaterial(
                        activity_id=int(act.id),
                        material_id=int(material.id),
                        consumption_rate=max(float(link.consumption_rate or 0), 0.0),
                    )
                )
                db.commit()
                created += 1
    except Exception:
        db.rollback()
        flash(request, "Failed to apply preset mappings.", "error")
        return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)

    flash(request, f"Preset mappings applied. Added {created} mappings.", "success")
    return RedirectResponse(f"/projects/{project_id}/activity-materials", status_code=302)


@router.get("/{project_id}/documents", response_class=HTMLResponse)
def project_documents_page(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        flash(request, "Please login to continue", "warning")
        return RedirectResponse("/login", status_code=302)

    project, role = get_project_access(db, project_id, user)
    if not project:
        flash(request, "Project not found", "error")
        return RedirectResponse("/projects", status_code=302)

    # Documents module not implemented under /projects — keep URL valid by
    # redirecting back to the project overview (avoids 404 while preserving UX)
    return RedirectResponse(f"/projects/{project_id}", status_code=302)

# =================================================
# ARCHIVE / COMPLETE
# =================================================
@router.post("/{project_id}/archive")
def archive_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    project, role = get_project_access(db, project_id, user)

    # Allow owners, admins and managers to archive/restore
    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to archive/restore this project.", "error")
        return RedirectResponse("/projects/manage", status_code=302)

    old = model_to_dict(project)

    project.is_active = not project.is_active
    project.status = "archived" if not project.is_active else "active"
    db.commit()

    log_action(
        db=db,
        request=request,
        action="ARCHIVE",
        entity_type="Project",
        entity_id=project.id,
        description=("Project restored" if project.is_active else "Project archived"),
        old_value=old,
        new_value=model_to_dict(project),
    )

    # User-facing message
    if project.is_active:
        flash(request, "Project restored successfully", "success")
    else:
        flash(request, "Project archived successfully", "success")

    return RedirectResponse("/projects/manage", status_code=302)


# =================================================
# COMPLETE PROJECT
# Marks a project completed (sets completed_at and status)
# Accessible to owner/admin/manager
# =================================================
@router.post("/{project_id}/complete")
def complete_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    project, role = get_project_access(db, project_id, user)

    if not project or role not in ["owner", "admin", "manager"]:
        flash(request, "You do not have permission to complete this project.", "error")
        return RedirectResponse("/projects/manage", status_code=302)

    project.completed_at = datetime.utcnow()
    project.status = "completed"
    db.commit()

    flash(request, "Project marked as completed", "success")

    return RedirectResponse(f"/projects/{project_id}", status_code=302)

# =================================================
# 🗑 DELETE PROJECT (FIXED FK ISSUE)
# =================================================
@router.post("/{project_id}/delete")
def delete_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    project, role = get_project_access(db, project_id, user)

    if not project or role != "admin":
        flash(request, "Only admins can delete projects.", "error")
        return RedirectResponse("/projects/manage", status_code=302)

    old = model_to_dict(project)

    # 🔥 DELETE DEPENDENCIES FIRST (explicit deletes to avoid FK errors)
    # Use synchronize_session=False for performance and to avoid stale session issues.
    # IMPORTANT: SQLite enforces FK constraints on DELETE, so we must delete children
    # before parents (activities, project_activities, road_stretches, projects).

    # 0) Daily work system: leaf tables first (only have report_id FK)
    # These must be deleted before DailyWorkReport
    db.query(DailyWorkUpload).filter(
        DailyWorkUpload.report_id.in_(
            db.query(DailyWorkReport.id).filter(DailyWorkReport.project_id == project_id)
        )
    ).delete(synchronize_session=False)
    db.query(DailyWorkQC).filter(
        DailyWorkQC.report_id.in_(
            db.query(DailyWorkReport.id).filter(DailyWorkReport.project_id == project_id)
        )
    ).delete(synchronize_session=False)
    db.query(DailyWorkDelay).filter(
        DailyWorkDelay.report_id.in_(
            db.query(DailyWorkReport.id).filter(DailyWorkReport.project_id == project_id)
        )
    ).delete(synchronize_session=False)
    db.query(DailyWorkMachinery).filter(
        DailyWorkMachinery.report_id.in_(
            db.query(DailyWorkReport.id).filter(DailyWorkReport.project_id == project_id)
        )
    ).delete(synchronize_session=False)
    db.query(DailyWorkLabour).filter(
        DailyWorkLabour.report_id.in_(
            db.query(DailyWorkReport.id).filter(DailyWorkReport.project_id == project_id)
        )
    ).delete(synchronize_session=False)
    
    # DailyWorkActivity and DailyWorkMaterial have both report_id and project_id
    db.query(DailyWorkMaterial).filter(DailyWorkMaterial.project_id == project_id).delete(synchronize_session=False)
    db.query(DailyWorkActivity).filter(DailyWorkActivity.project_id == project_id).delete(synchronize_session=False)
    
    # Now delete DailyWorkReport (no more children)
    db.query(DailyWorkReport).filter(DailyWorkReport.project_id == project_id).delete(synchronize_session=False)

    # 1) Stretch system (children -> stretch -> project)
    # StretchMaterial -> StretchActivity -> exclusions -> RoadStretch
    # (StretchActivity references ProjectActivity; must be removed before ProjectActivity deletion.)
    db.query(StretchMaterial).filter(
        StretchMaterial.stretch_activity_id.in_(
            db.query(StretchActivity.id).join(RoadStretch, RoadStretch.id == StretchActivity.stretch_id).filter(
                RoadStretch.project_id == project_id
            )
        )
    ).delete(synchronize_session=False)
    db.query(StretchMaterialExclusion).filter(
        StretchMaterialExclusion.stretch_id.in_(
            db.query(RoadStretch.id).filter(RoadStretch.project_id == project_id)
        )
    ).delete(synchronize_session=False)
    db.query(StretchActivity).filter(
        StretchActivity.stretch_id.in_(
            db.query(RoadStretch.id).filter(RoadStretch.project_id == project_id)
        )
    ).delete(synchronize_session=False)
    db.query(RoadStretch).filter(RoadStretch.project_id == project_id).delete(synchronize_session=False)

    # 2) Project alignment points
    db.query(ProjectAlignmentPoint).filter(ProjectAlignmentPoint.project_id == project_id).delete(synchronize_session=False)

    # 3) ProjectUser entries
    db.query(ProjectUser).filter(ProjectUser.project_id == project_id).delete(synchronize_session=False)

    # 4) Activity-linked tables (must be deleted before Activity rows)
    # Note: ActivityMaterial doesn't have project_id, must delete by activity_id
    db.query(ActivityMaterial).filter(
        ActivityMaterial.activity_id.in_(
            db.query(Activity.id).filter(Activity.project_id == project_id)
        )
    ).delete(synchronize_session=False)
    
    # These have project_id
    db.query(ProcurementLog).filter(ProcurementLog.project_id == project_id).delete(synchronize_session=False)
    db.query(PredictionLog).filter(PredictionLog.project_id == project_id).delete(synchronize_session=False)
    db.query(MaterialUsage).filter(MaterialUsage.project_id == project_id).delete(synchronize_session=False)
    db.query(MaterialUsageDaily).filter(MaterialUsageDaily.project_id == project_id).delete(synchronize_session=False)
    db.query(DailyEntry).filter(DailyEntry.project_id == project_id).delete(synchronize_session=False)
    db.query(ActivityProgress).filter(ActivityProgress.project_id == project_id).delete(synchronize_session=False)

    # 5) Project-activity mappings and activities
    db.query(ProjectActivity).filter(ProjectActivity.project_id == project_id).delete(synchronize_session=False)
    db.query(Activity).filter(Activity.project_id == project_id).delete(synchronize_session=False)

    # 6) Material / stock / planning records
    db.query(PlannedMaterial).filter(PlannedMaterial.project_id == project_id).delete(synchronize_session=False)
    db.query(MaterialStock).filter(MaterialStock.project_id == project_id).delete(synchronize_session=False)

    # Finally delete project object
    db.delete(project)
    db.commit()

    log_action(
        db=db,
        request=request,
        action="DELETE",
        entity_type="Project",
        entity_id=project_id,
        description="Project deleted",
        old_value=old,
        new_value=None,
    )

    flash(request, "Project deleted successfully", "success")

    return RedirectResponse("/projects/manage", status_code=302)
