"""
Phase 5 endpoints: Movement, Inventory Count, Write-off, Return, Reconciliation.

POST /movement                  — Internal location -> location move
GET  /replenishment             — Suggested reserve -> pick replenishment moves
POST /inventory/count           — Inventory count (full / cycle)
POST /writeoff                  — Write-off (spisaniye)
POST /return                    — Customer return inbound (vozvrat)
GET  /reconciliation            — WMS <-> Smartup balance reconciliation report

All write endpoints are tenant-guarded, warehouse-scoped, write to the ledger,
and enqueue the relevant Smartup import via the outbox (reliable delivery).
Idempotency external_id == the WMS Document id. Dates dd.mm.yyyy.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connector_factory import get_aslbelgisi_client, get_smartup_client
from app.core.deps import ActiveUser, ensure_warehouse_access, get_db, require_permission
from app.models.inventory import (
    Document, DocumentStatus, DocumentType, StockItem, StockStatus,
)
from app.models.ledger import LedgerAction
from app.models.warehouse import Location, Zone, ZoneType
from app.schemas.operations import (
    CountDiscrepancy, InventoryCountCreate, InventoryCountOut,
    MovementCreate, MovementOut,
    ReconciliationLineOut, ReconciliationOut,
    ReplenishmentOut, ReplenishmentSuggestion,
    ReturnCreate, ReturnOut,
    WriteoffCreate, WriteoffOut,
)
from app.services import documents as doc_svc
from app.services import ledger as ledger_svc
from app.services import outbox as outbox_svc
from app.services.reconciliation import run_reconciliation

router = APIRouter(tags=["operations"])
DB = Annotated[AsyncSession, Depends(get_db)]


# ─── Internal Movement ───────────────────────────────────────────────────────

@router.post(
    "/movement",
    response_model=MovementOut,
    status_code=201,
    dependencies=[require_permission("movement", "create")],
)
async def create_movement(body: MovementCreate, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    await ensure_warehouse_access(db, user, body.warehouse_id)
    await _validate_location(db, body.from_location_id, body.warehouse_id)
    await _validate_location(db, body.to_location_id, body.warehouse_id)

    if body.from_location_id == body.to_location_id:
        raise HTTPException(status_code=400, detail="from and to locations are identical")

    doc = Document(
        tenant_id=user.tenant_id,
        warehouse_id=body.warehouse_id,
        doc_type=DocumentType.MOVEMENT,
        status=DocumentStatus.IN_PROGRESS,
        created_by=user.id,
        notes=body.reason,
        extra={"sync_smartup": body.sync_smartup},
    )
    db.add(doc)
    await db.flush()

    for line in body.lines:
        # Deduct from source
        await ledger_svc.record(
            db,
            tenant_id=user.tenant_id,
            warehouse_id=body.warehouse_id,
            action=LedgerAction.MOVE,
            qty_delta=-line.qty,
            product_id=line.product_id,
            batch_id=line.batch_id,
            from_location_id=body.from_location_id,
            user_id=user.id,
            document_id=doc.id,
            reason=body.reason or "internal_move",
            extra={"marking_codes": line.marking_codes[:50]},
        )
        # Add to destination
        await ledger_svc.record(
            db,
            tenant_id=user.tenant_id,
            warehouse_id=body.warehouse_id,
            action=LedgerAction.MOVE,
            qty_delta=line.qty,
            product_id=line.product_id,
            batch_id=line.batch_id,
            to_location_id=body.to_location_id,
            user_id=user.id,
            document_id=doc.id,
            reason=body.reason or "internal_move",
        )

    doc.status = DocumentStatus.COMPLETED

    smartup_enqueued = False
    if body.sync_smartup and body.lines:
        movement_body = await doc_svc.build_movement_body(
            db,
            document_id=doc.id,
            warehouse_id=body.warehouse_id,
            lines=[
                {"product_id": ln.product_id, "qty": ln.qty,
                 "marking_codes": ln.marking_codes}
                for ln in body.lines
            ],
            reason=body.reason,
        )
        await outbox_svc.enqueue(
            db,
            tenant_id=user.tenant_id,
            connector="smartup",
            event_type="movement",
            payload=movement_body,
        )
        smartup_enqueued = True

    await db.commit()
    return MovementOut(
        document_id=doc.id,
        status=doc.status.value,
        lines_moved=len(body.lines),
        smartup_enqueued=smartup_enqueued,
    )


# ─── Replenishment suggestions (reserve -> pick) ─────────────────────────────

@router.get(
    "/replenishment",
    response_model=ReplenishmentOut,
    dependencies=[require_permission("movement", "view")],
)
async def get_replenishment(
    warehouse_id: uuid.UUID,
    user: ActiveUser,
    db: DB,
    threshold: int = 0,
):
    """Suggest reserve -> pick-face moves for SKUs whose pick location is at or
    below `threshold`. The operator can then POST /movement to execute each one.

    A SKU is replenishable when it has stock in a RESERVE zone and a pick face
    (a location in a PICK zone) that is low. We move enough from reserve to top
    the pick face up to the reserve's available qty.
    """
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    await ensure_warehouse_access(db, user, warehouse_id)

    # Stock rows joined to their zone type, available status only.
    rows = await db.execute(
        select(StockItem, Location.code, Zone.zone_type)
        .join(Location, StockItem.location_id == Location.id)
        .join(Zone, Location.zone_id == Zone.id)
        .where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.status == StockStatus.AVAILABLE,
        )
    )

    pick_faces: dict[tuple, tuple] = {}      # (product_id, batch_id) -> (stock, code)
    reserves: dict[tuple, list[tuple]] = {}  # (product_id, batch_id) -> [(stock, code)]
    for stock, loc_code, zone_type in rows.all():
        key = (stock.product_id, stock.batch_id)
        if zone_type == ZoneType.PICK:
            # Keep the lowest-qty pick face per SKU.
            if key not in pick_faces or stock.qty < pick_faces[key][0].qty:
                pick_faces[key] = (stock, loc_code)
        elif zone_type == ZoneType.RESERVE:
            reserves.setdefault(key, []).append((stock, loc_code))

    suggestions: list[ReplenishmentSuggestion] = []
    for key, (pick_stock, pick_code) in pick_faces.items():
        if pick_stock.qty > threshold:
            continue
        reserve_list = reserves.get(key)
        if not reserve_list:
            continue
        # Pick the reserve with the most available stock.
        reserve_stock, reserve_code = max(reserve_list, key=lambda r: r[0].qty)
        if reserve_stock.qty <= 0:
            continue
        suggestions.append(ReplenishmentSuggestion(
            product_id=key[0],
            batch_id=key[1],
            from_location_id=reserve_stock.location_id,
            from_location_code=reserve_code,
            to_location_id=pick_stock.location_id,
            to_location_code=pick_code,
            suggested_qty=reserve_stock.qty,
            pick_qty=pick_stock.qty,
            reserve_qty=reserve_stock.qty,
        ))

    return ReplenishmentOut(warehouse_id=warehouse_id, suggestions=suggestions)


# ─── Inventory Count ─────────────────────────────────────────────────────────

@router.post(
    "/inventory/count",
    response_model=InventoryCountOut,
    status_code=201,
    dependencies=[require_permission("inventory", "create")],
)
async def create_inventory_count(body: InventoryCountCreate, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    await ensure_warehouse_access(db, user, body.warehouse_id)

    doc = Document(
        tenant_id=user.tenant_id,
        warehouse_id=body.warehouse_id,
        doc_type=DocumentType.INVENTORY,
        status=DocumentStatus.IN_PROGRESS,
        created_by=user.id,
        notes=body.notes,
        extra={"count_type": body.count_type},
    )
    db.add(doc)
    await db.flush()

    discrepancies: list[CountDiscrepancy] = []
    stocktaking_lines: list[dict] = []

    for line in body.lines:
        await _validate_location(db, line.location_id, body.warehouse_id)

        result = await db.execute(
            select(StockItem).where(
                StockItem.location_id == line.location_id,
                StockItem.product_id == line.product_id,
                StockItem.batch_id == line.batch_id,
            )
        )
        stock = result.scalar_one_or_none()
        expected_qty = stock.qty if stock else 0
        diff = line.counted_qty - expected_qty

        # Every counted line is reported to Smartup (balance vs counted);
        # only diffs produce a ledger correction.
        stocktaking_lines.append({
            "product_id": line.product_id,
            "expected_qty": expected_qty,
            "counted_qty": line.counted_qty,
            "marking_codes": line.marking_codes,
        })

        if diff == 0:
            continue

        discrepancies.append(CountDiscrepancy(
            product_id=line.product_id,
            location_id=line.location_id,
            expected_qty=expected_qty,
            counted_qty=line.counted_qty,
            diff=diff,
        ))
        action = LedgerAction.INVENTORY_PLUS if diff > 0 else LedgerAction.INVENTORY_MINUS
        await ledger_svc.record(
            db,
            tenant_id=user.tenant_id,
            warehouse_id=body.warehouse_id,
            action=action,
            qty_delta=diff,
            product_id=line.product_id,
            batch_id=line.batch_id,
            from_location_id=line.location_id if diff < 0 else None,
            to_location_id=line.location_id if diff > 0 else None,
            user_id=user.id,
            document_id=doc.id,
            reason=f"inventory_count:{body.count_type}",
            extra={"marking_codes": line.marking_codes[:50]},
        )

    doc.status = DocumentStatus.COMPLETED

    smartup_enqueued = False
    if stocktaking_lines:
        stocktaking_body = await doc_svc.build_stocktaking_body(
            db,
            document_id=doc.id,
            warehouse_id=body.warehouse_id,
            lines=stocktaking_lines,
        )
        await outbox_svc.enqueue(
            db,
            tenant_id=user.tenant_id,
            connector="smartup",
            event_type="stocktaking",
            payload=stocktaking_body,
        )
        smartup_enqueued = True

    await db.commit()
    return InventoryCountOut(
        document_id=doc.id,
        status=doc.status.value,
        discrepancies=discrepancies,
        smartup_synced=smartup_enqueued,
    )


# ─── Write-Off ───────────────────────────────────────────────────────────────

@router.post(
    "/writeoff",
    response_model=WriteoffOut,
    status_code=201,
    dependencies=[require_permission("writeoff", "create")],
)
async def create_writeoff(body: WriteoffCreate, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    await ensure_warehouse_access(db, user, body.warehouse_id)

    doc = Document(
        tenant_id=user.tenant_id,
        warehouse_id=body.warehouse_id,
        doc_type=DocumentType.WRITEOFF,
        status=DocumentStatus.IN_PROGRESS,
        created_by=user.id,
        notes=body.notes,
    )
    db.add(doc)
    await db.flush()

    writeoff_lines: list[dict] = []
    for line in body.lines:
        await _validate_location(db, line.location_id, body.warehouse_id)
        await ledger_svc.record(
            db,
            tenant_id=user.tenant_id,
            warehouse_id=body.warehouse_id,
            action=LedgerAction.WRITEOFF,
            qty_delta=-line.qty,
            product_id=line.product_id,
            batch_id=line.batch_id,
            from_location_id=line.location_id,
            user_id=user.id,
            document_id=doc.id,
            reason=line.reason_code,
            extra={"marking_codes": line.marking_codes[:50]},
        )
        writeoff_lines.append({
            "product_id": line.product_id,
            "qty": line.qty,
            "reason_code": line.reason_code,
            "marking_codes": line.marking_codes,
        })

    doc.status = DocumentStatus.COMPLETED

    smartup_enqueued = False
    if writeoff_lines:
        writeoff_body = await doc_svc.build_writeoff_body(
            db,
            document_id=doc.id,
            warehouse_id=body.warehouse_id,
            lines=writeoff_lines,
            notes=body.notes,
        )
        await outbox_svc.enqueue(
            db,
            tenant_id=user.tenant_id,
            connector="smartup",
            event_type="writeoff",
            payload=writeoff_body,
        )
        smartup_enqueued = True

    await db.commit()
    return WriteoffOut(
        document_id=doc.id,
        status=doc.status.value,
        smartup_synced=smartup_enqueued,
    )


# ─── Return (Vozvrat) ────────────────────────────────────────────────────────

@router.post(
    "/return",
    response_model=ReturnOut,
    status_code=201,
    dependencies=[require_permission("return", "create")],
)
async def create_return(body: ReturnCreate, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    await ensure_warehouse_access(db, user, body.warehouse_id)

    disposition = body.disposition.lower()
    if disposition not in ("restock", "quarantine", "writeoff"):
        raise HTTPException(
            status_code=400,
            detail="disposition must be restock | quarantine | writeoff",
        )

    # For restock/quarantine the goods physically land in a location.
    if disposition != "writeoff":
        await _validate_location(db, body.to_location_id, body.warehouse_id)

    doc = Document(
        tenant_id=user.tenant_id,
        warehouse_id=body.warehouse_id,
        doc_type=DocumentType.RETURN,
        status=DocumentStatus.IN_PROGRESS,
        external_id=body.smartup_return_id,
        created_by=user.id,
        notes=body.notes,
        extra={"disposition": disposition},
    )
    db.add(doc)
    await db.flush()

    # restock    -> goods re-enter sellable stock (RETURN_IN, available)
    # quarantine -> goods re-enter but are held (RETURN_IN, then BLOCKED status)
    # writeoff   -> goods are scrapped on arrival (WRITEOFF, no stock created)
    ledger_action = LedgerAction.WRITEOFF if disposition == "writeoff" else LedgerAction.RETURN_IN

    for line in body.lines:
        if disposition == "writeoff":
            await ledger_svc.record(
                db,
                tenant_id=user.tenant_id,
                warehouse_id=body.warehouse_id,
                action=LedgerAction.WRITEOFF,
                qty_delta=-line.qty,
                product_id=line.product_id,
                batch_id=line.batch_id,
                from_location_id=body.to_location_id,
                user_id=user.id,
                document_id=doc.id,
                reason="return_writeoff",
                extra={"marking_codes": line.marking_codes[:50], "disposition": disposition},
            )
        else:
            await ledger_svc.record(
                db,
                tenant_id=user.tenant_id,
                warehouse_id=body.warehouse_id,
                action=LedgerAction.RETURN_IN,
                qty_delta=line.qty,
                product_id=line.product_id,
                batch_id=line.batch_id,
                to_location_id=body.to_location_id,
                user_id=user.id,
                document_id=doc.id,
                reason=f"return:{disposition}",
                extra={"marking_codes": line.marking_codes[:50], "disposition": disposition},
            )

    # Quarantined returns are not sellable: flag the stock rows BLOCKED.
    if disposition == "quarantine":
        for line in body.lines:
            res = await db.execute(
                select(StockItem).where(
                    StockItem.location_id == body.to_location_id,
                    StockItem.product_id == line.product_id,
                    StockItem.batch_id == line.batch_id,
                )
            )
            stock = res.scalar_one_or_none()
            if stock is not None:
                stock.status = StockStatus.BLOCKED

    doc.status = DocumentStatus.COMPLETED
    await db.commit()

    return ReturnOut(
        document_id=doc.id,
        status=doc.status.value,
        disposition=disposition,
        ledger_action=ledger_action.value,
        lines_returned=len(body.lines),
    )


# ─── Reconciliation ──────────────────────────────────────────────────────────

@router.get(
    "/reconciliation",
    response_model=ReconciliationOut,
    dependencies=[require_permission("reconciliation", "view")],
)
async def get_reconciliation(
    warehouse_id: uuid.UUID,
    user: ActiveUser,
    db: DB,
):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    await ensure_warehouse_access(db, user, warehouse_id)

    # Connector fetch is best-effort: a missing/unconfigured connector must not 500.
    smartup_client = None
    aslbelgisi_client = None
    try:
        smartup_client = await get_smartup_client(db, user.tenant_id)
    except Exception:
        smartup_client = None
    try:
        aslbelgisi_client = await get_aslbelgisi_client(db, user.tenant_id)
    except Exception:
        aslbelgisi_client = None

    result = await run_reconciliation(
        db,
        tenant_id=user.tenant_id,
        warehouse_id=warehouse_id,
        smartup_client=smartup_client,
        aslbelgisi_client=aslbelgisi_client,
    )

    lines = result.get("lines", [])
    summary = result.get("summary", {})
    match_count = int(summary.get("match", 0))

    return ReconciliationOut(
        warehouse_id=warehouse_id,
        total_lines=len(lines),
        match_count=match_count,
        discrepancy_count=len(lines) - match_count,
        lines=[
            ReconciliationLineOut(
                smartup_product_code=line.get("product_code") or "",
                product_id=line.get("product_id"),
                wms_qty=int(line.get("wms_qty") or 0),
                smartup_qty=int(line.get("smartup_qty") or 0),
                diff=int(line.get("diff") or 0),
                direction=str(line.get("direction") or ""),
            )
            for line in lines
        ],
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _validate_location(
    db: AsyncSession, location_id: uuid.UUID, warehouse_id: uuid.UUID
) -> Location:
    """Ensure the location exists and belongs to the given warehouse."""
    result = await db.execute(
        select(Location)
        .join(Zone, Location.zone_id == Zone.id)
        .where(Location.id == location_id, Zone.warehouse_id == warehouse_id)
    )
    loc = result.scalar_one_or_none()
    if loc is None:
        raise HTTPException(
            status_code=404,
            detail=f"Location {location_id} not found in this warehouse",
        )
    return loc
