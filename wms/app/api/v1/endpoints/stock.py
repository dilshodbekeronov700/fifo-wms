"""Stock query endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, ensure_warehouse_access, get_db, require_permission
from app.models.inventory import Batch, MarkingCode, Product, StockItem, StockStatus
from app.models.reservation import PutawayReservation, ReservationStatus
from app.models.warehouse import Location, LocationStatus, Zone
from app.schemas.inventory import StockItemOut

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
