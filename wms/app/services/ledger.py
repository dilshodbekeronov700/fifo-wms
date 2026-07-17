"""Ledger service — single entry-point for writing immutable stock events."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import StockItem
from app.models.ledger import LedgerAction, LedgerEntry
from sqlalchemy import select


async def record(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    action: LedgerAction,
    qty_delta: int,
    product_id: uuid.UUID | None = None,
    batch_id: uuid.UUID | None = None,
    marking_code: str | None = None,
    from_location_id: uuid.UUID | None = None,
    to_location_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    reason: str | None = None,
    extra: dict[str, Any] | None = None,
) -> LedgerEntry:
    """Append an immutable ledger entry and update StockItem cache."""
    entry = LedgerEntry(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        action=action,
        qty_delta=qty_delta,
        product_id=product_id,
        batch_id=batch_id,
        marking_code=marking_code,
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        user_id=user_id,
        document_id=document_id,
        reason=reason,
        extra=extra or {},
    )
    db.add(entry)

    # BOOK / UNBOOK — bu rezervatsiya harakati: fizik `qty` o'zgarmaydi, faqat
    # `qty_booked` (uni picking servisi boshqaradi). Aks holda ledger fizik
    # miqdorni kamaytirib, qty_booked > qty holatini keltirib chiqaradi (CHECK
    # buziladi). Shuning uchun bu action'lar uchun fizik keshni o'zgartirmaymiz.
    if action in (LedgerAction.BOOK, LedgerAction.UNBOOK):
        return entry

    # Update StockItem cache
    if product_id and (from_location_id or to_location_id):
        if to_location_id and qty_delta > 0:
            new_qty = await _adjust_stock(
                db, warehouse_id=warehouse_id, location_id=to_location_id,
                product_id=product_id, batch_id=batch_id, delta=qty_delta,
            )
            _publish_stock(tenant_id, to_location_id, product_id, new_qty)
        if from_location_id and qty_delta < 0:
            new_qty = await _adjust_stock(
                db, warehouse_id=warehouse_id, location_id=from_location_id,
                product_id=product_id, batch_id=batch_id, delta=qty_delta,
            )
            _publish_stock(tenant_id, from_location_id, product_id, new_qty)

    return entry


def _publish_stock(
    tenant_id: uuid.UUID,
    location_id: uuid.UUID,
    product_id: uuid.UUID,
    qty: int,
) -> None:
    """Best-effort real-time stock notification (TZ §5.1).

    Wrapped so a publish failure can never break a ledger write. The event bus
    is imported lazily to avoid import cycles.
    """
    try:
        from app.core.events import bus

        bus.publish(
            str(tenant_id),
            {
                "type": "stock",
                "location_id": str(location_id),
                "product_id": str(product_id),
                "qty": qty,
            },
        )
    except Exception:
        pass


async def _adjust_stock(
    db: AsyncSession,
    *,
    warehouse_id: uuid.UUID,
    location_id: uuid.UUID,
    product_id: uuid.UUID,
    batch_id: uuid.UUID | None,
    delta: int,
) -> int:
    result = await db.execute(
        select(StockItem)
        .where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.location_id == location_id,
            StockItem.product_id == product_id,
            StockItem.batch_id == batch_id,
        )
        .with_for_update()
    )
    stock = result.scalar_one_or_none()

    if stock is None:
        stock = StockItem(
            warehouse_id=warehouse_id,
            location_id=location_id,
            product_id=product_id,
            batch_id=batch_id,
            qty=max(0, delta),
        )
        db.add(stock)
        new_qty = stock.qty
    else:
        stock.qty = max(0, stock.qty + delta)
        new_qty = stock.qty
    return new_qty
