"""Warehouse, Zone, Location endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, get_db, require_permission
from datetime import datetime, timezone

from app.models.sensor import Sensor
from app.models.warehouse import Location, Warehouse, Zone
from app.schemas.warehouse import (
    BulkLocationCreate, LocationCreate, LocationOut, LocationUpdate, RackGenerateRequest,
    WarehouseCreate, WarehouseOut,
    ZoneCreate, ZoneOut, ZoneUpdate, SetRackCellsRequest,
)

router = APIRouter(prefix="/warehouses", tags=["warehouses"])
DB = Annotated[AsyncSession, Depends(get_db)]

# ─── Warehouse ──────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=WarehouseOut,
    status_code=201,
    dependencies=[require_permission("warehouse", "create")],
)
async def create_warehouse(body: WarehouseCreate, user: ActiveUser, db: DB):
    wh = Warehouse(tenant_id=user.tenant_id, **body.model_dump())
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh


@router.get("/", response_model=list[WarehouseOut])
async def list_warehouses(user: ActiveUser, db: DB):
    q = select(Warehouse).where(Warehouse.is_active.is_(True))
    if not user.is_superadmin:
        q = q.where(Warehouse.tenant_id == user.tenant_id)
    result = await db.execute(q.order_by(Warehouse.name))
    return result.scalars().all()


@router.get("/{warehouse_id}", response_model=WarehouseOut)
async def get_warehouse(warehouse_id: uuid.UUID, user: ActiveUser, db: DB):
    wh = await _get_wh(warehouse_id, user, db)
    return wh


from pydantic import BaseModel as _BM  # noqa: E402


class WarehousePatch(_BM):
    name: str | None = None
    smartup_warehouse_code: str | None = None


@router.patch(
    "/{warehouse_id}",
    response_model=WarehouseOut,
    dependencies=[require_permission("warehouse", "update")],
)
async def update_warehouse(warehouse_id: uuid.UUID, body: WarehousePatch, user: ActiveUser, db: DB):
    """Sklad sozlamalari — ayniqsa Smartup kodi (sklad↔ERP mapping)."""
    wh = await _get_wh(warehouse_id, user, db)
    if body.name is not None:
        wh.name = body.name
    if body.smartup_warehouse_code is not None:
        wh.smartup_warehouse_code = body.smartup_warehouse_code or None
    await db.commit()
    await db.refresh(wh)
    return wh


@router.delete(
    "/{warehouse_id}",
    status_code=204,
    dependencies=[require_permission("warehouse", "delete")],
)
async def delete_warehouse(warehouse_id: uuid.UUID, user: ActiveUser, db: DB):
    """Skladni o'chirish. Ledger/hujjat/task yozuvlari sklad'ga FK bilan bog'langani
    uchun qatorni jismonan o'chirib bo'lmaydi — sklad DEAKTIVATSIYA qilinadi
    (ro'yxat `is_active` bo'yicha filtrlaydi, shuning uchun ko'rinmay qoladi).
    Ichida qoldiq (qty>0) bo'lsa — bloklanadi (tasodifan yashirmaslik uchun)."""
    from app.models.inventory import StockItem
    wh = await _get_wh(warehouse_id, user, db)
    has_stock = (await db.execute(
        select(StockItem.id).where(
            StockItem.warehouse_id == warehouse_id, StockItem.qty > 0
        ).limit(1)
    )).first()
    if has_stock:
        raise HTTPException(
            status_code=409,
            detail="Skladda mahsulot (qoldiq) bor — avval qoldiqni bo'shating yoki ko'chiring.",
        )
    wh.is_active = False
    await db.commit()


# ─── Zone ───────────────────────────────────────────────────────────────────

@router.post(
    "/{warehouse_id}/zones",
    response_model=ZoneOut,
    status_code=201,
    dependencies=[require_permission("zone", "create")],
)
async def create_zone(warehouse_id: uuid.UUID, body: ZoneCreate, user: ActiveUser, db: DB):
    await _get_wh(warehouse_id, user, db)
    zone = Zone(warehouse_id=warehouse_id, **body.model_dump())
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


@router.patch(
    "/{warehouse_id}/zones/{zone_id}",
    response_model=ZoneOut,
    dependencies=[require_permission("zone", "update")],
)
async def update_zone(
    warehouse_id: uuid.UUID, zone_id: uuid.UUID, body: ZoneUpdate, user: ActiveUser, db: DB,
):
    """Zona (stellaj) nomi / turi / koordinatasini tahrirlaydi — xarita muharriri."""
    await _get_wh(warehouse_id, user, db)
    zone = (await db.execute(
        select(Zone).where(Zone.id == zone_id, Zone.warehouse_id == warehouse_id)
    )).scalar_one_or_none()
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(zone, field, value)
    await db.commit()
    await db.refresh(zone)
    return zone


@router.delete(
    "/{warehouse_id}/zones/{zone_id}",
    status_code=204,
    dependencies=[require_permission("zone", "delete")],
)
async def delete_zone(warehouse_id: uuid.UUID, zone_id: uuid.UUID, user: ActiveUser, db: DB):
    """Zonani o'chirish. Ichidagi bo'sh yacheykalar ham o'chadi; mahsulot bo'lsa bloklanadi."""
    from app.models.inventory import StockItem
    await _get_wh(warehouse_id, user, db)
    zone = (await db.execute(
        select(Zone).where(Zone.id == zone_id, Zone.warehouse_id == warehouse_id)
    )).scalar_one_or_none()
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    loc_ids = (await db.execute(
        select(Location.id).where(Location.zone_id == zone_id)
    )).scalars().all()
    if loc_ids:
        has_stock = (await db.execute(
            select(StockItem.id).where(
                StockItem.location_id.in_(loc_ids), StockItem.qty > 0
            ).limit(1)
        )).first()
        if has_stock:
            raise HTTPException(
                status_code=409,
                detail="Zonada mahsulot bor — avval yacheykalarni bo'shating.",
            )
        for lid in loc_ids:
            loc = await db.get(Location, lid)
            if loc is not None:
                await db.delete(loc)
    await db.delete(zone)
    await db.commit()


@router.get("/{warehouse_id}/zones", response_model=list[ZoneOut])
async def list_zones(warehouse_id: uuid.UUID, user: ActiveUser, db: DB):
    await _get_wh(warehouse_id, user, db)
    result = await db.execute(
        select(Zone).where(Zone.warehouse_id == warehouse_id, Zone.is_active.is_(True))
    )
    return result.scalars().all()


# ─── Location ───────────────────────────────────────────────────────────────

@router.post(
    "/{warehouse_id}/zones/{zone_id}/locations",
    response_model=LocationOut,
    status_code=201,
    dependencies=[require_permission("location", "create")],
)
async def create_location(
    warehouse_id: uuid.UUID, zone_id: uuid.UUID, body: LocationCreate, user: ActiveUser, db: DB
):
    await _get_wh(warehouse_id, user, db)
    zone_result = await db.execute(
        select(Zone).where(Zone.id == zone_id, Zone.warehouse_id == warehouse_id)
    )
    if zone_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    loc = Location(zone_id=zone_id, **body.model_dump())
    db.add(loc)
    await db.commit()
    await db.refresh(loc)
    return loc


@router.get("/{warehouse_id}/zones/{zone_id}/locations", response_model=list[LocationOut])
async def list_locations(
    warehouse_id: uuid.UUID, zone_id: uuid.UUID, user: ActiveUser, db: DB
):
    await _get_wh(warehouse_id, user, db)
    result = await db.execute(
        select(Location).where(Location.zone_id == zone_id, Location.is_active.is_(True))
    )
    return result.scalars().all()


@router.get("/{warehouse_id}/locations", response_model=list[LocationOut])
async def list_all_locations(warehouse_id: uuid.UUID, user: ActiveUser, db: DB):
    """Skladdagi BARCHA yacheykalar (xarita/Digital Twin uchun)."""
    await _get_wh(warehouse_id, user, db)
    result = await db.execute(
        select(Location)
        .join(Zone, Location.zone_id == Zone.id)
        .where(Zone.warehouse_id == warehouse_id, Location.is_active.is_(True))
    )
    return result.scalars().all()


# ─── Xarita muharriri (Faza 1) ────────────────────────────────────────────────

async def _loc_in_wh(db: AsyncSession, warehouse_id: uuid.UUID, location_id: uuid.UUID) -> Location:
    res = await db.execute(
        select(Location).join(Zone, Location.zone_id == Zone.id)
        .where(Location.id == location_id, Zone.warehouse_id == warehouse_id)
    )
    loc = res.scalar_one_or_none()
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return loc


@router.patch(
    "/{warehouse_id}/locations/{location_id}",
    response_model=LocationOut,
    dependencies=[require_permission("location", "update")],
)
async def update_location_by_id(
    warehouse_id: uuid.UUID, location_id: uuid.UUID,
    body: LocationUpdate, user: ActiveUser, db: DB,
):
    """Bitta yacheykani tahrirlash (kod, etaj, pallet, o'lcham, og'irlik, joylashuv...)."""
    await _get_wh(warehouse_id, user, db)
    loc = await _loc_in_wh(db, warehouse_id, location_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(loc, field, value)
    await db.commit()
    await db.refresh(loc)
    return loc


@router.delete(
    "/{warehouse_id}/locations/{location_id}",
    status_code=204,
    dependencies=[require_permission("location", "delete")],
)
async def delete_location_by_id(
    warehouse_id: uuid.UUID, location_id: uuid.UUID, user: ActiveUser, db: DB,
):
    """Yacheykani o'chirish (xaritadan)."""
    await _get_wh(warehouse_id, user, db)
    loc = await _loc_in_wh(db, warehouse_id, location_id)
    await db.delete(loc)
    await db.commit()


@router.post(
    "/{warehouse_id}/locations/bulk",
    response_model=list[LocationOut],
    status_code=201,
    dependencies=[require_permission("location", "create")],
)
async def bulk_create_locations(
    warehouse_id: uuid.UUID, body: BulkLocationCreate, user: ActiveUser, db: DB,
):
    """Ko'plab yacheyka yaratish (bitta zonaga)."""
    await _get_wh(warehouse_id, user, db)
    zone = (await db.execute(
        select(Zone).where(Zone.id == body.zone_id, Zone.warehouse_id == warehouse_id)
    )).scalar_one_or_none()
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    created = [Location(zone_id=body.zone_id, **loc.model_dump()) for loc in body.locations]
    db.add_all(created)
    await db.commit()
    for loc in created:
        await db.refresh(loc)
    return created


@router.post(
    "/{warehouse_id}/rack-generator",
    response_model=list[LocationOut],
    status_code=201,
    dependencies=[require_permission("location", "create")],
)
async def generate_rack(
    warehouse_id: uuid.UUID, body: RackGenerateRequest, user: ActiveUser, db: DB,
):
    """Rack/blok generatsiyasi: cols × tiers × positions yacheyka avtomatik yaratiladi.
    Kod format: {prefix}-{ustun:02d}  (tier/position barcode'da farqlanadi)."""
    from app.models.warehouse import LocationType, LocationStatus

    await _get_wh(warehouse_id, user, db)
    zone = (await db.execute(
        select(Zone).where(Zone.id == body.zone_id, Zone.warehouse_id == warehouse_id)
    )).scalar_one_or_none()
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")

    prefix = body.code_prefix or body.rack_group
    # Mavjud barcode'larni oldindan olamiz — to'qnashuvni oldini olish (unique constraint).
    taken = set((await db.execute(select(Location.barcode).where(Location.barcode.isnot(None)))).scalars().all())
    created: list[Location] = []
    for c in range(body.cols):
        cx = body.x + c * body.cell_w
        rack_code = f"{prefix}-{c + 1:02d}"           # stellaj: A-01
        n = 0
        for t in range(1, body.tiers + 1):
            for p in range(1, body.positions + 1):
                n += 1
                cell_code = f"{rack_code}-{n}"        # yacheyka: A-01-1 (flat raqam)
                if cell_code in taken:
                    continue                           # bu kod allaqachon bor — o'tkazib yuboramiz
                taken.add(cell_code)
                created.append(Location(
                    zone_id=body.zone_id,
                    code=cell_code,
                    barcode=cell_code,                # barcode = kod = nom (skanlanadi)
                    location_type=LocationType.PALLET,
                    status=LocationStatus.EMPTY,
                    row=body.row,
                    rack=c + 1,
                    tier=t,
                    position=p,                        # joy (etaj ichida)
                    x=cx,
                    y=body.y,
                    rack_group=rack_code,              # GURUHLASH: stellaj = A-01 (bitta quti)
                    max_pallets=1,
                    max_weight_kg=body.max_weight_kg,
                    length_mm=body.length_mm,
                    width_mm=body.width_mm,
                    height_mm=body.height_mm,
                ))
    db.add_all(created)
    await db.commit()
    for loc in created:
        await db.refresh(loc)
    return created


@router.post(
    "/{warehouse_id}/set-rack-cells",
    response_model=list[LocationOut],
    dependencies=[require_permission("location", "update")],
)
async def set_rack_cells(
    warehouse_id: uuid.UUID, body: SetRackCellsRequest, user: ActiveUser, db: DB,
):
    """Stellaj yacheykalarini IDEMPOTENT o'rnatadi: {base}-1 … {base}-N.
    Mavjudini tekshiradi (faqat yetishmaganini yaratadi), ortiqcha BO'SH larni
    o'chiradi. Barcode unikalligini hurmat qiladi — to'qnashuvda o'tkazib yuboradi.
    Takror chaqirilsa ham xavfsiz (yarim holat bo'lmaydi — bitta tranzaksiya)."""
    from app.models.warehouse import LocationType, LocationStatus
    await _get_wh(warehouse_id, user, db)
    zone = (await db.execute(
        select(Zone).where(Zone.id == body.zone_id, Zone.warehouse_id == warehouse_id)
    )).scalar_one_or_none()
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    base = body.base_code.strip()
    if not base:
        raise HTTPException(status_code=422, detail="base_code required")
    tiers = max(1, body.tiers)
    positions = max(1, body.positions)
    # Flat raqam {base}-{n}, lekin grid joylashuvi uchun tier/position (etaj×joy).
    # n reading-order: 1 2 / 3 4 / 5 6  (etaj t, joy p)
    target_meta: dict[str, tuple[int, int]] = {}
    n = 0
    for t in range(1, tiers + 1):
        for p in range(1, positions + 1):
            n += 1
            target_meta[f"{base}-{n}"] = (t, p)
    target = list(target_meta.keys())
    target_set = set(target)

    existing = (await db.execute(
        select(Location).join(Zone, Zone.id == Location.zone_id).where(
            Zone.warehouse_id == warehouse_id,
            or_(Location.code == base, Location.code.like(f"{base}-%")),
        )
    )).scalars().all()
    by_code = {l.code: l for l in existing}

    for tc in target:
        if tc in by_code:
            continue
        clash = (await db.execute(
            select(Location).where(Location.barcode == tc)
        )).scalar_one_or_none()
        if clash is not None:
            continue  # barcode band — o'tkazib yuboramiz
        t, p = target_meta[tc]
        db.add(Location(
            zone_id=body.zone_id, code=tc, barcode=tc,
            location_type=LocationType.PALLET, status=LocationStatus.EMPTY,
            tier=t, position=p, max_pallets=1, rack_group=base,
        ))

    for l in existing:
        if l.code not in target_set and l.status == LocationStatus.EMPTY:
            await db.delete(l)

    await db.commit()
    rows = (await db.execute(
        select(Location).join(Zone, Zone.id == Location.zone_id).where(
            Zone.warehouse_id == warehouse_id, Location.code.like(f"{base}-%"),
        ).order_by(Location.code)
    )).scalars().all()
    return rows


@router.post(
    "/{warehouse_id}/auto-arrange-racks",
    dependencies=[require_permission("location", "update")],
)
async def auto_arrange_racks(warehouse_id: uuid.UUID, user: ActiveUser, db: DB, cols: int = 0):
    """Stellajlarni tartibli grid'ga joylaydi (rack_group bo'yicha, nomi bilan saralab)
    va har stellajning x/y koordinatasini barcha yacheykalariga yozadi.
    2D va 3D ikkalasi shu x/y'dan o'qigani uchun — bir xil ko'rinadi."""
    await _get_wh(warehouse_id, user, db)
    locs = (await db.execute(
        select(Location).join(Zone, Zone.id == Location.zone_id)
        .where(Zone.warehouse_id == warehouse_id)
    )).scalars().all()
    # rack_group bo'yicha guruhlash
    racks: dict[str, list[Location]] = {}
    for l in locs:
        rg = l.rack_group or (l.code or "").rsplit("-", 1)[0] or l.code or "?"
        racks.setdefault(rg, []).append(l)
    names = sorted(racks.keys(), key=lambda s: [int(t) if t.isdigit() else t for t in __import__("re").split(r"(\d+)", s)])
    import math
    n = len(names)
    ncols = cols if cols and cols > 0 else max(1, math.ceil(math.sqrt(n)))
    GX, GY = 5.0, 4.0  # grid oralig'i (m)
    for i, name in enumerate(names):
        rx = (i % ncols) * GX
        ry = (i // ncols) * GY
        for l in racks[name]:
            l.x = rx
            l.y = ry
    await db.commit()
    return {"detail": "arranged", "racks": n, "cols": ncols}


# ─── Climate ────────────────────────────────────────────────────────────────

@router.get("/{warehouse_id}/climate")
async def warehouse_climate(warehouse_id: uuid.UUID, user: ActiveUser, db: DB):
    """Shu skladdagi barcha sensorlarning joriy harorat/namlik holati."""
    await _get_wh(warehouse_id, user, db)
    sensors = (await db.execute(
        select(Sensor).where(
            Sensor.warehouse_id == warehouse_id,
            Sensor.is_active.is_(True),
        )
    )).scalars().all()

    now = datetime.now(timezone.utc)
    result = []
    for s in sensors:
        if s.last_seen is None:
            status = "no_data"
        else:
            seconds_ago = (now - s.last_seen).total_seconds()
            if seconds_ago > 300:
                status = "offline"
            elif (
                (s.temp_min is not None and s.last_temp is not None and s.last_temp < s.temp_min) or
                (s.temp_max is not None and s.last_temp is not None and s.last_temp > s.temp_max) or
                (s.hum_max is not None and s.last_hum is not None and s.last_hum > s.hum_max)
            ):
                status = "alert"
            else:
                status = "online"
        result.append({
            "id": str(s.id),
            "name": s.name,
            "zone_id": str(s.zone_id) if s.zone_id else None,
            "last_temp": s.last_temp,
            "last_hum": s.last_hum,
            "last_seen": s.last_seen.isoformat() if s.last_seen else None,
            "status": status,
            "temp_min": s.temp_min,
            "temp_max": s.temp_max,
        })

    temps = [s["last_temp"] for s in result if s["last_temp"] is not None]
    return {
        "sensors": result,
        "avg_temp": round(sum(temps) / len(temps), 1) if temps else None,
        "alert_count": sum(1 for s in result if s["status"] == "alert"),
        "offline_count": sum(1 for s in result if s["status"] == "offline"),
    }


# ─── Helper ─────────────────────────────────────────────────────────────────

async def _get_wh(warehouse_id: uuid.UUID, user: ActiveUser, db: AsyncSession) -> Warehouse:
    q = select(Warehouse).where(Warehouse.id == warehouse_id)
    if not user.is_superadmin:
        q = q.where(Warehouse.tenant_id == user.tenant_id)
    result = await db.execute(q)
    wh = result.scalar_one_or_none()
    if wh is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return wh
