from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.activity_progress import ActivityProgress
from app.models.material_usage import MaterialUsage
from app.models.material_usage_daily import MaterialUsageDaily
from app.models.material import Material


BUFFER_RATIO = 0.05  # 5% allowable buffer


def get_material_progress_analytics(
    db: Session,
    project_id: int,
    activity_id: int
) -> Dict:
    """
    Compare planned vs actual material usage based on activity progress %
    """

    # ------------------ Get progress ------------------
    progress = (
        db.query(ActivityProgress)
        .filter(
            ActivityProgress.project_id == project_id,
            ActivityProgress.activity_id == activity_id
        )
        .first()
    )

    if not progress:
        raise ValueError("Activity progress not found")

    progress_percent = progress.progress_percent or 0

    # ------------------ Planned materials ------------------
    planned_materials = (
        db.query(
            MaterialUsage.material_id,
            MaterialUsage.quantity.label("planned_total")
        )
        .filter(
            MaterialUsage.project_id == project_id,
            MaterialUsage.activity_id == activity_id
        )
        .all()
    )

    results: List[Dict] = []

    for pm in planned_materials:
        planned_total = float(pm.planned_total or 0)
        planned_till_date = planned_total * (progress_percent / 100.0)

        # ------------------ Actual usage ------------------
        actual_used = (
            db.query(func.coalesce(func.sum(MaterialUsageDaily.quantity), 0))
            .filter(
                MaterialUsageDaily.project_id == project_id,
                MaterialUsageDaily.activity_id == activity_id,
                MaterialUsageDaily.material_id == pm.material_id
            )
            .scalar()
        )

        variance = actual_used - planned_till_date

        # ------------------ Status logic ------------------
        if actual_used <= planned_till_date:
            status = "OK"
        elif actual_used <= planned_till_date * (1 + BUFFER_RATIO):
            status = "WARNING"
        else:
            status = "OVER_CONSUMPTION"

        # Optional: material name for readability
        material = db.query(Material).get(pm.material_id)

        results.append({
            "material_id": pm.material_id,
            "material_name": material.name if material else None,
            "planned_total": round(planned_total, 3),
            "planned_till_date": round(planned_till_date, 3),
            "actual_used": round(actual_used, 3),
            "variance": round(variance, 3),
            "status": status
        })

    return {
        "project_id": project_id,
        "activity_id": activity_id,
        "progress_percent": progress_percent,
        "materials": results
    }
