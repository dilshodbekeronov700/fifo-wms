"""Export endpoints (TZ §10) — stream current stock and reconciliation reports
as CSV / Excel / PDF. Tenant-guarded and RBAC-protected (export:view)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, ensure_warehouse_access, get_db, require_permission
from app.models.inventory import Batch, Product, StockItem
from app.models.warehouse import Location, Zone
from app.services import export as export_svc
from app.services.reconciliation import run_reconciliation

router = APIRouter(prefix="/export", tags=["export"])
DB = Annotated[AsyncSession, Depends(get_db)]


def _stream(content: bytes, media_type: str, filename: str) -> StreamingResponse:
    """Wrap rendered bytes in a download StreamingResponse."""
    import io

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/stock", dependencies=[require_permission("export", "view")])
async def export_stock(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    format: str = "csv",
):
    """Export current stock (StockItem + Location + Zone + Product + Batch)."""
    await ensure_warehouse_access(db, user, warehouse_id)

    q = (
        select(
            Location.code.label("location_code"),
            Zone.name.label("zone_name"),
            Product.smartup_product_code.label("product_code"),
            Product.gtin.label("gtin"),
            Product.name.label("product_name"),
            Product.category.label("category"),
            Batch.lot_number.label("batch"),
            Batch.expiry_date.label("expiry_date"),
            StockItem.qty,
            StockItem.qty_booked,
            StockItem.status,
            StockItem.pallet_open,
        )
        .select_from(StockItem)
        .join(Location, StockItem.location_id == Location.id)
        .join(Zone, Location.zone_id == Zone.id)
        .join(Product, StockItem.product_id == Product.id)
        .outerjoin(Batch, StockItem.batch_id == Batch.id)
        .where(StockItem.warehouse_id == warehouse_id)
        .order_by(Location.code, Product.id)
    )
    result = await db.execute(q)

    fieldnames = [
        "location_code",
        "zone_name",
        "product_code",
        "gtin",
        "product_name",
        "category",
        "batch",
        "expiry_date",
        "qty",
        "qty_booked",
        "available",
        "status",
        "pallet_open",
    ]
    rows: list[dict] = []
    for r in result.all():
        # Product.name is a JSON dict like {"ru": "...", "uz": "..."}.
        name = r.product_name
        if isinstance(name, dict):
            name = name.get("ru") or name.get("uz") or next(iter(name.values()), "")
        rows.append(
            {
                "location_code": r.location_code,
                "zone_name": r.zone_name,
                "product_code": r.product_code,
                "gtin": r.gtin,
                "product_name": name,
                "category": r.category,
                "batch": r.batch,
                "expiry_date": r.expiry_date or "",
                "qty": r.qty,
                "qty_booked": r.qty_booked,
                "available": (r.qty or 0) - (r.qty_booked or 0),
                "status": r.status.value if r.status is not None else "",
                "pallet_open": r.pallet_open,
            }
        )

    content, media, ext = export_svc.render(
        rows, fmt=format, fieldnames=fieldnames, title="Stock"
    )
    filename = f"stock_{warehouse_id}.{ext}"
    return _stream(content, media, filename)


@router.get("/reconciliation", dependencies=[require_permission("export", "view")])
async def export_reconciliation(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    format: str = "csv",
):
    """Export the WMS ↔ Smartup reconciliation report (TZ §10)."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    wh = await ensure_warehouse_access(db, user, warehouse_id)
    smartup_warehouse_code = getattr(wh, "smartup_warehouse_code", None)
    if not smartup_warehouse_code:
        raise HTTPException(
            status_code=400,
            detail="Warehouse has no smartup_warehouse_code configured",
        )

    # Smartup client is best-effort: if the connector is not configured we still
    # produce a report (reconciliation will then fail loudly), so guard the build.
    smartup_client = None
    try:
        from app.core.connector_factory import get_smartup_client

        smartup_client = await get_smartup_client(db, user.tenant_id)
    except Exception:
        smartup_client = None

    if smartup_client is None:
        raise HTTPException(
            status_code=400,
            detail="Smartup connector not configured for this tenant",
        )

    report = await run_reconciliation(
        db,
        tenant_id=user.tenant_id,
        warehouse_id=warehouse_id,
        smartup_warehouse_code=smartup_warehouse_code,
        smartup_client=smartup_client,
    )

    fieldnames = [
        "smartup_product_code",
        "product_id",
        "wms_qty",
        "smartup_qty",
        "diff",
        "direction",
    ]
    rows = [
        {
            "smartup_product_code": line.get("smartup_product_code") or "",
            "product_id": str(line.get("product_id")) if line.get("product_id") else "",
            "wms_qty": line.get("wms_qty"),
            "smartup_qty": line.get("smartup_qty"),
            "diff": line.get("diff"),
            "direction": line.get("direction") or "",
        }
        for line in report.get("lines", [])
    ]

    content, media, ext = export_svc.render(
        rows, fmt=format, fieldnames=fieldnames, title="Reconciliation"
    )
    filename = f"reconciliation_{warehouse_id}.{ext}"
    return _stream(content, media, filename)


# ─── Yangi hisobotlar (Faza 4) ────────────────────────────────────────────────

def _pname(name) -> str:
    if isinstance(name, dict):
        return name.get("ru") or name.get("uz") or next(iter(name.values()), "")
    return name or ""


@router.get("/temperature", dependencies=[require_permission("export", "view")])
async def export_temperature(
    user: ActiveUser, db: DB, warehouse_id: uuid.UUID = ..., hours: int = 168, format: str = "csv",
):
    """IoT harorat/namlik tarixi hisoboti."""
    from datetime import datetime, timezone, timedelta
    from app.models.sensor import Sensor, SensorReading
    await ensure_warehouse_access(db, user, warehouse_id)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = (
        select(Sensor.name, SensorReading.temperature, SensorReading.humidity, SensorReading.recorded_at)
        .select_from(SensorReading)
        .join(Sensor, SensorReading.sensor_id == Sensor.id)
        .where(Sensor.warehouse_id == warehouse_id, SensorReading.recorded_at >= since)
        .order_by(SensorReading.recorded_at.desc())
    )
    res = await db.execute(q)
    fieldnames = ["sensor", "temperature_c", "humidity_pct", "time"]
    rows = [
        {"sensor": r.name, "temperature_c": r.temperature, "humidity_pct": r.humidity,
         "time": r.recorded_at.isoformat()}
        for r in res.all()
    ]
    content, media, ext = export_svc.render(rows, fmt=format, fieldnames=fieldnames, title="Temperature")
    return _stream(content, media, f"temperature_{warehouse_id}.{ext}")


@router.get("/movement", dependencies=[require_permission("export", "view")])
async def export_movement(
    user: ActiveUser, db: DB, warehouse_id: uuid.UUID = ..., days: int = 30, format: str = "csv",
):
    """Harakat (ledger) hisoboti — kirim/chiqim/ko'chirish."""
    from datetime import datetime, timezone, timedelta
    from app.models.ledger import LedgerEntry
    await ensure_warehouse_access(db, user, warehouse_id)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        select(
            LedgerEntry.created_at, LedgerEntry.action, LedgerEntry.qty_delta,
            LedgerEntry.reason, Product.name.label("pname"), Product.smartup_product_code,
        )
        .select_from(LedgerEntry)
        .outerjoin(Product, LedgerEntry.product_id == Product.id)
        .where(LedgerEntry.warehouse_id == warehouse_id, LedgerEntry.created_at >= since)
        .order_by(LedgerEntry.created_at.desc())
    )
    res = await db.execute(q)
    fieldnames = ["time", "action", "product_code", "product", "qty_delta", "reason"]
    rows = [
        {"time": r.created_at.isoformat(), "action": r.action.value if r.action else "",
         "product_code": r.smartup_product_code or "", "product": _pname(r.pname),
         "qty_delta": r.qty_delta, "reason": r.reason or ""}
        for r in res.all()
    ]
    content, media, ext = export_svc.render(rows, fmt=format, fieldnames=fieldnames, title="Movement")
    return _stream(content, media, f"movement_{warehouse_id}.{ext}")


@router.get("/expiry", dependencies=[require_permission("export", "view")])
async def export_expiry(
    user: ActiveUser, db: DB, warehouse_id: uuid.UUID = ..., format: str = "csv",
):
    """Muddat (FEFO) hisoboti — partiyalar yaroqlilik bo'yicha, qoldiq bilan."""
    await ensure_warehouse_access(db, user, warehouse_id)
    q = (
        select(
            Product.smartup_product_code, Product.name.label("pname"),
            Batch.lot_number, Batch.expiry_date, StockItem.qty, Location.code.label("loc"),
        )
        .select_from(StockItem)
        .join(Product, StockItem.product_id == Product.id)
        .join(Batch, StockItem.batch_id == Batch.id)
        .join(Location, StockItem.location_id == Location.id)
        .where(StockItem.warehouse_id == warehouse_id, Batch.expiry_date.isnot(None))
        .order_by(Batch.expiry_date)
    )
    res = await db.execute(q)
    fieldnames = ["expiry_date", "product_code", "product", "batch", "location", "qty"]
    rows = [
        {"expiry_date": r.expiry_date or "", "product_code": r.smartup_product_code or "",
         "product": _pname(r.pname), "batch": r.lot_number or "", "location": r.loc, "qty": r.qty}
        for r in res.all()
    ]
    content, media, ext = export_svc.render(rows, fmt=format, fieldnames=fieldnames, title="Expiry (FEFO)")
    return _stream(content, media, f"expiry_{warehouse_id}.{ext}")
