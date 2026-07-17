"""
RMA (Return Merchandise Authorization) — mijoz qaytarishi + tasnif (disposition).

Oddiy "return inbound"dan farqi: har qaytgan tovar uchun QAROR qabul qilinadi:
  * RESTOCK    — soz holatda → qayta stokka (RETURN_IN, partiya AVAILABLE).
  * QUARANTINE — tekshirish kerak → karantin zonaga (RETURN_IN + Batch QUARANTINE).
  * SCRAP      — brak → hisobdan chiqarish (WRITEOFF, stokka qo'shilmaydi).

Har qaror mos ledger yozuvini beradi; hammasi bitta RETURN hujjati ostida.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum as PyEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import (
    Batch, BatchStatus, Document, DocumentStatus, DocumentType,
)
from app.models.ledger import LedgerAction
from app.models.warehouse import Location, Zone, ZoneType
from app.services import ledger as ledger_svc


class Disposition(str, PyEnum):
    RESTOCK = "restock"
    QUARANTINE = "quarantine"
    SCRAP = "scrap"


@dataclass
class RmaLine:
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    qty: int
    disposition: Disposition
    location_id: uuid.UUID | None = None   # RESTOCK/QUARANTINE uchun; None → zona bo'yicha topiladi
    marking_codes: list[str] | None = None


@dataclass
class RmaResult:
    document_id: uuid.UUID
    restocked: int
    quarantined: int
    scrapped: int


async def _zone_location(db: AsyncSession, warehouse_id: uuid.UUID, ztype: ZoneType) -> Location | None:
    return (await db.execute(
        select(Location)
        .join(Zone, Zone.id == Location.zone_id)
        .where(
            Zone.warehouse_id == warehouse_id, Zone.zone_type == ztype,
            Zone.is_active.is_(True), Location.is_active.is_(True),
        )
        .order_by(Location.code)
        .limit(1)
    )).scalar_one_or_none()


async def process_rma(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    lines: list[RmaLine],
    user_id: uuid.UUID | None,
    external_id: str | None = None,
    notes: str | None = None,
) -> RmaResult:
    """RMA hujjatini yaratadi va har qatorni tasnifiga ko'ra ledgerga yozadi."""
    doc = Document(
        tenant_id=tenant_id, warehouse_id=warehouse_id,
        doc_type=DocumentType.RETURN, status=DocumentStatus.IN_PROGRESS,
        external_id=external_id, created_by=user_id, notes=notes,
        extra={"rma": True},
    )
    db.add(doc)
    await db.flush()

    restocked = quarantined = scrapped = 0
    for ln in lines:
        if ln.qty <= 0:
            continue
        extra = {"disposition": ln.disposition.value}
        if ln.marking_codes:
            extra["marking_codes"] = ln.marking_codes[:50]

        if ln.disposition == Disposition.SCRAP:
            # Brak — stokka qo'shilmaydi, hisobdan chiqariladi.
            await ledger_svc.record(
                db, tenant_id=tenant_id, warehouse_id=warehouse_id,
                action=LedgerAction.WRITEOFF, qty_delta=-ln.qty,
                product_id=ln.product_id, batch_id=ln.batch_id,
                user_id=user_id, document_id=doc.id, reason="rma_scrap", extra=extra,
            )
            scrapped += ln.qty
            continue

        # RESTOCK / QUARANTINE — joyni aniqlaymiz.
        loc_id = ln.location_id
        if loc_id is None:
            ztype = ZoneType.RETURN if ln.disposition == Disposition.RESTOCK else ZoneType.QUARANTINE
            loc = await _zone_location(db, warehouse_id, ztype)
            if loc is None:   # zona sozlanmagan bo'lsa, RESTOCK RETURN'siz ham qaytadi
                raise ValueError(f"no_{ztype.value}_location")
            loc_id = loc.id

        await ledger_svc.record(
            db, tenant_id=tenant_id, warehouse_id=warehouse_id,
            action=LedgerAction.RETURN_IN, qty_delta=ln.qty,
            product_id=ln.product_id, batch_id=ln.batch_id,
            to_location_id=loc_id, user_id=user_id, document_id=doc.id,
            reason=f"rma_{ln.disposition.value}", extra=extra,
        )
        if ln.disposition == Disposition.QUARANTINE:
            quarantined += ln.qty
            if ln.batch_id is not None:
                batch = await db.get(Batch, ln.batch_id)
                if batch is not None:
                    batch.status = BatchStatus.QUARANTINE
        else:
            restocked += ln.qty

    doc.status = DocumentStatus.COMPLETED
    await db.flush()
    return RmaResult(document_id=doc.id, restocked=restocked,
                     quarantined=quarantined, scrapped=scrapped)
