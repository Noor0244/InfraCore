from __future__ import annotations

import json
import math
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.material import Material
from app.models.material_stock import MaterialStock
from app.models.material_usage_daily import MaterialUsageDaily
from app.models.material_usage import MaterialUsage


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _days_to_date(days: float) -> date:
    if not math.isfinite(days) or days <= 0:
        return date.today()
    return date.today() + timedelta(days=int(math.ceil(days)))


def _risk_level(delay_days: float, days_to_stockout: float | None) -> str:
    # Simple rule-based mapping (ML-ready later)
    if delay_days >= 5:
        return "High"
    if days_to_stockout is not None and days_to_stockout <= 7:
        return "High"
    if delay_days >= 2:
        return "Medium"
    if days_to_stockout is not None and days_to_stockout <= 14:
        return "Medium"
    return "Low"


def calculate_predictions(
    db: Session,
    project_id: int,
    project_type: str,
    mode: str,
    inputs: dict,
) -> dict:
    """Rule-based predictions (no ML training).

    Returns a structure that is intentionally ML-ready:
    - features: clean numeric/string features
    - per_material: material-level outputs
    - summary: top risk rollup
    - charts: datasets for charts
    """

    project_type_norm = (project_type or "").strip() or "Unknown"
    mode_norm = (mode or "Inventory").strip() or "Inventory"

    is_road = project_type_norm.lower() == "road"

    lead_time_buffer_days = int(_clamp(_safe_float(inputs.get("lead_time_buffer_days"), 0), 0, 90))
    safety_stock_pct = _clamp(_safe_float(inputs.get("safety_stock_pct"), 0), 0, 80)

    # Road inputs
    chainage_rate = _clamp(_safe_float(inputs.get("chainage_progress_rate"), 0.5), 0.0, 10.0)  # km/day
    road_layer = (inputs.get("road_layer") or "").strip() or None
    weather_impact = _clamp(_safe_float(inputs.get("weather_impact_factor"), 0), 0, 1)  # 0..1

    # Building inputs
    floor_rate = _clamp(_safe_float(inputs.get("floor_progress_rate"), 0.1), 0.0, 5.0)  # floors/day
    activity_id = inputs.get("activity_id")

    horizon_days = int(_clamp(_safe_float(inputs.get("horizon_days"), 14), 7, 60))

    # Pull current stock per material
    stocks = (
        db.query(MaterialStock)
        .filter(MaterialStock.project_id == project_id, MaterialStock.is_active == True)
        .all()
    )
    stock_by_material = {int(s.material_id): float(s.quantity_available or 0) for s in stocks}
    lead_override_by_material = {int(s.material_id): (s.lead_time_days_override if s.lead_time_days_override is not None else None) for s in stocks}

    materials = db.query(Material).order_by(Material.name.asc()).all()

    # Consumption history (last N days)
    start_date = date.today() - timedelta(days=horizon_days)
    usage_q = db.query(
        MaterialUsageDaily.material_id,
        func.sum(MaterialUsageDaily.quantity_used),
        func.count(func.distinct(MaterialUsageDaily.usage_date)),
    ).filter(
        MaterialUsageDaily.project_id == project_id,
        MaterialUsageDaily.usage_date >= start_date,
    )
    if is_road and road_layer:
        usage_q = usage_q.filter(MaterialUsageDaily.road_layer == road_layer)

    usage_rows = usage_q.group_by(MaterialUsageDaily.material_id).all()
    usage_stats = {
        int(mid): {
            "sum_qty": float(total or 0),
            "days": int(days or 0),
        }
        for (mid, total, days) in usage_rows
    }

    # Planned requirement (fallback signal)
    planned_rows = (
        db.query(
            MaterialUsage.material_id,
            func.sum(func.coalesce(MaterialUsage.quantity, MaterialUsage.quantity_used)),
        )
        .filter(MaterialUsage.project_id == project_id)
        .group_by(MaterialUsage.material_id)
        .all()
    )
    planned_by_material = {int(mid): float(total or 0) for (mid, total) in planned_rows}

    per_material = []
    alerts = []

    # Effective progress rate considering weather
    effective_chainage_rate = chainage_rate * (1.0 - weather_impact) if is_road else 0.0
    effective_floor_rate = floor_rate if not is_road else 0.0

    for m in materials:
        mid = int(m.id)
        stock = float(stock_by_material.get(mid, 0.0) or 0.0)

        # Simple daily consumption estimate
        st = usage_stats.get(mid)
        if st and st["days"] > 0 and st["sum_qty"] > 0:
            daily_consumption = st["sum_qty"] / max(st["days"], 1)
        else:
            # fallback: if planned exists, smear over horizon
            planned = float(planned_by_material.get(mid, 0.0) or 0.0)
            daily_consumption = planned / float(max(horizon_days, 1)) if planned > 0 else 0.0

        daily_consumption = max(daily_consumption, 0.0)

        # Safety stock means we only consider usable stock
        usable_stock = stock * (1.0 - (safety_stock_pct / 100.0))

        # Lead time
        lead_time_days = int(m.lead_time_days or 0)
        override = lead_override_by_material.get(mid)
        if override is not None:
            try:
                lead_time_days = int(override)
            except Exception:
                pass
        lead_time_days = max(0, lead_time_days)

        reorder_eta_days = lead_time_days + lead_time_buffer_days

        days_to_stockout = None
        if daily_consumption > 0:
            days_to_stockout = usable_stock / daily_consumption

        stockout_date = _days_to_date(days_to_stockout) if days_to_stockout is not None else None

        # If stockout happens before reorder arrives, that's predicted delay
        delay_days = 0.0
        if days_to_stockout is not None and days_to_stockout < reorder_eta_days:
            delay_days = float(reorder_eta_days - days_to_stockout)

        # Reorder date: reorder_eta before stockout (or now)
        reorder_in_days = 0.0
        if days_to_stockout is not None:
            reorder_in_days = max(days_to_stockout - reorder_eta_days, 0.0)

        reorder_date = date.today() + timedelta(days=int(math.floor(reorder_in_days)))

        # Reorder quantity recommendation: cover ETA window + safety margin
        recommended_qty = daily_consumption * float(max(reorder_eta_days, 1))
        recommended_qty = recommended_qty * (1.0 + (safety_stock_pct / 100.0))

        unit_cost = _safe_float(getattr(m, "unit_cost", None), 0.0)
        cost_impact = recommended_qty * unit_cost

        # Impact loss
        chainage_loss_km = delay_days * effective_chainage_rate if is_road else 0.0
        floor_loss = delay_days * effective_floor_rate if not is_road else 0.0

        risk = _risk_level(delay_days=delay_days, days_to_stockout=days_to_stockout)

        if risk in ("High", "Medium") and days_to_stockout is not None and daily_consumption > 0:
            alerts.append(
                {
                    "material_id": mid,
                    "material": m.name,
                    "message": f"{m.name} may stock out in {int(math.ceil(days_to_stockout))} days",
                    "risk": risk,
                }
            )

        per_material.append(
            {
                "material_id": mid,
                "material": m.name,
                "category": getattr(m, "category", None),
                "specification": getattr(m, "specification", None),
                "unit": m.get_standard_unit() or m.unit,
                "available_stock": stock,
                "daily_consumption": daily_consumption,
                "lead_time_days": lead_time_days,
                "buffer_days": lead_time_buffer_days,
                "reorder_eta_days": reorder_eta_days,
                "safety_stock_pct": safety_stock_pct,
                "days_to_stockout": days_to_stockout,
                "stockout_date": stockout_date.isoformat() if stockout_date else None,
                "reorder_date": reorder_date.isoformat(),
                "recommended_reorder_qty": recommended_qty,
                "delay_days": delay_days,
                "chainage_loss_km": chainage_loss_km,
                "floor_loss": floor_loss,
                "unit_cost": unit_cost if unit_cost > 0 else None,
                "cost_impact": cost_impact,
                "risk": risk,
            }
        )

    # Choose top risk row
    def _risk_rank(r: str) -> int:
        return {"High": 3, "Medium": 2, "Low": 1}.get(r, 0)

    sorted_rows = sorted(
        per_material,
        key=lambda r: (
            -_risk_rank(r.get("risk")),
            (r.get("days_to_stockout") if r.get("days_to_stockout") is not None else 1e9),
        ),
    )

    top = sorted_rows[0] if sorted_rows else None

    # Charts: for the top material only (keeps UI light)
    chart = {
        "dates": [],
        "predicted_stock": [],
        "predicted_consumption": [],
        "actual_consumption": [],
    }

    if top and top.get("material_id"):
        mid = int(top["material_id"])
        daily = float(top.get("daily_consumption") or 0)
        start_stock = float(top.get("available_stock") or 0)

        # actual consumption series from last horizon_days
        rows = (
            db.query(MaterialUsageDaily.usage_date, func.sum(MaterialUsageDaily.quantity_used))
            .filter(
                MaterialUsageDaily.project_id == project_id,
                MaterialUsageDaily.material_id == mid,
                MaterialUsageDaily.usage_date >= start_date,
            )
            .group_by(MaterialUsageDaily.usage_date)
            .order_by(MaterialUsageDaily.usage_date.asc())
            .all()
        )
        actual_map = {d.isoformat(): float(q or 0) for (d, q) in rows}

        stock_pred = start_stock
        for i in range(0, horizon_days + 1):
            d = (date.today() + timedelta(days=i)).isoformat()
            chart["dates"].append(d)
            chart["predicted_consumption"].append(daily)
            chart["actual_consumption"].append(float(actual_map.get(d, 0.0)))
            chart["predicted_stock"].append(max(stock_pred, 0.0))
            stock_pred -= daily

    summary = {
        "project_type": project_type_norm,
        "mode": mode_norm,
        "risk": top.get("risk") if top else "Low",
        "predicted_stockout_date": top.get("stockout_date") if top else None,
        "reorder_date": top.get("reorder_date") if top else date.today().isoformat(),
        "delay_days": float(top.get("delay_days") or 0) if top else 0.0,
        "chainage_loss_km": float(top.get("chainage_loss_km") or 0) if top else 0.0,
        "floor_loss": float(top.get("floor_loss") or 0) if top else 0.0,
        "cost_impact": float(top.get("cost_impact") or 0) if top else 0.0,
        "headline_material": top.get("material") if top else None,
        "recommendation": "Reorder now" if top and (top.get("days_to_stockout") is not None and top.get("days_to_stockout") <= float(top.get("reorder_eta_days") or 0)) else "Monitor" ,
    }

    features = {
        "is_road": is_road,
        "lead_time_buffer_days": lead_time_buffer_days,
        "safety_stock_pct": safety_stock_pct,
        "weather_impact_factor": weather_impact if is_road else None,
        "chainage_progress_rate": chainage_rate if is_road else None,
        "road_layer": road_layer if is_road else None,
        "floor_progress_rate": floor_rate if not is_road else None,
        "activity_id": activity_id if not is_road else None,
        "horizon_days": horizon_days,
    }

    return {
        "summary": summary,
        "alerts": alerts[:10],
        "per_material": per_material,
        "charts": {
            "top_material": top.get("material") if top else None,
            "inventory_vs_time": chart,
        },
        "features": features,
    }


def dumps_compact(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
