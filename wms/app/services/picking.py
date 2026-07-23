"""
Picking service.

FEFO/FIFO allotment + route optimisation + partial pallet logic.

Allotment strategy (TZ §12):
  1. FEFO  — earliest expiry_date first
  2. FIFO  — earliest batch.created_at if expiry tied
  3. Open pallet first — avoid creating new open pallets unnecessarily
  4. Full boxes only (GROUP level) — unit-level splitting not done in WMS

Partial pallet rule (TZ §7.6 step 5):
  - If a pallet has e.g. 80 boxes and we need 68, we take full boxes.
  - The leftover boxes stay on the pallet; pallet becomes "open".
  - One open pallet per SKU at a time — new picks from same pallet until empty.
  - If the pallet is fully consumed → pallet_open = False.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select, asc, nulls_last
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import (
    Batch, BatchStatus, MarkingCode, PackageType, StockItem, StockStatus,
)
from app.models.ledger import LedgerAction
from app.models.warehouse import Location, Zone, ZoneType
from app.services import ledger as ledger_svc


@dataclass
class AllotmentLine:
    """One line of the pick plan: which stock to take, how much."""
    stock_item: StockItem
    location: Location
    zone: Zone
    take_qty: int                        # in boxes (GROUP)
    marking_codes: list[str] = field(default_factory=list)
    is_partial_pallet: bool = False      # pallet will become "open" after this pick
    batch: Batch | None = None           # FEFO/FIFO manbasi — partiya/muddat/i.ch. sana


@dataclass
class PickPlan:
    order_line_product_id: uuid.UUID
    order_line_id: str
    requested_boxes: int
    allotments: list[AllotmentLine]
    shortfall: int          # boxes we couldn't allocate (0 = fully filled)


async def build_pick_plan(
    db: AsyncSession,
    *,
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    order_line_id: str,
    requested_boxes: int,
    stock_product_ids: list[uuid.UUID] | None = None,
) -> PickPlan:
    """
    Build a FEFO/FIFO pick plan for one order line.
    Returns allotments + remaining shortfall.

    `stock_product_ids` — qoldiqni qidirishda hisobga olinadigan mahsulot yozuvlari
    (bir savdo-birligining turli qadoq/GTIN yozuvlari — GROUP/UNIT). Berilmasa
    faqat `product_id` ishlatiladi.
    """
    ids = stock_product_ids or [product_id]
    # 1. Load available stock sorted by FEFO then FIFO
    stock_rows = await _load_available_stock(db, warehouse_id=warehouse_id, product_ids=ids)

    remaining = requested_boxes
    allotments: list[AllotmentLine] = []

    for stock, batch, location, zone in stock_rows:
        if remaining <= 0:
            break

        available_boxes = stock.qty - stock.qty_booked

        # Open pallets are preferred (already "broken") — if any exist, pick from them first.
        # The query already sorts open pallets first; just take what we need.
        take = min(available_boxes, remaining)
        if take <= 0:
            continue

        is_partial = (take < available_boxes) or stock.pallet_open

        # Collect marking codes for the boxes being picked (GROUP level).
        # Qoldiq qaysi mahsulot yozuvida bo'lsa (GROUP/UNIT) — o'shaniki bo'yicha.
        codes = await _get_group_codes(db, location_id=stock.location_id, product_id=stock.product_id, limit=take)

        allotments.append(
            AllotmentLine(
                stock_item=stock,
                location=location,
                zone=zone,
                take_qty=take,
                marking_codes=codes,
                is_partial_pallet=is_partial,
                batch=batch,
            )
        )
        remaining -= take

    return PickPlan(
        order_line_product_id=product_id,
        order_line_id=order_line_id,
        requested_boxes=requested_boxes,
        allotments=allotments,
        shortfall=max(0, remaining),
    )


async def execute_pick_plan(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    plan: PickPlan,
) -> list[str]:
    """
    Execute a confirmed pick plan: book stock, write ledger, handle open pallets.
    Returns list of all marking codes picked.
    """
    all_codes: list[str] = []

    for al in plan.allotments:
        # Konkurent piklarni serializatsiya qilamiz: stok qatorini QULFLAB qayta
        # o'qiymiz (SELECT ... FOR UPDATE). Reja tuzilgach boshqa order shu joydan
        # booking qilgan bo'lishi mumkin — shuning uchun mavjud miqdorni QAYTA
        # tekshiramiz va ortiqcha booking'ning oldini olamiz (qty_booked <= qty).
        locked = (await db.execute(
            select(StockItem).where(StockItem.id == al.stock_item.id).with_for_update()
        )).scalar_one_or_none()
        if locked is None:
            continue
        stock = al.stock_item = locked

        available = stock.qty - stock.qty_booked
        take = min(al.take_qty, max(0, available))
        if take <= 0:
            # Bu joy reja tuzilgandan keyin band bo'lib qoldi — o'tkazib yuboramiz.
            al.take_qty = 0
            continue
        al.take_qty = take  # downstream (qisman pallet, disaggregation) mos qolishi uchun

        # Book the quantity
        stock.qty_booked = stock.qty_booked + take

        # Mark pallet open if partial pick
        if al.is_partial_pallet and stock.qty - stock.qty_booked > 0:
            stock.pallet_open = True
        elif stock.qty - stock.qty_booked <= 0:
            stock.pallet_open = False

        # Ledger: BOOK (reservation)
        await ledger_svc.record(
            db,
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            action=LedgerAction.BOOK,
            qty_delta=-al.take_qty,
            product_id=stock.product_id,   # qoldiq qaysi mahsulot yozuvida bo'lsa — o'sha
            batch_id=stock.batch_id,
            from_location_id=stock.location_id,
            user_id=user_id,
            document_id=document_id,
            reason=f"order_line:{plan.order_line_id}",
        )

        # Booking clamp bo'lgan bo'lsa — kod ro'yxatini ham take'ga qisqartiramiz.
        al.marking_codes = al.marking_codes[:take]
        all_codes.extend(al.marking_codes)

    return all_codes


async def confirm_shipment(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    product_id: uuid.UUID,
    location_id: uuid.UUID,
    qty: int,
    marking_codes: list[str],
    batch_id: uuid.UUID | None = None,
) -> None:
    """Convert BOOK → SHIPMENT (actual physical departure)."""
    # Deduct from stock cache
    result = await db.execute(
        select(StockItem).where(
            StockItem.location_id == location_id,
            StockItem.product_id == product_id,
            StockItem.batch_id == batch_id,
        )
    )
    stock = result.scalar_one_or_none()
    if stock:
        stock.qty = max(0, stock.qty - qty)
        stock.qty_booked = max(0, stock.qty_booked - qty)

    # Ledger: SHIPMENT
    await ledger_svc.record(
        db,
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        action=LedgerAction.SHIPMENT,
        qty_delta=-qty,
        product_id=product_id,
        batch_id=batch_id,
        from_location_id=location_id,
        user_id=user_id,
        document_id=document_id,
        reason="shipment_confirmed",
        extra={"marking_codes": marking_codes[:50]},  # keep payload small
    )


# ─── Partial pallet / open pallet (TZ §7.6 step 5) ──────────────────────────

async def find_open_pallet_location(
    db: AsyncSession, *, warehouse_id: uuid.UUID
) -> Location | None:
    """
    Return the warehouse's OPEN_PALLET-zone location (the bench where broken
    pallets live). The first active location of an OPEN_PALLET zone is used.
    """
    result = await db.execute(
        select(Location)
        .join(Zone, Zone.id == Location.zone_id)
        .where(
            Zone.warehouse_id == warehouse_id,
            Zone.zone_type == ZoneType.OPEN_PALLET,
            Zone.is_active.is_(True),
            Location.is_active.is_(True),
        )
        .order_by(Location.code)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def open_partial_pallet(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    source_stock: StockItem,
    leftover_boxes: int,
) -> uuid.UUID | None:
    """
    A pallet was broken during picking: move the *leftover* boxes to the open
    pallet location and mark the source pallet open. One open pallet per SKU.

    Returns the destination (open pallet) location id, or None when no
    OPEN_PALLET zone is configured (in which case the pallet just stays open in
    place).
    """
    source_stock.pallet_open = True
    if leftover_boxes <= 0:
        return None

    dest = await find_open_pallet_location(db, warehouse_id=warehouse_id)
    if dest is None or dest.id == source_stock.location_id:
        return None

    # Ledger MOVE: leftover boxes from source location → open pallet location.
    await ledger_svc.record(
        db,
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        action=LedgerAction.MOVE,
        qty_delta=leftover_boxes,
        product_id=source_stock.product_id,
        batch_id=source_stock.batch_id,
        from_location_id=source_stock.location_id,
        to_location_id=dest.id,
        user_id=user_id,
        document_id=document_id,
        reason="open_partial_pallet",
    )
    # The new open-pallet stock row is the leftover; mark it open too.
    dest_stock = await _get_stock(
        db, location_id=dest.id, product_id=source_stock.product_id,
        batch_id=source_stock.batch_id,
    )
    if dest_stock is not None:
        dest_stock.pallet_open = True
    return dest.id


def build_disaggregation_body(
    *,
    tin: str,
    business_place_id: int | str | None,
    parent_code: str,
    child_codes: list[str],
    business_datetime: str,
) -> dict:
    """
    Asl Belgisi transport-code-disaggregation doc body (will be base64-wrapped by
    the connector). Disaggregating a pallet (BOX_LV_*) into its GROUP children
    because we only ship part of it.
    """
    body: dict = {
        "tin": tin,
        "businessDatetime": business_datetime,
        "codes": [parent_code],
        "childCodes": child_codes,
    }
    if business_place_id is not None:
        body["businessPlaceId"] = business_place_id
    return body


# ─── Private helpers ─────────────────────────────────────────────────────────

async def _get_stock(
    db: AsyncSession,
    *,
    location_id: uuid.UUID,
    product_id: uuid.UUID,
    batch_id: uuid.UUID | None,
) -> StockItem | None:
    result = await db.execute(
        select(StockItem).where(
            StockItem.location_id == location_id,
            StockItem.product_id == product_id,
            StockItem.batch_id == batch_id,
        )
    )
    return result.scalar_one_or_none()

async def _load_available_stock(
    db: AsyncSession,
    *,
    warehouse_id: uuid.UUID,
    product_ids: list[uuid.UUID],
):
    """
    Returns (StockItem, Batch|None, Location, Zone) ordered by:
      1. open pallet first (pallet_open DESC)
      2. FEFO: earliest expiry_date (nulls last)
      3. FIFO: earliest batch created_at
    """
    result = await db.execute(
        select(StockItem, Batch, Location, Zone)
        .join(Location, Location.id == StockItem.location_id)
        .join(Zone, Zone.id == Location.zone_id)
        .outerjoin(Batch, Batch.id == StockItem.batch_id)
        .where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.product_id.in_(product_ids),
            StockItem.status == StockStatus.AVAILABLE,
            (StockItem.qty - StockItem.qty_booked) > 0,
            # FEFO/FIFO faqat AVAILABLE partiyadan teradi. Karantin / bloklangan /
            # muddati o'tgan partiya (yoki batch'siz erkin stok) chetlab o'tiladi —
            # bu inventar yaxlitligini saqlaydi (karantin tovar jo'natilmaydi).
            (Batch.id.is_(None)) | (Batch.status == BatchStatus.AVAILABLE),
        )
        .order_by(
            StockItem.pallet_open.desc(),             # open pallets first
            nulls_last(asc(Batch.expiry_date)),       # FEFO
            nulls_last(asc(Batch.created_at)),        # FIFO
        )
    )
    return result.all()


async def _get_group_codes(
    db: AsyncSession,
    *,
    location_id: uuid.UUID,
    product_id: uuid.UUID,
    limit: int,
) -> list[str]:
    """Return up to `limit` GROUP-level marking codes at a location."""
    result = await db.execute(
        select(MarkingCode.code)
        .where(
            MarkingCode.location_id == location_id,
            MarkingCode.product_id == product_id,
            MarkingCode.package_type == PackageType.GROUP,
        )
        .limit(limit)
    )
    return [row[0] for row in result.all()]
