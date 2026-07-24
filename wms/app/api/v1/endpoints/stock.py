"""Stock query endpoints."""
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, ensure_warehouse_access, get_db, require_permission
from app.models.inventory import (
    Batch, Document, DocumentStatus, DocumentType, MarkingCode, Product,
    StockItem, StockStatus,
)
from app.models.ledger import LedgerAction, LedgerEntry
from app.models.reservation import PutawayReservation, ReservationStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.warehouse import Location, LocationStatus, Zone
from app.schemas.inventory import StockItemOut


def _tradeunit_key(gtin: str | None, product_id: uuid.UUID) -> str:
    """Savdo-birligi kaliti — GTIN-14 ning o'rta 12 raqami (qadoq darajasidan qat'i
    nazar GROUP/UNIT birlashadi). GTIN bo'lmasa product_id."""
    if gtin and len(gtin) == 14 and gtin.isdigit():
        return gtin[1:13]
    return str(product_id)


def _pname(n) -> str:
    if isinstance(n, dict):
        return n.get("uz") or n.get("ru") or n.get("en") or "—"
    return str(n) if n else "—"

router = APIRouter(prefix="/stock", tags=["stock"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/location/{location_id}/contents", dependencies=[require_permission("stock", "view")])
async def get_location_contents(location_id: uuid.UUID, user: ActiveUser, db: DB):
    """Everything inside one cell — for the map cell-detail panel (TZ §9).

    Returns the location header, its stock lines (product/batch/qty), the pending
    putaway reservations, and the marking-code **aggregation tree**
    (transport → box → unit) built from the locally-stored Asl Belgisi codes.
    """
    loc = await db.get(Location, location_id)
    if loc is None:
        return {"error": "not_found"}
    zone = await db.get(Zone, loc.zone_id)
    if zone is None:
        return {"error": "not_found"}
    await ensure_warehouse_access(db, user, zone.warehouse_id)

    # Stock lines at this location (enriched).
    stock_rows = (await db.execute(
        select(
            Product.name.label("product_name"), Product.category,
            Batch.lot_number, Batch.expiry_date,
            StockItem.qty, StockItem.qty_booked, StockItem.status, StockItem.pallet_open,
        )
        .select_from(StockItem)
        .join(Product, StockItem.product_id == Product.id)
        .outerjoin(Batch, StockItem.batch_id == Batch.id)
        .where(StockItem.location_id == location_id)
    )).all()
    stock = [{
        "product_name": r.product_name, "category": r.category,
        "batch": r.lot_number, "expiry_date": r.expiry_date,
        "qty": r.qty, "qty_booked": r.qty_booked, "available": r.qty - r.qty_booked,
        "status": r.status.value if r.status is not None else None,
        "pallet_open": r.pallet_open,
    } for r in stock_rows]

    # Marking codes physically stored here → aggregation tree by parent_code.
    codes = (await db.execute(
        select(MarkingCode).where(MarkingCode.location_id == location_id)
    )).scalars().all()
    by_code = {c.code: {
        "code": c.code, "package_type": c.package_type.value,
        "status": c.mc_status.value, "gtin": c.gtin,
        "expiry_date": c.expiry_date, "batch_number": c.batch_number,
        "production_date": c.production_date,
        "parent_code": c.parent_code, "children": [],
    } for c in codes}
    roots = []
    for c in codes:
        node = by_code[c.code]
        parent = by_code.get(c.parent_code) if c.parent_code else None
        if parent is not None:
            parent["children"].append(node)
        else:
            roots.append(node)

    # Pending reservations holding this slot.
    reservations = (await db.execute(
        select(PutawayReservation).where(
            PutawayReservation.location_id == location_id,
            PutawayReservation.status == ReservationStatus.PENDING,
        )
    )).scalars().all()
    res_out = [{
        "id": str(r.id), "code": r.code, "qty": r.qty, "unit_count": r.unit_count,
        "reason": r.reason, "score": r.score, "manual": r.manual,
        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
    } for r in reservations]

    return {
        "location": {
            "id": str(loc.id), "code": loc.code, "barcode": loc.barcode,
            "status": loc.status.value, "zone_name": zone.name,
            "zone_type": zone.zone_type.value,
            "row": loc.row, "rack": loc.rack, "tier": loc.tier, "position": loc.position,
        },
        "stock": stock,
        "code_tree": roots,
        "reservations": res_out,
    }


@router.post(
    "/location/{location_id}/fetch-code-tree",
    dependencies=[require_permission("stock", "view")],
)
async def fetch_location_code_tree(location_id: uuid.UUID, user: ActiveUser, db: DB):
    """Yacheykadagi transport (SSCC) kod(lar)i uchun Asl Belgisi'dan chuqur daraxtni
    (box → unit) talab bo'yicha tortadi va saqlaydi (Buxgalteriya Ocard `checkOwnerDeep`
    kabi). Keyin cell-contents daraxti to'liq ko'rinadi."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    loc = await db.get(Location, location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    zone = await db.get(Zone, loc.zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    await ensure_warehouse_access(db, user, zone.warehouse_id)

    # Yacheykadagi barcha kodlar. Kirish kodi unit/box/transport bo'lishi mumkin —
    # build_code_tree o'zi TEPAGA (root) qidiradi, shuning uchun har "ko'rinish-root"
    # (parenti shu yacheykada bo'lmagan kod) uchun bir marta ishga tushiramiz.
    loc_codes = (await db.execute(
        select(MarkingCode.code, MarkingCode.parent_code).where(
            MarkingCode.location_id == location_id
        )
    )).all()
    if not loc_codes:
        raise HTTPException(status_code=404, detail="Bu yacheykada kod yo'q")
    code_set = {c for c, _ in loc_codes}
    roots = [c for c, p in loc_codes if not p or p not in code_set]
    if not roots:  # barchasi bog'langan — istalgan bittasidan boshlaymiz (climb-up qiladi)
        roots = [loc_codes[0][0]]

    from app.core.connector_factory import get_aslbelgisi_client
    from app.services.marking_tree import build_code_tree
    try:
        client = await get_aslbelgisi_client(db, user.tenant_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Asl Belgisi ulanmagan: {exc}")

    totals = {"created": 0, "updated": 0, "api_calls": 0}
    for root in roots:
        try:
            res = await build_code_tree(
                db, tenant_id=user.tenant_id, root_code=root,
                location_id=location_id, aslbelgisi_client=client,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Asl Belgisi: {exc}")
        for k in totals:
            totals[k] += res.get(k, 0)
    return {"roots": len(roots), **totals}


@router.get("/", response_model=list[StockItemOut])
async def get_stock(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    product_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    limit: int = 200,
    offset: int = 0,
):
    # Tenant + data-scope isolation (was an open cross-tenant read before)
    await ensure_warehouse_access(db, user, warehouse_id)

    q = select(StockItem).where(StockItem.warehouse_id == warehouse_id)
    if product_id:
        q = q.where(StockItem.product_id == product_id)
    if location_id:
        q = q.where(StockItem.location_id == location_id)
    q = q.limit(min(limit, 1000)).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/detailed", dependencies=[require_permission("stock", "view")])
async def get_stock_detailed(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    product_id: uuid.UUID | None = None,
    batch_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    status: StockStatus | None = None,
    pallet_open: bool | None = None,
    limit: int = 200,
    offset: int = 0,
):
    """Rich joined stock view (TZ §7.5): one row per StockItem enriched with
    Location code/zone, Product name/category and Batch lot/expiry."""
    await ensure_warehouse_access(db, user, warehouse_id)

    q = (
        select(
            Location.code.label("location_code"),
            Zone.name.label("zone_name"),
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
    )
    if product_id:
        q = q.where(StockItem.product_id == product_id)
    if batch_id:
        q = q.where(StockItem.batch_id == batch_id)
    if location_id:
        q = q.where(StockItem.location_id == location_id)
    if status is not None:
        q = q.where(StockItem.status == status)
    if pallet_open is not None:
        q = q.where(StockItem.pallet_open == pallet_open)

    q = q.order_by(Location.code, Product.id).limit(min(limit, 1000)).offset(offset)
    result = await db.execute(q)

    rows = []
    for r in result.all():
        rows.append(
            {
                "location_code": r.location_code,
                "zone_name": r.zone_name,
                "product_name": r.product_name,
                "category": r.category,
                "batch": r.batch,
                "expiry_date": r.expiry_date,
                "qty": r.qty,
                "qty_booked": r.qty_booked,
                "available": r.qty - r.qty_booked,
                "status": r.status.value if r.status is not None else None,
                "pallet_open": r.pallet_open,
            }
        )
    return rows


@router.get("/summary", dependencies=[require_permission("stock", "view")])
async def get_stock_summary(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
):
    """Warehouse-level stock KPIs (TZ §7.5): SKU/qty totals, open-pallet count,
    blocked qty and near-empty (PARTIAL) location count. Tenant-guarded."""
    await ensure_warehouse_access(db, user, warehouse_id)

    agg = await db.execute(
        select(
            func.count(func.distinct(StockItem.product_id)).label("total_skus"),
            func.coalesce(func.sum(StockItem.qty), 0).label("total_qty"),
            func.coalesce(
                func.sum(StockItem.qty).filter(StockItem.status == StockStatus.BLOCKED),
                0,
            ).label("blocked_qty"),
            func.count(StockItem.id)
            .filter(StockItem.pallet_open.is_(True))
            .label("open_pallets"),
        ).where(StockItem.warehouse_id == warehouse_id)
    )
    row = agg.one()

    near_empty = await db.execute(
        select(func.count(Location.id))
        .join(Zone, Location.zone_id == Zone.id)
        .where(
            Zone.warehouse_id == warehouse_id,
            Location.status == LocationStatus.PARTIAL,
        )
    )

    return {
        "total_skus": row.total_skus,
        "total_qty": row.total_qty,
        "open_pallets": row.open_pallets,
        "blocked_qty": row.blocked_qty,
        "near_empty_locations": near_empty.scalar_one(),
    }


@router.get("/consolidated", dependencies=[require_permission("stock", "view")])
async def get_stock_consolidated(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    velocity_days: int = 30,
):
    """Savdo-birligi bo'yicha JAMLANGAN qoldiq (GROUP/UNIT yozuvlari GTIN negizi bo'yicha
    birlashadi). Har qatorда: jami/bron/erkin, yacheykalar, eng yaqin muddat, ochiq pallet,
    bloklangan, harakat tezligi (velocity) va «necha kunga yetadi» (days-of-supply)."""
    await ensure_warehouse_access(db, user, warehouse_id)
    today = date.today()

    rows = (await db.execute(
        select(
            StockItem.product_id, Product.name, Product.gtin, Product.category,
            Product.units_per_box, Product.abc_class,
            Location.code.label("loc"), Batch.expiry_date, Batch.lot_number,
            StockItem.qty, StockItem.qty_booked, StockItem.status, StockItem.pallet_open,
        )
        .select_from(StockItem)
        .join(Product, StockItem.product_id == Product.id)
        .join(Location, StockItem.location_id == Location.id)
        .outerjoin(Batch, StockItem.batch_id == Batch.id)
        .where(StockItem.warehouse_id == warehouse_id)
    )).all()

    # Velocity — oxirgi N kun SHIPMENT (chiqim) miqdori, mahsulot bo'yicha.
    since = datetime.now(timezone.utc) - timedelta(days=velocity_days)
    vel_rows = (await db.execute(
        select(LedgerEntry.product_id, func.coalesce(func.sum(func.abs(LedgerEntry.qty_delta)), 0))
        .where(
            LedgerEntry.warehouse_id == warehouse_id,
            LedgerEntry.action == LedgerAction.SHIPMENT,
            LedgerEntry.created_at >= since,
        )
        .group_by(LedgerEntry.product_id)
    )).all()
    vel_by_pid = {pid: int(v or 0) for pid, v in vel_rows}

    groups: dict[str, dict] = {}
    for r in rows:
        key = _tradeunit_key(r.gtin, r.product_id)
        g = groups.get(key)
        if g is None:
            g = groups[key] = {
                "key": key, "product_ids": set(), "names": [], "gtin": r.gtin,
                "category": r.category, "units_per_box": None, "abc_class": None,
                "qty": 0, "booked": 0, "blocked_qty": 0, "locations": set(),
                "open_pallet": False, "batches": set(), "nearest_expiry": None,
                "expired_qty": 0, "sold": 0,
            }
        g["product_ids"].add(r.product_id)
        g["names"].append(_pname(r.name))
        if r.gtin and (not g["gtin"] or len(str(r.gtin)) < len(str(g["gtin"]))):
            g["gtin"] = r.gtin
        if r.units_per_box and (g["units_per_box"] or 0) < r.units_per_box:
            g["units_per_box"] = r.units_per_box
        if r.abc_class is not None and g["abc_class"] is None:
            g["abc_class"] = r.abc_class.value if hasattr(r.abc_class, "value") else r.abc_class
        g["qty"] += r.qty or 0
        g["booked"] += r.qty_booked or 0
        if r.status == StockStatus.BLOCKED:
            g["blocked_qty"] += r.qty or 0
        if r.qty and r.qty > 0:
            g["locations"].add(r.loc)
        if r.pallet_open:
            g["open_pallet"] = True
        if r.lot_number:
            g["batches"].add(r.lot_number)
        if r.expiry_date:
            ed = r.expiry_date if isinstance(r.expiry_date, date) else None
            if ed:
                if g["nearest_expiry"] is None or ed < g["nearest_expiry"]:
                    g["nearest_expiry"] = ed
                if ed < today:
                    g["expired_qty"] += r.qty or 0

    out = []
    for g in groups.values():
        for pid in g["product_ids"]:
            g["sold"] += vel_by_pid.get(pid, 0)
        avail = g["qty"] - g["booked"]
        # Ko'rsatiladigan nom — "(GROUP)" bo'lmagani afzal, aks holda eng qisqasi.
        clean = [n for n in g["names"] if "(GROUP)" not in n and "(BOX)" not in n]
        name = (clean or sorted(g["names"], key=len))[0] if g["names"] else "—"
        per_day = g["sold"] / velocity_days if velocity_days else 0
        dos = round(avail / per_day, 1) if per_day > 0 else None
        ne = g["nearest_expiry"]
        out.append({
            "key": g["key"],
            "product_ids": [str(p) for p in g["product_ids"]],
            "name": name,
            "gtin": g["gtin"],
            "category": g["category"],
            "units_per_box": g["units_per_box"],
            "abc_class": g["abc_class"],
            "qty": g["qty"], "booked": g["booked"], "available": avail,
            "blocked_qty": g["blocked_qty"],
            "locations": sorted(g["locations"]),
            "location_count": len(g["locations"]),
            "open_pallet": g["open_pallet"],
            "batch_count": len(g["batches"]),
            "nearest_expiry": ne.isoformat() if ne else None,
            "expiry_days": (ne - today).days if ne else None,
            "expired_qty": g["expired_qty"],
            "sold_30d": g["sold"],
            "days_of_supply": dos,
        })
    out.sort(key=lambda x: x["name"].lower())
    return out


@router.post("/release-bookings", dependencies=[require_permission("stock", "view")])
async def release_bookings(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    product_id: uuid.UUID | None = None,
):
    """Tasdiqlanmagan (IN_PROGRESS) chiqim/terish hujjatlari band qilib qo'ygan qoldiqni
    BO'SHATADI — ochiq pick vazifalari yig'ilib, ERKIN=0 bo'lib qolganда kerak. Tegishli
    SHIPMENT hujjatlar + PICK vazifalar bekor qilinadi va qty_booked qaytariladi."""
    await ensure_warehouse_access(db, user, warehouse_id)

    # IN_PROGRESS chiqim hujjatlarini bekor qilamiz + ularning PICK vazifalarini.
    docs = (await db.execute(
        select(Document).where(
            Document.tenant_id == user.tenant_id,
            Document.warehouse_id == warehouse_id,
            Document.doc_type == DocumentType.SHIPMENT,
            Document.status == DocumentStatus.IN_PROGRESS,
        )
    )).scalars().all()
    doc_ids = [d.id for d in docs]
    for d in docs:
        d.status = DocumentStatus.CANCELLED
    if doc_ids:
        tasks = (await db.execute(
            select(Task).where(
                Task.document_id.in_(doc_ids),
                Task.task_type == TaskType.PICK,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
            )
        )).scalars().all()
        for t in tasks:
            t.status = TaskStatus.CANCELLED

    # Band qoldiqni qaytaramiz (rezervlar hujjat bilan bekor bo'ldi).
    q = select(StockItem).where(
        StockItem.warehouse_id == warehouse_id, StockItem.qty_booked > 0
    )
    if product_id is not None:
        q = q.where(StockItem.product_id == product_id)
    items = (await db.execute(q)).scalars().all()
    freed = sum(i.qty_booked for i in items)
    for i in items:
        i.qty_booked = 0
    await db.commit()
    return {"cancelled_documents": len(doc_ids), "freed_qty": int(freed), "stock_items": len(items)}
