"""
Analytics endpoints — KPI, heatmap, ABC suggestions, expiry alerts.

GET /analytics/kpi              — Ombor KPI (throughput, receipt/shipment counts)
GET /analytics/heatmap          — Yacheyka faollik xaritasi (son va koordinata)
GET /analytics/abc-suggestions  — Re-slotting tavsiyalari
GET /analytics/expiry-alerts    — Muddat yaqinlashgan partiyalar
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, ensure_warehouse_access, get_db, require_permission
from app.services.analytics import (
    compute_abc_suggestions, get_dashboard, get_expiry_alerts, get_heatmap, get_kpi,
    get_location_history, get_occupancy, get_returns_analytics, get_throughput,
    get_zone_summary,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/kpi", dependencies=[require_permission("analytics", "view")])
async def kpi(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    result = await get_kpi(db, warehouse_id=warehouse_id, days=days)
    return {
        "warehouse_id": str(result.warehouse_id),
        "period_days": result.period_days,
        "receipts": result.total_receipts,
        "shipments": result.total_shipments,
        "units_in": result.total_units_in,
        "units_out": result.total_units_out,
        "throughput_per_day": result.throughput_units_per_day,
        "open_tasks": result.open_tasks_count,
        "sku_count": result.total_sku_count,
        "units_on_hand": result.total_units_on_hand,
        "open_pallets": result.open_pallets_count,
    }


@router.get("/heatmap", dependencies=[require_permission("analytics", "view")])
async def heatmap(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    days: int = Query(default=30, ge=1, le=365),
) -> list[dict]:
    points = await get_heatmap(db, warehouse_id=warehouse_id, days=days)
    return [
        {
            "location_id": str(p.location_id),
            "location_code": p.location_code,
            "zone_id": str(p.zone_id),
            "x": p.x,
            "y": p.y,
            "move_count": p.move_count,
            "last_activity": p.last_activity.isoformat() if p.last_activity else None,
        }
        for p in points
    ]


@router.get("/abc-suggestions", dependencies=[require_permission("analytics", "view")])
async def abc_suggestions(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    days: int = Query(default=30, ge=7, le=365),
) -> list[dict]:
    suggestions = await compute_abc_suggestions(db, warehouse_id=warehouse_id, days=days)
    return [
        {
            "product_id": str(s.product_id),
            "current_abc": s.current_abc.value if s.current_abc else None,
            "suggested_abc": s.suggested_abc.value,
            "move_count_30d": s.move_count_30d,
            "reason": s.reason,
        }
        for s in suggestions
    ]


@router.get("/expiry-alerts", dependencies=[require_permission("analytics", "view")])
async def expiry_alerts(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    warn_days: int = Query(default=30, ge=1, le=180),
) -> list[dict]:
    alerts = await get_expiry_alerts(db, warehouse_id=warehouse_id, warn_days=warn_days)
    return [
        {
            "product_id": str(a.product_id),
            "batch_id": str(a.batch_id),
            "lot_number": a.lot_number,
            "expiry_date": a.expiry_date,
            "days_remaining": a.days_remaining,
            "total_qty": a.total_qty,
            "locations": a.locations,
        }
        for a in alerts
    ]


@router.get("/throughput", dependencies=[require_permission("analytics", "view")])
async def throughput(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    days: int = Query(default=14, ge=1, le=90),
) -> list[dict]:
    await ensure_warehouse_access(db, user, warehouse_id)
    return await get_throughput(db, warehouse_id=warehouse_id, days=days)


@router.get("/location-history", dependencies=[require_permission("analytics", "view")])
async def location_history(
    user: ActiveUser,
    db: DB,
    location_id: uuid.UUID = ...,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict]:
    return await get_location_history(db, location_id=location_id, limit=limit)


@router.get("/dashboard", dependencies=[require_permission("analytics", "view")])
async def dashboard(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
) -> dict:
    await ensure_warehouse_access(db, user, warehouse_id)
    return await get_dashboard(db, warehouse_id=warehouse_id)


@router.get("/occupancy", dependencies=[require_permission("analytics", "view")])
async def occupancy(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
) -> list[dict]:
    await ensure_warehouse_access(db, user, warehouse_id)
    return await get_occupancy(db, warehouse_id=warehouse_id)


@router.get("/returns", dependencies=[require_permission("analytics", "view")])
async def returns_analytics(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    days: int = Query(default=30, ge=1, le=180),
) -> dict:
    await ensure_warehouse_access(db, user, warehouse_id)
    return await get_returns_analytics(db, warehouse_id=warehouse_id, days=days)


@router.get("/zone-summary", dependencies=[require_permission("analytics", "view")])
async def zone_summary(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    days: int = Query(default=30, ge=1, le=180),
) -> list[dict]:
    await ensure_warehouse_access(db, user, warehouse_id)
    return await get_zone_summary(db, warehouse_id=warehouse_id, days=days)
