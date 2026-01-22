# ======================================================
# TEST EMAIL ROUTE (for SMTP debugging)
# ======================================================







# Ensure .env is loaded before anything else
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, environment variables must be set manually

# Ensure logging is configured to show warnings/errors
import logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
import hashlib
import traceback
from datetime import datetime, timedelta
import os
import secrets
from email.message import EmailMessage

# Centralized email utility
from app.utils.email import send_email, EmailSendError
import bcrypt

from app.db.session import engine, get_db
from app.db.base import Base
import app.db.models  # ✅ REGISTER ALL MODELS
from app.db.seed_road_presets import seed_road_presets

from app.models.user import User
from app.models.user_session import UserSession
from app.models.password_reset_otp import PasswordResetOTP
from app.models.material_vendor import MaterialVendor
from app.models.material import Material
from app.models.activity import Activity

# ======================================================
# ROUTERS
# ======================================================

from app.routes.dashboard import router as dashboard_router
from app.routes.projects import router as projects_router
from app.routes.reports import router as reports_router
from app.routes.users import router as users_router

# ADMIN
from app.routes.admin import router as admin_router
from app.routes.admin_presets import router as admin_presets_router

# PROJECT USERS
from app.routes.project_users import router as project_users_router

# PROJECT ACTIVITY PLANNING
from app.routes.project_activity_plan import router as project_activity_plan_router

# UNIFIED ACTIVITY + MATERIAL PLANNING
from app.routes.activity_material_planning import router as activity_material_planning_router

# PROJECT ACTIVITIES
from app.routes.project_activities import router as project_activities_router

# ACTIVITY PROGRESS
from app.routes.activity_progress import router as activity_progress_router

# CORE DOMAIN
from app.routes.activity import router as activity_router
from app.routes.activities import router as activities_router
from app.routes.materials import router as materials_router
from app.routes.activity_materials import router as activity_materials_router
from app.routes.material_master import router as material_master_router

# INVENTORY
from app.routes.material_stock import router as material_stock_router
from app.routes.material_daily_usage import router as material_daily_usage_router
from app.routes.inventory import router as inventory_router
from app.routes.material_requirements import router as material_requirements_router

# PROCUREMENT (VENDOR INTELLIGENCE)
from app.routes.procurement import router as procurement_router

# SCHEDULE
from app.routes.schedule import router as schedule_router

# 🔥 DAILY EXECUTION (ORDER MATTERS)
from app.routes.daily_entry_ui import router as daily_entry_ui_router   # UI (GET)
from app.routes.daily_entry import router as daily_entry_router         # API (POST)

# ANALYTICS
from app.routes.material_progress import router as material_progress_router
from app.routes.project_dashboard import router as project_dashboard_router

# PREDICTION
from app.routes.prediction import router as prediction_router

# SETTINGS
from app.routes.settings import router as settings_router

# Wizard UX (Road preset selection)
from app.routes.project_wizard import router as project_wizard_router

# 🔥 DESIGN DATA (NEW)
from app.routes.design_data import router as design_data_router   # ✅ NEW
from app.routes.road_projects import router as road_projects_router

# FLASH
from app.utils.flash import get_flashed_messages, flash
from app.utils.audit_logger import log_action
from app.utils.id_codes import ensure_activity_codes_per_project, ensure_codes
from app.utils.template_filters import register_template_filters

# ======================================================
# APP
# ======================================================
app = FastAPI(
    title="InfraCore",
    debug=False   # 🔥 IMPORTANT: prevents raw code leakage
)

# ---------------- TEMPLATES & STATIC ----------------
templates = Jinja2Templates(directory="app/templates")
register_template_filters(templates)
try:
    templates.env.auto_reload = True
    templates.env.cache = {}
except Exception:
    pass
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------- SESSION ----------------
app.add_middleware(
    SessionMiddleware,
    secret_key="infracore-secret-key",
    same_site="lax",
    https_only=False,
)

# ---------------- SESSION EXPIRY MIDDLEWARE ----------------
@app.middleware("http")
async def session_expiry_middleware(request: Request, call_next):
    if "session" in request.scope:
        session = request.session
        now = datetime.utcnow()
        max_age = 30 * 60  # 30 minutes in seconds
        last_active = session.get('last_active')
        if last_active:
            try:
                last_active_dt = datetime.strptime(last_active, "%Y-%m-%dT%H:%M:%S.%f")
            except Exception:
                last_active_dt = now
            if (now - last_active_dt).total_seconds() > max_age:
                session.clear()
                return RedirectResponse("/logout")
        session['last_active'] = now.isoformat()
    response = await call_next(request)
    return response


# ---------------- SESSION EXPIRY MIDDLEWARE ----------------
@app.middleware("http")
async def session_expiry_middleware(request: Request, call_next):
    if "session" in request.scope:
        session = request.session
        now = datetime.utcnow()
        max_age = 30 * 60  # 30 minutes in seconds
        last_active = session.get('last_active')
        if last_active:
            try:
                last_active_dt = datetime.strptime(last_active, "%Y-%m-%dT%H:%M:%S.%f")
            except Exception:
                last_active_dt = now
            if (now - last_active_dt).total_seconds() > max_age:
                session.clear()
                return RedirectResponse("/logout")
        session['last_active'] = now.isoformat()
    response = await call_next(request)
    return response

# ---------------- FLASH MIDDLEWARE ----------------
@app.middleware("http")
async def flash_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        request.state.flashes = get_flashed_messages(request)
        return response
    except Exception:
        return PlainTextResponse(
            traceback.format_exc(),
            status_code=500
        )

# ======================================================
# ROUTER REGISTRATION (STRICT ORDER)
# ======================================================

# Core UI
app.include_router(dashboard_router)
app.include_router(projects_router)
app.include_router(project_wizard_router)
app.include_router(design_data_router)   # ✅ NEW (Design Data routes)
app.include_router(road_projects_router)
app.include_router(settings_router)
app.include_router(reports_router, prefix="/reports")
app.include_router(users_router, prefix="/users")
app.include_router(admin_router)
app.include_router(admin_presets_router)

# Project Management
app.include_router(project_users_router)
app.include_router(project_activities_router)
app.include_router(project_activity_plan_router)
app.include_router(activity_material_planning_router)
app.include_router(activity_progress_router)

# Core Domain
app.include_router(activity_router)
app.include_router(activities_router)
app.include_router(materials_router)
app.include_router(activity_materials_router)

# Master data
app.include_router(material_master_router)

# Inventory
app.include_router(material_stock_router)
app.include_router(material_daily_usage_router)
app.include_router(inventory_router)
app.include_router(material_requirements_router)

# Procurement
app.include_router(procurement_router)

# Schedule
app.include_router(schedule_router)

# 🔥 DAILY EXECUTION (FIXED & WORKING)
app.include_router(daily_entry_ui_router)   # /execution (GET)
app.include_router(daily_entry_router)      # /daily-entry (POST)

# Analytics
app.include_router(material_progress_router)
app.include_router(project_dashboard_router)

# Prediction
app.include_router(prediction_router)

# Material & Vendor Management
from app.routes.material_vendor import router as material_vendor_router
app.include_router(material_vendor_router)

# ======================================================
# HELPERS
# ======================================================
def _sha256(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def hash_password(password: str) -> str:
    pw = (password or "").encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    if password_hash.startswith("$2"):
        try:
            pw = (password or "").encode("utf-8")[:72]
            return bcrypt.checkpw(pw, password_hash.encode("utf-8"))
        except Exception:
            return False
    return _sha256(password) == password_hash


def _generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _send_otp_email(to_email: str, otp: str) -> None:
    subject = "InfraCore Password Reset OTP"
    body = (
        f"Your InfraCore OTP is: {otp}\n\n"
        "This OTP is valid for 10 minutes and can be used only once."
    )
    import logging
    try:
        send_email(
            to_email=to_email,
            subject=subject,
            body=body
        )
    except EmailSendError as e:
        logging.error(f"OTP email send failed: {e}")
        pass

# ======================================================
# STARTUP
# ======================================================
@app.on_event("startup")
def startup_tasks():
    Base.metadata.create_all(bind=engine)

    db: Session = next(get_db())

    # Load standards-based preset seed files (hybrid: JSON source-of-truth + DB copy)
    try:
        seed_road_presets(db)
    except Exception:
        # Preset seeding must never block server startup
        pass

    superadmin_exists = db.query(User).filter(User.role == "superadmin").first()
    admin_user = db.query(User).filter(User.username == "admin").first()
    sajjad_user = db.query(User).filter(User.username == "Sajjad").first()

    if not superadmin_exists:
        if admin_user:
            admin_user.role = "superadmin"
            admin_user.password_hash = hash_password("admin123")
            db.add(admin_user)
            db.commit()
        else:
            db.add(
                User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    role="superadmin",
                    is_active=True,
                )
            )
            db.commit()

    if not sajjad_user:
        db.add(
            User(
                username="Sajjad",
                password_hash=hash_password("1234"),
                role="superadmin",
                is_active=True,
            )
        )
        db.commit()
    else:
        sajjad_user.password_hash = hash_password("1234")
        sajjad_user.role = "superadmin"
        sajjad_user.is_active = True
        db.add(sajjad_user)
        db.commit()
    # Ensure new columns exist (safe dev-time migration)
    try:
        with engine.begin() as conn:
            # Add project_type if missing
            conn.exec_driver_sql("ALTER TABLE projects ADD COLUMN project_type VARCHAR(50) DEFAULT ''")
    except Exception:
        # ignore if column already exists or DB doesn't support alter
        pass

    # Preset admin safety columns (dev-time migration)
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE road_presets ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
    except Exception:
        pass
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
    except Exception:
        pass
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE projects ADD COLUMN road_preset_key VARCHAR(200)")
    except Exception:
        pass

    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE projects ADD COLUMN road_construction_type VARCHAR(100)")
    except Exception:
        pass

    # ==================================================
    # MATERIAL VENDORS + DEFAULT LEAD TIME (SAFE, SQLITE)
    # ==================================================
    try:
        with engine.begin() as conn:
            try:
                conn.exec_driver_sql(
                    """
                    CREATE TABLE IF NOT EXISTS material_vendors (
                        id INTEGER PRIMARY KEY,
                        material_id INTEGER NOT NULL,
                        vendor_name VARCHAR(200) NOT NULL,
                        contact_person VARCHAR(150),
                        phone VARCHAR(50),
                        email VARCHAR(200),
                        lead_time_days INTEGER NOT NULL DEFAULT 0,
                        min_order_qty REAL,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        FOREIGN KEY(material_id) REFERENCES materials(id)
                    )
                    """
                )
                conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_material_vendors_material_id ON material_vendors(material_id)")
            except Exception:
                pass

            # materials.default_lead_time_days
            try:
                conn.exec_driver_sql("ALTER TABLE materials ADD COLUMN default_lead_time_days INTEGER")
            except Exception:
                pass

            # materials.code (human-friendly ID)
            try:
                conn.exec_driver_sql("ALTER TABLE materials ADD COLUMN code VARCHAR(30)")
            except Exception:
                pass

            # activity_materials planning columns
            for stmt in [
                "ALTER TABLE activity_materials ADD COLUMN vendor_id INTEGER",
                "ALTER TABLE activity_materials ADD COLUMN order_date DATE",
                "ALTER TABLE activity_materials ADD COLUMN lead_time_days_override INTEGER",
                "ALTER TABLE activity_materials ADD COLUMN lead_time_days INTEGER",
                "ALTER TABLE activity_materials ADD COLUMN expected_delivery_date DATE",
                "ALTER TABLE activity_materials ADD COLUMN is_material_risk BOOLEAN NOT NULL DEFAULT 0",
                "ALTER TABLE activity_materials ADD COLUMN updated_at DATETIME",
            ]:
                try:
                    conn.exec_driver_sql(stmt)
                except Exception:
                    pass
    except Exception:
        pass

    # ==================================================
    # HUMAN-FRIENDLY ID CODES (SAFE, SQLITE)
    # ==================================================
    try:
        with engine.begin() as conn:
            # activities.code (human-friendly ID)
            try:
                conn.exec_driver_sql("ALTER TABLE activities ADD COLUMN code VARCHAR(30)")
            except Exception:
                pass

            # activities.default_start_time / default_end_time (optional time-of-day defaults)
            try:
                conn.exec_driver_sql("ALTER TABLE activities ADD COLUMN default_start_time VARCHAR(10)")
            except Exception:
                pass
            try:
                conn.exec_driver_sql("ALTER TABLE activities ADD COLUMN default_end_time VARCHAR(10)")
            except Exception:
                pass
    except Exception:
        pass

    # Backfill codes for existing rows (idempotent)
    try:
        updated_materials = ensure_codes(db, Material, code_attr="code", prefix="MAT", width=6)
        updated_activities = ensure_activity_codes_per_project(db, Activity, code_attr="code", width=6, project_width=6)
        if updated_materials or updated_activities:
            db.commit()
    except Exception:
        db.rollback()

    # ==================================================
    # ROAD CLASSIFICATION + PRESET STORAGE (SAFE, SQLITE)
    # ==================================================
    try:
        with engine.begin() as conn:
            for stmt in [
                "ALTER TABLE projects ADD COLUMN road_category VARCHAR(100)",
                "ALTER TABLE projects ADD COLUMN road_engineering_type VARCHAR(150)",
                "ALTER TABLE projects ADD COLUMN road_extras_json TEXT",
                "ALTER TABLE projects ADD COLUMN preset_activities_json TEXT",
                "ALTER TABLE projects ADD COLUMN preset_materials_json TEXT",
            ]:
                try:
                    conn.exec_driver_sql(stmt)
                except Exception:
                    pass

            # Backfill road_category from legacy road_type where missing
            try:
                conn.exec_driver_sql(
                    "UPDATE projects SET road_category = road_type "
                    "WHERE (road_category IS NULL OR road_category = '') "
                    "AND road_type IS NOT NULL AND road_type != ''"
                )
            except Exception:
                pass
    except Exception:
        pass

    # ==================================================
    # ROAD PROJECT METADATA (SAFE, SQLITE)
    # Adds Road-only optional fields without affecting building workflows.
    # ==================================================
    try:
        with engine.begin() as conn:
            for stmt in [
                "ALTER TABLE projects ADD COLUMN road_name VARCHAR(255)",
                "ALTER TABLE projects ADD COLUMN lane_configuration VARCHAR(10)",
                "ALTER TABLE projects ADD COLUMN road_pavement_type VARCHAR(20)",
                "ALTER TABLE projects ADD COLUMN terrain_type VARCHAR(20)",
                "ALTER TABLE projects ADD COLUMN concrete_pavement_type VARCHAR(20)",
                "ALTER TABLE projects ADD COLUMN slab_thickness_mm INTEGER",
                "ALTER TABLE projects ADD COLUMN grade_of_concrete VARCHAR(20)",
                "ALTER TABLE projects ADD COLUMN joint_spacing_m FLOAT",
                "ALTER TABLE projects ADD COLUMN dowel_diameter_mm INTEGER",
                "ALTER TABLE projects ADD COLUMN tie_bar_diameter_mm INTEGER",
                "ALTER TABLE projects ADD COLUMN location_id INTEGER",
            ]:
                try:
                    conn.exec_driver_sql(stmt)
                except Exception:
                    pass
    except Exception:
        pass

    # ==================================================
    # ROAD STRETCH EXTENSIONS (SAFE, SQLITE)
    # Adds per-stretch classification + planned dates.
    # ==================================================
    try:
        with engine.begin() as conn:
            for stmt in [
                "ALTER TABLE road_stretches ADD COLUMN road_category VARCHAR(100)",
                "ALTER TABLE road_stretches ADD COLUMN engineering_type VARCHAR(50)",
                "ALTER TABLE road_stretches ADD COLUMN start_date DATE",
                "ALTER TABLE road_stretches ADD COLUMN end_date DATE",
                "ALTER TABLE road_stretches ADD COLUMN location_id INTEGER",
            ]:
                try:
                    conn.exec_driver_sql(stmt)
                except Exception:
                    pass
    except Exception:
        pass

    # ==================================================
    # INVENTORY METADATA (SAFE, SQLITE)
    # ==================================================
    try:
        with engine.begin() as conn:
            for stmt in [
                "ALTER TABLE materials ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
                "ALTER TABLE materials ADD COLUMN category VARCHAR(80)",
                "ALTER TABLE materials ADD COLUMN specification VARCHAR(120)",
                "ALTER TABLE materials ADD COLUMN unit_cost FLOAT",
                "ALTER TABLE material_stocks ADD COLUMN supplier VARCHAR(150)",
                "ALTER TABLE material_stocks ADD COLUMN lead_time_days_override INTEGER",
                "ALTER TABLE material_stocks ADD COLUMN storage_location VARCHAR(100)",
            ]:
                try:
                    conn.exec_driver_sql(stmt)
                except Exception:
                    pass
    except Exception:
        pass

    # ==================================================
    # SOFT-DELETE FLAGS (SAFE, SQLITE)
    # ==================================================
    try:
        with engine.begin() as conn:
            for stmt in [
                "ALTER TABLE activities ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
            ]:
                try:
                    conn.exec_driver_sql(stmt)
                except Exception:
                    pass
    except Exception:
        pass

    # ==================================================
    # ROAD CONSUMPTION (CHAINAGE-BASED) (SAFE, SQLITE)
    # ==================================================
    try:
        with engine.begin() as conn:
            for stmt in [
                "ALTER TABLE material_usage_daily ADD COLUMN chainage_start VARCHAR(50)",
                "ALTER TABLE material_usage_daily ADD COLUMN chainage_end VARCHAR(50)",
                "ALTER TABLE material_usage_daily ADD COLUMN road_layer VARCHAR(30)",
                "ALTER TABLE daily_work_materials ADD COLUMN chainage_start VARCHAR(50)",
                "ALTER TABLE daily_work_materials ADD COLUMN chainage_end VARCHAR(50)",
                "ALTER TABLE daily_work_materials ADD COLUMN road_layer VARCHAR(30)",
                "ALTER TABLE daily_work_machinery ADD COLUMN equipment_type VARCHAR(80)",
            ]:
                try:
                    conn.exec_driver_sql(stmt)
                except Exception:
                    pass
    except Exception:
        pass

    # ==================================================
    # MATERIAL REQUIREMENTS MODEL ALIGNMENT (SAFE, SQLITE)
    # Keeps inventory_service compatible with older DBs.
    # ==================================================
    try:
        with engine.begin() as conn:
            for stmt in [
                "ALTER TABLE material_usages ADD COLUMN quantity FLOAT",
                "ALTER TABLE material_usages ADD COLUMN is_planned BOOLEAN",
                "ALTER TABLE material_usages ADD COLUMN unit VARCHAR(50)",
            ]:
                try:
                    conn.exec_driver_sql(stmt)
                except Exception:
                    pass
    except Exception:
        pass

    # ==================================================
    # PLANNED MATERIALS EXTENSION (SAFE, SQLITE)
    # Adds optional stretch_id for per-stretch planning.
    # ==================================================
    try:
        with engine.begin() as conn:
            for stmt in [
                "ALTER TABLE planned_materials ADD COLUMN stretch_id INTEGER",
                "ALTER TABLE planned_materials ADD COLUMN unit VARCHAR(50)",
                "ALTER TABLE planned_materials ADD COLUMN allowed_units VARCHAR(500)",
            ]:
                try:
                    conn.exec_driver_sql(stmt)
                except Exception:
                    pass
    except Exception:
        pass

    # ==================================================
    # AUDIT LOG TABLE EXTENSION (SAFE, SQLITE)
    # Adds missing columns + indexes for enterprise audit logging.
    # ==================================================
    try:
        with engine.begin() as conn:
            # Columns (ADD COLUMN is safe to retry in SQLite)
            for stmt in [
                "ALTER TABLE activity_logs ADD COLUMN role VARCHAR(50)",
                "ALTER TABLE activity_logs ADD COLUMN entity_type VARCHAR(50)",
                "ALTER TABLE activity_logs ADD COLUMN entity_id INTEGER",
                "ALTER TABLE activity_logs ADD COLUMN description TEXT",
                "ALTER TABLE activity_logs ADD COLUMN old_value TEXT",
                "ALTER TABLE activity_logs ADD COLUMN new_value TEXT",
                "ALTER TABLE activity_logs ADD COLUMN ip_address VARCHAR(64)",
                "ALTER TABLE activity_logs ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
            ]:
                try:
                    conn.exec_driver_sql(stmt)
                except Exception:
                    pass

            # Backfill created_at from legacy timestamp for existing rows
            try:
                conn.exec_driver_sql(
                    "UPDATE activity_logs SET created_at = timestamp "
                    "WHERE created_at IS NULL AND timestamp IS NOT NULL"
                )
            except Exception:
                pass

            # Indexes
            try:
                conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_activity_logs_created_at ON activity_logs(created_at)")
            except Exception:
                pass
            try:
                conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_activity_logs_user_id ON activity_logs(user_id)")
            except Exception:
                pass
    except Exception:
        pass

    # ==================================================
    # DPR / DAILY WORK EXECUTION EXTENSION (SAFE, SQLITE)
    # Adds optional columns used by the new DPR UI.
    # ==================================================
    try:
        with engine.begin() as conn:
            try:
                conn.exec_driver_sql("ALTER TABLE daily_entries ADD COLUMN remarks VARCHAR(2000)")
            except Exception:
                pass
    except Exception:
        pass

# ======================================================
# AUTH
# ======================================================
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str | None = None):
    if request.session.get("user"):
        if next:
            n = str(next).strip()
            if n.startswith("/") and ("://" not in n) and ("\\" not in n):
                return RedirectResponse(n, status_code=302)
        return RedirectResponse("/dashboard", status_code=302)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "user": None, "next": next}
    )

@app.post("/login")
def login_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str | None = Form(None),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(func.lower(User.username) == username.lower()).first()

    if not user or not verify_password(password, user.password_hash):
        flash(request, "Invalid username or password", "error")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "user": None, "next": next}
        )

    if not user.is_active:
        flash(request, "Your account is disabled. Contact admin.", "error")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "user": None, "next": next}
        )

    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
    }

    session_log = UserSession(
        user_id=user.id,
        login_time=datetime.utcnow()
    )
    db.add(session_log)
    db.commit()

    request.session["session_log_id"] = session_log.id

    # Audit: LOGIN (best-effort)
    log_action(
        db=db,
        request=request,
        action="LOGIN",
        entity_type="User",
        entity_id=user.id,
        description="User login",
        old_value=None,
        new_value={"username": user.username, "role": user.role},
    )

    flash(request, "Logged in successfully", "success")
    if next:
        n = str(next).strip()
        if n.startswith("/") and ("://" not in n) and ("\\" not in n):
            return RedirectResponse(n, status_code=302)
    return RedirectResponse("/dashboard", status_code=302)


@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(
        "forgot_password.html",
        {"request": request, "user": None},
    )

@app.post("/forgot-password/send-otp")
def send_forgot_password_otp(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    print("OTP ROUTE TRIGGERED")
    if request.session.get("user"):
        return RedirectResponse("/dashboard", status_code=302)

    email_clean = str(email or "").strip()
    import re
    # Basic email format validation
    email_regex = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    if not re.match(email_regex, email_clean):
        return {"error": "Please enter a valid email address."}

    now = datetime.utcnow()

    user = None
    if email_clean:
        user = db.query(User).filter(func.lower(User.username) == email_clean.lower()).first()

    import logging
    if user:
        db.query(PasswordResetOTP).filter(
            PasswordResetOTP.email == email_clean,
            PasswordResetOTP.used_at.is_(None),
            PasswordResetOTP.expires_at > now,
        ).update({PasswordResetOTP.used_at: now}, synchronize_session=False)

        otp = _generate_otp()
        otp_hash = bcrypt.hashpw(otp.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")
        expires_at = now + timedelta(minutes=10)

        db.add(
            PasswordResetOTP(
                email=email_clean,
                otp_hash=otp_hash,
                expires_at=expires_at,
                attempts=0,
                verified_at=None,
                used_at=None,
            )
        )
        db.commit()

        try:
            _send_otp_email(email_clean, otp)
        except Exception as e:
            logging.error(f"OTP email send failed: {e}")
            return {"error": "Failed to send OTP email. Please try again later or contact support."}

        return {"message": "If the account exists, an OTP has been sent."}
    else:
        # Do not reveal if user exists, but always return success for non-existent users
        return {"message": "If the account exists, an OTP has been sent."}


@app.post("/forgot-password/verify-otp")
def verify_forgot_password_otp(
    request: Request,
    email: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db),
):
    if request.session.get("user"):
        return RedirectResponse("/dashboard", status_code=302)

    email_clean = str(email or "").strip()
    otp_clean = str(otp or "").strip()
    now = datetime.utcnow()

    row = (
        db.query(PasswordResetOTP)
        .filter(
            PasswordResetOTP.email == email_clean,
            PasswordResetOTP.used_at.is_(None),
            PasswordResetOTP.expires_at > now,
        )
        .order_by(PasswordResetOTP.id.desc())
        .first()
    )

    if not row:
        return {"message": "Invalid or expired OTP."}

    if row.verified_at is not None:
        return {"message": "OTP already verified."}

    if row.attempts >= 5:
        return {"message": "OTP attempts exceeded."}

    try:
        otp_ok = bcrypt.checkpw(otp_clean.encode("utf-8")[:72], row.otp_hash.encode("utf-8"))
    except Exception:
        otp_ok = False

    if not otp_ok:
        row.attempts = int(row.attempts or 0) + 1
        db.add(row)
        db.commit()
        return {"message": "Invalid or expired OTP."}

    row.verified_at = now
    db.add(row)
    db.commit()
    return {"message": "OTP verified."}


@app.post("/forgot-password/reset")
def reset_password_with_otp(
    request: Request,
    email: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    if request.session.get("user"):
        return RedirectResponse("/dashboard", status_code=302)

    email_clean = str(email or "").strip()
    now = datetime.utcnow()

    row = (
        db.query(PasswordResetOTP)
        .filter(
            PasswordResetOTP.email == email_clean,
            PasswordResetOTP.used_at.is_(None),
            PasswordResetOTP.expires_at > now,
            PasswordResetOTP.verified_at.isnot(None),
        )
        .order_by(PasswordResetOTP.id.desc())
        .first()
    )

    if not row:
        return {"message": "OTP verification required or expired."}

    user = db.query(User).filter(func.lower(User.username) == email_clean.lower()).first()
    if not user:
        return {"message": "OTP verification required or expired."}

    user.password_hash = hash_password(new_password)
    row.used_at = now
    db.add(user)
    db.add(row)
    db.commit()

    return {"message": "Password reset successful."}

@app.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    session_log_id = request.session.get("session_log_id")

    if session_log_id:
        session_log = db.query(UserSession).filter(
            UserSession.id == session_log_id
        ).first()

        if session_log and session_log.logout_time is None:
            session_log.logout_time = datetime.utcnow()
            session_log.session_duration = int(
                (session_log.logout_time - session_log.login_time).total_seconds()
            )
            db.commit()

    # Audit: LOGOUT (best-effort)
    if user:
        log_action(
            db=db,
            request=request,
            action="LOGOUT",
            entity_type="User",
            entity_id=user.get("id"),
            description="User logout",
            old_value=None,
            new_value={"username": user.get("username"), "role": user.get("role")},
        )

    request.session.clear()
    return RedirectResponse("/login", status_code=302)

# ======================================================
# ROOT
# ======================================================
@app.get("/")
def root():
    return RedirectResponse("/dashboard", status_code=302)
