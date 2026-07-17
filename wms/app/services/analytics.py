"""
Analytics service — KPI, ABC analysis, heatmap, expiry alerts.

All queries run against LedgerEntry (source of truth) +
StockItem cache (for fast balance lookups).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import (
    Batch, BatchStatus, Product, StockItem, StockStatus, AbcClass,
)
from app.models.ledger import LedgerAction, LedgerEntry
from app.models.warehouse import Location


# ── Heatmap ──────────────────────────────────────────────────────────────────

@dataclass
class LocationHeatPoint:
    location_id: uuid.UUID
    location_code: str
    zone_id: uuid.UUID
    x: float | None
    y: float | None
    move_count: int          # total pick/putaway events in period
    last_activity: datetime | None


async def get_heatmap(
    db: AsyncSession,
    *,
    warehouse_id: uuid.UUID,
    days: int = 30,
) -> list[LocationHeatPoint]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    picking_actions = [LedgerAction.PICK, LedgerAction.PUTAWAY, LedgerAction.MOVE, LedgerAction.SHIPMENT]

    result = await db.execute(
        select(
            LedgerEntry.from_location_id.label("loc_id"),
            func.count(LedgerEntry.id).label("cnt"),
            func.max(LedgerEntry.created_at).label("last_at"),
        )
        .where(
            LedgerEntry.warehouse_id == warehouse_id,
            LedgerEntry.action.in_(picking_actions),
            LedgerEntry.from_location_id.isnot(None),
            LedgerEntry.created_at >= since,
        )
        .group_by(LedgerEntry.from_location_id)
    )
    rows = {row.loc_id: (row.cnt, row.last_at) for row in result.all()}

    # Also count to_location
    result2 = await db.execute(
        select(
            LedgerEntry.to_location_id.label("loc_id"),
            func.count(LedgerEntry.id).label("cnt"),
            func.max(LedgerEntry.created_at).label("last_at"),
        )
        .where(
            LedgerEntry.warehouse_id == warehouse_id,
            LedgerEntry.action.in_(picking_actions),
            LedgerEntry.to_location_id.isnot(None),
            LedgerEntry.created_at >= since,
        )
        .group_by(LedgerEntry.to_location_id)
    )
    for row in result2.all():
        if row.loc_id in rows:
            c, la = rows[row.loc_id]
            rows[row.loc_id] = (c + row.cnt, max(la, row.last_at) if la and row.last_at else la or row.last_at)
        else:
            rows[row.loc_id] = (row.cnt, row.last_at)

    # Load location details
    loc_ids = list(rows.keys())
    if not loc_ids:
        return []

    locs_result = await db.execute(
        select(Location).where(Location.id.in_(loc_ids))
    )
    locs = {loc.id: loc for loc in locs_result.scalars()}

    points: list[LocationHeatPoint] = []
    for loc_id, (cnt, last_at) in rows.items():
        loc = locs.get(loc_id)
        if loc is None:
            continue
        points.append(
            LocationHeatPoint(
                location_id=loc_id,
                location_code=loc.code,
                zone_id=loc.zone_id,
                x=loc.x,
                y=loc.y,
                move_count=cnt,
                last_activity=last_at,
            )
        )
    points.sort(key=lambda p: p.move_count, reverse=True)
    return points


# ── ABC Re-slotting ───────────────────────────────────────────────────────────

@dataclass
class AbcSuggestion:
    product_id: uuid.UUID
    current_abc: AbcClass | None
    suggested_abc: AbcClass
    move_count_30d: int
    reason: str


async def compute_abc_suggestions(
    db: AsyncSession,
    *,
    warehouse_id: uuid.UUID,
    days: int = 30,
) -> list[AbcSuggestion]:
    """Compare pick frequency to current ABC class and flag mis-classified SKUs."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            LedgerEntry.product_id,
            func.count(LedgerEntry.id).label("picks"),
        )
        .where(
            LedgerEntry.warehouse_id == warehouse_id,
            LedgerEntry.action.in_([LedgerAction.PICK, LedgerAction.SHIPMENT]),
            LedgerEntry.product_id.isnot(None),
            LedgerEntry.created_at >= since,
        )
        .group_by(LedgerEntry.product_id)
        .order_by(func.count(LedgerEntry.id).desc())
    )
    rows = result.all()
    if not rows:
        return []

    total = len(rows)
    top_20pct = max(1, int(total * 0.20))
    top_50pct = max(1, int(total * 0.50))

    suggestions: list[AbcSuggestion] = []
    for idx, row in enumerate(rows):
        suggested = AbcClass.A if idx < top_20pct else (AbcClass.B if idx < top_50pct else AbcClass.C)

        prod_result = await db.execute(select(Product).where(Product.id == row.product_id))
        product = prod_result.scalar_one_or_none()
        if product is None:
            continue

        if product.abc_class != suggested:
            suggestions.append(
                AbcSuggestion(
                    product_id=row.product_id,
                    current_abc=product.abc_class,
                    suggested_abc=suggested,
                    move_count_30d=row.picks,
                    reason=f"ranked #{idx+1}/{total} by pick frequency",
                )
            )

    return suggestions


# ── KPI ───────────────────────────────────────────────────────────────────────

@dataclass
class WarehouseKPI:
    warehouse_id: uuid.UUID
    period_days: int
    total_receipts: int
    total_shipments: int
    total_units_in: int
    total_units_out: int
    # Throughput = units out / days
    throughput_units_per_day: float
    # Fulfillment: shipments with no shortfall (task completed) / total
    open_tasks_count: int
    # Stock counts
    total_sku_count: int
    total_units_on_hand: int
    open_pallets_count: int


async def get_kpi(
    db: AsyncSession,
    *,
    warehouse_id: uuid.UUID,
    days: int = 30,
) -> WarehouseKPI:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Receipts / shipments count and volume
    agg = await db.execute(
        select(
            LedgerEntry.action,
            func.count(LedgerEntry.id).label("cnt"),
            func.sum(func.abs(LedgerEntry.qty_delta)).label("units"),
        )
        .where(
            LedgerEntry.warehouse_id == warehouse_id,
            LedgerEntry.created_at >= since,
            LedgerEntry.action.in_([LedgerAction.RECEIPT, LedgerAction.SHIPMENT]),
        )
        .group_by(LedgerEntry.action)
    )
    receipt_cnt = shipment_cnt = units_in = units_out = 0
    for row in agg.all():
        if row.action == LedgerAction.RECEIPT:
            receipt_cnt = row.cnt
            units_in = int(row.units or 0)
        else:
            shipment_cnt = row.cnt
            units_out = int(row.units or 0)

    throughput = round(units_out / days, 2) if days else 0.0

    # Open tasks
    from app.models.task import Task, TaskStatus
    open_tasks = await db.scalar(
        select(func.count(Task.id)).where(
            Task.warehouse_id == warehouse_id,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
        )
    )

    # Stock summary
    sku_count = await db.scalar(
        select(func.count(func.distinct(StockItem.product_id))).where(
            StockItem.warehouse_id == warehouse_id
        )
    )
    total_on_hand = await db.scalar(
        select(func.sum(StockItem.qty)).where(StockItem.warehouse_id == warehouse_id)
    )
    open_pallets = await db.scalar(
        select(func.count(StockItem.id)).where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.pallet_open.is_(True),
        )
    )

    return WarehouseKPI(
        warehouse_id=warehouse_id,
        period_days=days,
        total_receipts=receipt_cnt,
        total_shipments=shipment_cnt,
        total_units_in=units_in,
        total_units_out=units_out,
        throughput_units_per_day=throughput,
        open_tasks_count=int(open_tasks or 0),
        total_sku_count=int(sku_count or 0),
        total_units_on_hand=int(total_on_hand or 0),
        open_pallets_count=int(open_pallets or 0),
    )


# ── Expiry alerts ─────────────────────────────────────────────────────────────

@dataclass
class ExpiryAlert:
    product_id: uuid.UUID
    batch_id: uuid.UUID
    lot_number: str | None
    expiry_date: str
    days_remaining: int
    total_qty: int
    locations: list[str]   # location codes


async def get_expiry_alerts(
    db: AsyncSession,
    *,
    warehouse_id: uuid.UUID,
    warn_days: int = 30,
) -> list[ExpiryAlert]:
    """Return batches expiring within warn_days, with their current stock."""
    today = date.today().isoformat()
    warn_limit = (date.today() + timedelta(days=warn_days)).isoformat()

    # Batches expiring soon and not blocked/expired already
    batches_result = await db.execute(
        select(Batch).where(
            Batch.expiry_date.isnot(None),
            Batch.expiry_date <= warn_limit,
            Batch.expiry_date >= today,
            Batch.status == BatchStatus.AVAILABLE,
        )
    )
    batches = batches_result.scalars().all()
    if not batches:
        return []

    alerts: list[ExpiryAlert] = []
    for batch in batches:
        # Stock for this batch in the warehouse
        stock_result = await db.execute(
            select(StockItem, Location)
            .join(Location, Location.id == StockItem.location_id)
            .where(
                StockItem.warehouse_id == warehouse_id,
                StockItem.batch_id == batch.id,
                StockItem.qty > 0,
            )
        )
        rows = stock_result.all()
        if not rows:
            continue

        total_qty = sum(s.qty for s, _ in rows)
        location_codes = [loc.code for _, loc in rows]

        from datetime import date as dt_date
        expiry = dt_date.fromisoformat(batch.expiry_date)
        days_remaining = (expiry - date.today()).days

        alerts.append(
            ExpiryAlert(
                product_id=batch.product_id,
                batch_id=batch.id,
                lot_number=batch.lot_number,
                expiry_date=batch.expiry_date,
                days_remaining=days_remaining,
                total_qty=total_qty,
                locations=location_codes,
            )
        )

    alerts.sort(key=lambda a: a.days_remaining)
    return alerts


# ── Throughput (daily in/out) ────────────────────────────────────────────────

_IN_ACTIONS = (LedgerAction.RECEIPT, LedgerAction.PUTAWAY, LedgerAction.RETURN_IN, LedgerAction.INVENTORY_PLUS)
_OUT_ACTIONS = (LedgerAction.PICK, LedgerAction.SHIPMENT, LedgerAction.WRITEOFF, LedgerAction.INVENTORY_MINUS)


async def get_throughput(
    db: AsyncSession, *, warehouse_id: uuid.UUID, days: int = 14
) -> list[dict]:
    """Daily inbound vs outbound unit volume from the ledger (TZ §10)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await db.execute(
        select(LedgerEntry.created_at, LedgerEntry.action, LedgerEntry.qty_delta)
        .where(LedgerEntry.warehouse_id == warehouse_id, LedgerEntry.created_at >= since)
    )).all()

    buckets: dict[str, dict[str, int]] = {}
    for created_at, action, qty in rows:
        day = created_at.date().isoformat()
        b = buckets.setdefault(day, {"in": 0, "out": 0})
        if action in _IN_ACTIONS and qty > 0:
            b["in"] += qty
        elif action in _OUT_ACTIONS:
            b["out"] += abs(qty)
    return [
        {"date": d, "inbound": v["in"], "outbound": v["out"]}
        for d, v in sorted(buckets.items())
    ]


# ── Возврат (returns) analytics — foydalanuvchi so'rovi ───────────────────────

async def get_returns_analytics(
    db: AsyncSession, *, warehouse_id: uuid.UUID, days: int = 30
) -> dict:
    """Qaytarishlar tahlili: mijozdan (RETURN_IN) + ta'minotchiga (RETURN_OUT),
    kunlik trend, top qaytarilgan mahsulotlar, qaytarish darajasi (return rate)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await db.execute(
        select(LedgerEntry.created_at, LedgerEntry.action, LedgerEntry.qty_delta,
               LedgerEntry.product_id, LedgerEntry.reason)
        .where(
            LedgerEntry.warehouse_id == warehouse_id,
            LedgerEntry.created_at >= since,
            LedgerEntry.action.in_((LedgerAction.RETURN_IN, LedgerAction.RETURN_OUT)),
        )
    )).all()

    daily: dict[str, dict[str, int]] = {}
    by_product: dict[uuid.UUID, int] = {}
    cust_units = supp_units = events = 0
    for created_at, action, qty, pid, _reason in rows:
        day = created_at.date().isoformat()
        b = daily.setdefault(day, {"customer": 0, "supplier": 0})
        events += 1
        if action == LedgerAction.RETURN_IN:
            u = abs(qty)
            cust_units += u
            b["customer"] += u
        else:
            u = abs(qty)
            supp_units += u
            b["supplier"] += u
        if pid is not None:
            by_product[pid] = by_product.get(pid, 0) + abs(qty)

    # Top qaytarilgan mahsulotlar (nom bilan)
    top: list[dict] = []
    if by_product:
        prods = (await db.execute(
            select(Product).where(Product.id.in_(list(by_product.keys())))
        )).scalars().all()
        name_by = {p.id: (p.name.get("uz") or p.name.get("ru") or p.sku) for p in prods}
        top = sorted(
            ({"product_name": name_by.get(pid, "—"), "qty": q} for pid, q in by_product.items()),
            key=lambda x: x["qty"], reverse=True,
        )[:10]

    # Qaytarish darajasi = mijoz qaytaruvi / umumiy chiqim (shu davrda)
    out_units = (await db.execute(
        select(func.coalesce(func.sum(func.abs(LedgerEntry.qty_delta)), 0))
        .where(
            LedgerEntry.warehouse_id == warehouse_id,
            LedgerEntry.created_at >= since,
            LedgerEntry.action.in_(_OUT_ACTIONS),
        )
    )).scalar_one()
    return_rate = round(cust_units / out_units * 100, 1) if out_units else 0.0

    return {
        "period_days": days,
        "customer_return_units": cust_units,
        "supplier_return_units": supp_units,
        "return_events": events,
        "return_rate_pct": return_rate,
        "daily": [
            {"date": d, "customer": v["customer"], "supplier": v["supplier"]}
            for d, v in sorted(daily.items())
        ],
        "top_products": top,
    }


# ── Zona/yacheyka summary — per-zona jamlanma (foydalanuvchi so'rovi) ──────────

async def get_zone_summary(
    db: AsyncSession, *, warehouse_id: uuid.UUID, days: int = 30
) -> list[dict]:
    """Har zona bo'yicha: yacheyka soni, band, umumiy qoldiq, o'rtacha to'lish,
    davr harakati (move_count) — zona darajasidagi analitika."""
    from app.models.warehouse import Zone

    zones = (await db.execute(
        select(Zone).where(Zone.warehouse_id == warehouse_id, Zone.is_active.is_(True))
    )).scalars().all()

    locs = (await db.execute(
        select(Location.id, Location.zone_id, Location.max_pallets)
        .join(Zone, Zone.id == Location.zone_id)
        .where(Zone.warehouse_id == warehouse_id, Location.is_active.is_(True))
    )).all()
    loc_zone = {lid: zid for lid, zid, _ in locs}
    loc_cap = {lid: (mp or 1) * 80 for lid, _, mp in locs}

    stock_rows = (await db.execute(
        select(StockItem.location_id, func.sum(StockItem.qty))
        .where(StockItem.warehouse_id == warehouse_id)
        .group_by(StockItem.location_id)
    )).all()
    qty_by_loc = {lid: int(q or 0) for lid, q in stock_rows}

    since = datetime.now(timezone.utc) - timedelta(days=days)
    move_rows = (await db.execute(
        select(LedgerEntry.from_location_id, LedgerEntry.to_location_id)
        .where(LedgerEntry.warehouse_id == warehouse_id, LedgerEntry.created_at >= since)
    )).all()
    moves_by_zone: dict[uuid.UUID, int] = {}
    for frm, to in move_rows:
        for lid in (frm, to):
            zid = loc_zone.get(lid)
            if zid is not None:
                moves_by_zone[zid] = moves_by_zone.get(zid, 0) + 1

    out: list[dict] = []
    for z in zones:
        z_locs = [lid for lid, zid, _ in locs if zid == z.id]
        occupied = sum(1 for lid in z_locs if qty_by_loc.get(lid, 0) > 0)
        total_qty = sum(qty_by_loc.get(lid, 0) for lid in z_locs)
        total_cap = sum(loc_cap.get(lid, 0) for lid in z_locs)
        fill = round(total_qty / total_cap * 100, 1) if total_cap else 0.0
        out.append({
            "zone_id": str(z.id),
            "name": z.name,
            "zone_type": z.zone_type.value,
            "location_count": len(z_locs),
            "occupied_count": occupied,
            "total_qty": total_qty,
            "fill_pct": fill,
            "move_count": moves_by_zone.get(z.id, 0),
        })
    out.sort(key=lambda x: x["move_count"], reverse=True)
    return out


# ── Location history (TZ §10 — "what left this cell, when") ───────────────────

async def get_location_history(
    db: AsyncSession, *, location_id: uuid.UUID, limit: int = 100
) -> list[dict]:
    rows = (await db.execute(
        select(LedgerEntry, Product)
        .outerjoin(Product, Product.id == LedgerEntry.product_id)
        .where(
            (LedgerEntry.from_location_id == location_id)
            | (LedgerEntry.to_location_id == location_id)
        )
        .order_by(LedgerEntry.created_at.desc())
        .limit(limit)
    )).all()
    out: list[dict] = []
    for entry, product in rows:
        direction = "in" if entry.to_location_id == location_id else "out"
        name = None
        if product is not None:
            name = product.name.get("uz") or product.name.get("ru")
        out.append({
            "at": entry.created_at,
            "action": entry.action.value,
            "direction": direction,
            "qty": abs(entry.qty_delta),
            "product_name": name,
            "marking_code": entry.marking_code,
            "reason": entry.reason,
        })
    return out


# ── Consolidated operations dashboard ─────────────────────────────────────────

async def get_dashboard(db: AsyncSession, *, warehouse_id: uuid.UUID) -> dict:
    """One call for the shift-lead monitor: today's flow + risk counters."""
    today = datetime.now(timezone.utc).date()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    flow = (await db.execute(
        select(LedgerEntry.action, LedgerEntry.qty_delta)
        .where(LedgerEntry.warehouse_id == warehouse_id, LedgerEntry.created_at >= start)
    )).all()
    today_in = sum(q for a, q in flow if a in _IN_ACTIONS and q > 0)
    today_out = sum(abs(q) for a, q in flow if a in _OUT_ACTIONS)

    open_pallets = (await db.execute(
        select(func.count(StockItem.id)).where(
            StockItem.warehouse_id == warehouse_id, StockItem.pallet_open.is_(True)
        )
    )).scalar_one()
    blocked_qty = (await db.execute(
        select(func.coalesce(func.sum(StockItem.qty), 0)).where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.status == StockStatus.BLOCKED,
        )
    )).scalar_one()

    return {
        "today_inbound": today_in,
        "today_outbound": today_out,
        "open_pallets": open_pallets,
        "blocked_qty": blocked_qty,
    }


# ── Occupancy (aggregated, for 2D/3D digital twin) ────────────────────────────

async def get_occupancy(db: AsyncSession, *, warehouse_id: uuid.UUID) -> list[dict]:
    """One aggregated row per location: coordinates + fill state + status — the
    data the (lazy) 3D digital twin renders by colour. Cheap: no per-unit data."""
    from app.models.warehouse import LocationStatus, Zone

    rows = (await db.execute(
        select(Location, Zone).join(Zone, Zone.id == Location.zone_id)
        .where(Zone.warehouse_id == warehouse_id, Location.is_active.is_(True))
    )).all()

    # Sum stock per location in one query.
    stock_rows = (await db.execute(
        select(StockItem.location_id, func.sum(StockItem.qty), func.max(StockItem.status))
        .where(StockItem.warehouse_id == warehouse_id)
        .group_by(StockItem.location_id)
    )).all()
    qty_by_loc = {lid: int(q or 0) for lid, q, _ in stock_rows}
    status_by_loc = {lid: s for lid, _, s in stock_rows}

    out: list[dict] = []
    for loc, zone in rows:
        qty = qty_by_loc.get(loc.id, 0)
        capacity = (loc.max_pallets or 1) * 80
        fill = min(1.0, qty / capacity) if capacity else 0.0
        if loc.status == LocationStatus.BLOCKED or status_by_loc.get(loc.id) == StockStatus.BLOCKED:
            state = "blocked"
        elif qty <= 0:
            state = "empty"
        elif fill >= 0.95:
            state = "full"
        else:
            state = "partial"
        out.append({
            "location_id": str(loc.id),
            "code": loc.code,
            "x": loc.x, "y": loc.y, "tier": loc.tier or 1,
            "zone_type": zone.zone_type.value,
            "state": state,
            "fill_ratio": round(fill, 2),
        })
    return out
