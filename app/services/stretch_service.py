from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.activity_material import ActivityMaterial
from app.models.planned_material import PlannedMaterial
from app.models.project_activity import ProjectActivity
from app.models.road_stretch import RoadStretch
from app.models.stretch import Stretch as LegacyStretch
from app.models.stretch_activity import StretchActivity
from app.models.stretch_material import StretchMaterial
from app.models.stretch_material_exclusion import StretchMaterialExclusion
from app.utils.stretch_generation import generate_stretch_segments


@dataclass(frozen=True)
class StretchGenerationResult:
    project_id: int
    created_count: int
    stretches: list[RoadStretch]


def generate_stretches(
    project_id: int,
    total_length_m: int,
    number_of_stretches: int | None = None,
    stretch_length_m: int | None = None,
    *,
    deactivate_existing: bool = True,
) -> StretchGenerationResult:
    """Generate and persist stretches for a project.

    - Uses a DB transaction
    - Optionally deactivates existing active stretches
    - Raises ValueError for invalid inputs
    """
    db: Session = SessionLocal()
    try:
        preview = generate_stretch_segments(
            total_length_m=int(total_length_m),
            number_of_stretches=int(number_of_stretches) if number_of_stretches is not None else None,
            stretch_length_m=int(stretch_length_m) if stretch_length_m is not None else None,
        )

        if deactivate_existing:
            db.query(RoadStretch).filter(
                RoadStretch.project_id == int(project_id),
                RoadStretch.is_active == True,
            ).update({RoadStretch.is_active: False})

        created: list[RoadStretch] = []
        for row in preview:
            stretch = RoadStretch(
                project_id=int(project_id),
                stretch_code=str(row["stretch_code"]),
                stretch_name=str(row["stretch_name"]),
                start_chainage=str(row["start_chainage"]),
                end_chainage=str(row["end_chainage"]),
                length_m=int(row["length_m"]),
                sequence_no=int(row["sequence_no"]),
                is_active=True,
            )
            created.append(stretch)
            db.add(stretch)

        db.commit()

        return StretchGenerationResult(
            project_id=int(project_id),
            created_count=len(created),
            stretches=created,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def apply_activities_to_stretches(
    project_id: int,
    mode: str = "ALL",
    *,
    stretch_ids: list[int] | None = None,
    project_activity_ids: list[int] | None = None,
    overwrite_existing: bool = False,
) -> int:
    """Create StretchActivity mappings.

    Modes:
    - ALL: apply all project activities to all active stretches
    - SELECTIVE: apply provided project_activity_ids to provided stretch_ids

    Returns number of created mappings.
    """
    mode = (mode or "").strip().upper()
    db: Session = SessionLocal()
    try:
        stretches_q = db.query(RoadStretch).filter(
            RoadStretch.project_id == int(project_id),
            RoadStretch.is_active == True,
        )
        if mode == "SELECTIVE":
            if not stretch_ids or not project_activity_ids:
                raise ValueError("SELECTIVE mode requires stretch_ids and project_activity_ids")
            stretches_q = stretches_q.filter(RoadStretch.id.in_([int(x) for x in stretch_ids]))

        stretches = stretches_q.order_by(RoadStretch.sequence_no.asc()).all()
        if not stretches:
            return 0

        pa_q = (
            db.query(ProjectActivity)
            .filter(
                ProjectActivity.project_id == int(project_id),
                ProjectActivity.activity_scope == "STRETCH",
            )
        )
        if mode == "SELECTIVE":
            pa_q = pa_q.filter(ProjectActivity.id.in_([int(x) for x in project_activity_ids]))

        project_activities = pa_q.order_by(ProjectActivity.id.asc()).all()
        if not project_activities:
            return 0

        created = 0

        for stretch in stretches:
            if overwrite_existing:
                db.query(StretchActivity).filter(
                    StretchActivity.stretch_id == int(stretch.id),
                    StretchActivity.is_active == True,
                ).update({StretchActivity.is_active: False})

            legacy_stretch = (
                db.query(LegacyStretch)
                .filter(LegacyStretch.id == int(stretch.id))
                .first()
            )
            if not legacy_stretch:
                legacy_stretch = LegacyStretch(
                    id=int(stretch.id),
                    project_id=int(project_id),
                    sequence_no=int(getattr(stretch, "sequence_no", 0) or 0),
                    name=str(getattr(stretch, "stretch_name", "") or ""),
                    code=str(getattr(stretch, "stretch_code", "") or ""),
                    length_m=int(getattr(stretch, "length_m", 0) or 0),
                    planned_start_date=stretch.planned_start_date,
                    planned_end_date=stretch.planned_end_date,
                    manual_override=False,
                )
                db.add(legacy_stretch)
                db.flush()

            for pa in project_activities:
                # prevent duplicates (best-effort)
                exists = (
                    db.query(StretchActivity)
                    .filter(
                        StretchActivity.stretch_id == int(stretch.id),
                        StretchActivity.project_activity_id == int(pa.id),
                        StretchActivity.is_active == True,
                    )
                    .first()
                )
                if exists:
                    continue

                activity_name = "Activity"
                try:
                    activity_name = str(getattr(getattr(pa, "activity", None), "name", "") or "Activity")
                except Exception:
                    activity_name = "Activity"
                sa = StretchActivity(
                    stretch_id=int(stretch.id),
                    project_activity_id=int(pa.id),
                    name=activity_name,
                    planned_start_date=None,
                    planned_end_date=None,
                    planned_duration_hours=float(getattr(pa, "default_duration_hours", None)) if getattr(pa, "default_duration_hours", None) is not None else None,
                    planned_quantity=None,
                    actual_quantity=None,
                    progress_percent=None,
                    is_active=True,
                )
                db.add(sa)
                created += 1

        db.commit()
        return created
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def compute_stretch_materials(project_id: int, *, overwrite_existing: bool = False) -> int:
    """Compute StretchMaterial rows from StretchActivity + ActivityMaterial consumption_rate.

    required_quantity = planned_quantity * consumption_rate

    Notes:
    - This uses PlannedMaterial as the existing project-level material selection.
    - If a project has no stretches or no stretch activities, returns 0.
    """
    db: Session = SessionLocal()
    try:
        stretches = db.query(RoadStretch.id).filter(
            RoadStretch.project_id == int(project_id),
            RoadStretch.is_active == True,
        )
        stretch_ids = [int(r[0]) for r in stretches.all()]
        if not stretch_ids:
            return 0

        stretch_acts = (
            db.query(StretchActivity)
            .join(RoadStretch, RoadStretch.id == StretchActivity.stretch_id)
            .filter(
                RoadStretch.project_id == int(project_id),
                RoadStretch.is_active == True,
                StretchActivity.is_active == True,
            )
            .all()
        )
        if not stretch_acts:
            return 0

        # Map of material_id -> PlannedMaterial.id for this project
        planned = (
            db.query(PlannedMaterial)
            .filter(
                PlannedMaterial.project_id == int(project_id),
                PlannedMaterial.stretch_id == None,  # noqa: E711
            )
            .all()
        )
        planned_by_material_id = {int(pm.material_id): int(pm.id) for pm in planned}

        # Optional per-stretch exclusions
        excluded_rows = (
            db.query(StretchMaterialExclusion.stretch_id, StretchMaterialExclusion.material_id)
            .filter(StretchMaterialExclusion.stretch_id.in_(stretch_ids))
            .all()
        )
        excluded_by_stretch: dict[int, set[int]] = {}
        for sid, mid in excluded_rows:
            excluded_by_stretch.setdefault(int(sid), set()).add(int(mid))

        created = 0
        for sa in stretch_acts:
            if overwrite_existing:
                db.query(StretchMaterial).filter(StretchMaterial.stretch_activity_id == int(sa.id)).delete()

            if sa.planned_quantity is None:
                continue

            # Consumption rates are defined at Activity level.
            # Get activity_id from ProjectActivity.
            pa = db.query(ProjectActivity).filter(ProjectActivity.id == int(sa.project_activity_id)).first()
            if not pa:
                continue

            links = db.query(ActivityMaterial).filter(ActivityMaterial.activity_id == int(pa.activity_id)).all()
            for link in links:
                material_id = int(link.material_id)
                if material_id in excluded_by_stretch.get(int(sa.stretch_id), set()):
                    continue
                project_material_id = planned_by_material_id.get(material_id)
                if not project_material_id:
                    # project hasn't selected/planned this material -> skip (non-breaking)
                    continue

                required_qty = float(sa.planned_quantity) * float(link.consumption_rate)
                sm = StretchMaterial(
                    stretch_activity_id=int(sa.id),
                    project_material_id=int(project_material_id),
                    material_id=int(material_id),
                    required_quantity=float(required_qty),
                    consumed_quantity=0.0,
                    balance_quantity=float(required_qty),
                )
                db.add(sm)
                created += 1

        db.commit()
        return created
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
