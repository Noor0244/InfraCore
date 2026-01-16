# This file ONLY imports models so SQLAlchemy can see them
# DO NOT add logic here

# -------- USER & AUTH --------
from app.models.user import User
from app.models.user_session import UserSession   # ✅ ADDED
from app.models.user_setting import UserSetting

# -------- CORE PROJECT (PLANNED CONTAINER) --------
from app.models.project import Project
from app.models.road_type import RoadType
from app.models.road_preset import RoadPreset, PresetActivity, PresetMaterial, PresetActivityMaterialMap
from app.models.project_wizard import ProjectWizardState

# -------- ROAD STRETCH / CHAINAGE (OPTIONAL EXTENSION) --------
from app.models.road_stretch import RoadStretch
from app.models.road_geometry import RoadGeometry
from app.models.pavement_design import PavementDesign
from app.models.location import Location
from app.models.stretch_activity import StretchActivity
from app.models.stretch_material import StretchMaterial
from app.models.stretch_material_exclusion import StretchMaterialExclusion

# -------- ACTIVITIES --------
from app.models.activity import Activity
from app.models.project_activity import ProjectActivity
from app.models.activity_progress import ActivityProgress

# -------- MATERIAL & INVENTORY (PLANNED + ACTUAL) --------
from app.models.material import Material
from app.models.material_vendor import MaterialVendor
from app.models.planned_material import PlannedMaterial   # ✅ ADDED (CRITICAL)
from app.models.inventory import Inventory
from app.models.activity_material import ActivityMaterial

# -------- DAILY & ACTUAL USAGE --------
from app.models.daily_entry import DailyEntry
from app.models.material_usage import MaterialUsage
from app.models.material_usage_daily import MaterialUsageDaily
from app.models.material_stock import MaterialStock

# -------- PROCUREMENT (VENDOR INTELLIGENCE) --------
from app.models.procurement_log import ProcurementLog

# -------- DAILY WORK REPORT (DPR / SITE READY) --------
from app.models.daily_work_report import DailyWorkReport
from app.models.daily_work_labour import DailyWorkLabour
from app.models.daily_work_machinery import DailyWorkMachinery
from app.models.daily_work_qc import DailyWorkQC
from app.models.daily_work_delay import DailyWorkDelay
from app.models.daily_work_activity import DailyWorkActivity
from app.models.daily_work_material import DailyWorkMaterial
from app.models.daily_work_upload import DailyWorkUpload

# -------- REPORTS & LOGS --------
from app.models.report import Report
from app.models.activity_log import ActivityLog
from app.models.project_user import ProjectUser

# -------- PREDICTION (AUDIT / HISTORY) --------
from app.models.prediction_log import PredictionLog
