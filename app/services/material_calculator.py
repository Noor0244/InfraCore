# app/services/material_calculator.py
# --------------------------------------------------
# Auto Material Requirement Calculator (FINAL)
# InfraCore - Construction Planning Logic
# --------------------------------------------------

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.project import Project
from app.models.project_activity import ProjectActivity
from app.models.activity_material import ActivityMaterial
from app.models.material import Material
from app.models.material_usage import MaterialUsage


class MaterialRequirementCalculator:
    """
    Calculates planned material requirement for a project
    based on:
    - Project Activities
    - Activity-Material consumption rates
    - Planned quantities
    """

    def __init__(self, db: Session):
        self.db = db

    def calculate_for_project(self, project_id: int) -> dict:
        """
        Main entry point.
        Returns material-wise total required quantity
        and stores results in DB.
        """

        # ------------------------------
        # 1. Validate Project
        # ------------------------------
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("Project not found")

        # ------------------------------
        # 2. Fetch Project Activities
        # ------------------------------
        project_activities = (
            self.db.query(ProjectActivity)
            .filter(ProjectActivity.project_id == project_id)
            .all()
        )

        if not project_activities:
            return {}

        # ------------------------------
        # 3. Clear old planned data
        # ------------------------------
        self.db.query(MaterialUsage).filter(
            MaterialUsage.project_id == project_id,
            MaterialUsage.is_planned == True
        ).delete()

        # ------------------------------
        # 4. Calculation Container
        # ------------------------------
        material_totals = {}

        # ------------------------------
        # 5. Core Calculation Loop
        # ------------------------------
        for pa in project_activities:
            planned_qty = pa.planned_quantity

            if planned_qty is None or planned_qty <= 0:
                continue

            activity_materials = (
                self.db.query(ActivityMaterial)
                .filter(ActivityMaterial.activity_id == pa.activity_id)
                .all()
            )

            for am in activity_materials:
                if am.consumption_rate is None or am.consumption_rate <= 0:
                    continue

                required_qty = planned_qty * am.consumption_rate

                material_totals[am.material_id] = (
                    material_totals.get(am.material_id, 0) + required_qty
                )

        # ------------------------------
        # 6. Persist Planned Usage
        # ------------------------------
        for material_id, qty in material_totals.items():
            usage = MaterialUsage(
                project_id=project_id,
                material_id=material_id,
                quantity=qty,
                is_planned=True
            )
            self.db.add(usage)

        self.db.commit()

        # ------------------------------
        # 7. Human-Readable Output
        # ------------------------------
        result = (
            self.db.query(
                Material.name,
                MaterialUsage.quantity
            )
            .join(MaterialUsage, Material.id == MaterialUsage.material_id)
            .filter(
                MaterialUsage.project_id == project_id,
                MaterialUsage.is_planned == True
            )
            .order_by(Material.name)
            .all()
        )

        return {
            row.name: row.quantity for row in result
        }
