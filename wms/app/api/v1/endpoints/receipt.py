"""
Receipt (kirim) + Putaway endpoints.

POST /receipt          — TSD transport kodlarini qabul qilish
GET  /receipt/{id}     — Hujjat holati
POST /putaway/suggest  — Yacheyka tavsiyalari
POST /putaway/confirm  — Operator tasdiqlashi (skanlash)
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connector_factory import (
    get_aslbelgisi_client, get_smartup_client, get_tenant_tin,
)
from app.core.deps import ActiveUser, ensure_warehouse_access, get_db, require_permission
from app.models.exception import ExceptionType
from app.models.inventory import Batch, Document, DocumentType, MarkingCode, Product
from app.models.task import Task, TaskStatus, TaskType
from app.models.ledger import LedgerAction
from app.models.warehouse import Location, LocationStatus, Zone
from app.schemas.inventory import (
    PutawayConfirm, ReceiptCreate, ReceiptOut, SlottingSuggestion,
    TsdScanRequest, TsdScanResponse, TsdSuggestionItem,
)
from app.services import documents as doc_svc
from app.services import exceptions as exc_svc
from app.services import ledger as ledger_svc
from app.services.receipt import process_receipt
from app.services.slotting import suggest_locations

router = APIRouter(tags=["receipt & putaway"])
DB = Annotated[AsyncSession, Depends(get_db)]


def _num(v) -> float | None:
    """Smartup son maydonini xavfsiz float'ga (bo'sh/None → None)."""
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _first(d: dict, *keys):
    """Berilgan kalitlardan birinchi bo'sh bo'lmagan qiymat (Smartup nomlash har xil)."""
    for k in keys:
        val = d.get(k)
        if val not in (None, ""):
            return val
    return None


def _normalize_receipt_item(it: dict) -> dict:
    """Kirim/xarid qatorini (product-level) barcha foydali Smartup maydonlari bilan
    normallashtiramiz — nomlash kelishmovchiliklarini fallback bilan yopamiz."""
    return {
        "product_code": _first(it, "product_code", "product_unit_code"),
        "product_name": _first(it, "product_name", "product_unit_name", "name"),
        "gtin": _first(it, "gtin", "barcode"),
        "quantity": _num(_first(it, "quant", "quantity", "input_quant", "purchase_quant", "qty")),
        "uom": _first(it, "measure_code", "measure", "uom"),
        "price": _num(_first(it, "price", "input_price", "purchase_price")),
        "total": _num(_first(it, "total_value", "margin_value", "total_margin_value", "summa", "amount")),
        "series_number": _first(it, "series_number", "series", "batch_number", "party_number"),
        "production_date": _first(it, "production_date", "manufacture_date"),
        "expiry_date": _first(it, "expiry_date", "expiration_date", "expire_date"),
    }


@router.get(
    "/receipt/production-inputs",
    dependencies=[require_permission("receipt", "view")],
)
async def production_inputs(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    begin_modified_on: str | None = None,
    end_modified_on: str | None = None,
):
    """Read production receipts from Smartup (mkw/input$export) for reconciliation
    against the physical TSD scan (TZ §16 q1). API oynasi: ≤30 kun."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    wh = await ensure_warehouse_access(db, user, warehouse_id)

    client = await get_smartup_client(db, user.tenant_id)
    codes = doc_svc.warehouse_filter(wh.smartup_warehouse_code)
    rows = await client.get_inputs(
        warehouse_codes=codes, begin_modified_on=begin_modified_on,
        end_modified_on=end_modified_on,
    )
    inputs_out = []
    for p in rows:
        items = p.get("input_items") or p.get("input_products") or []
        inputs_out.append({
            "input_id": str(_first(p, "input_id", "id") or ""),
            "input_number": _first(p, "input_number", "invoice_number", "delivery_number"),
            "date": _first(p, "input_date", "input_time"),
            "warehouse_code": _first(p, "warehouse_code"),
            "warehouse_name": _first(p, "warehouse_name"),
            "status_code": _first(p, "status_code", "status"),
            "posted": p.get("posted"),
            "note": _first(p, "note", "comment"),
            "total": _num(_first(p, "total_value", "total_margin_value")),
            "lines": len(items),
            "items": [_normalize_receipt_item(it) for it in items],
        })
    return {"count": len(inputs_out), "inputs": inputs_out}


@router.get(
    "/receipt/purchases",
    dependencies=[require_permission("receipt", "view")],
)
async def purchases(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    begin_modified_on: str | None = None,
    end_modified_on: str | None = None,
):
    """Smartup'dan TA'MINOTCHIDAN XARIDLAR (mkw/purchase$export) — distributor uchun
    asosiy kirim oqimi (zavod input$export emas). API oynasi: ≤30 kun."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    wh = await ensure_warehouse_access(db, user, warehouse_id)

    client = await get_smartup_client(db, user.tenant_id)
    codes = doc_svc.warehouse_filter(wh.smartup_warehouse_code)
    rows = await client.get_purchases(
        warehouse_codes=codes, begin_modified_on=begin_modified_on,
        end_modified_on=end_modified_on,
    )
    purchases_out = []
    for p in rows:
        items = p.get("purchase_items") or p.get("purchase_products") or []
        purchases_out.append({
            "purchase_id": str(_first(p, "purchase_id", "id") or ""),
            "purchase_number": _first(p, "purchase_number", "invoice_number"),
            "date": _first(p, "input_date") or (_first(p, "purchase_time") or "").split(" ")[0] or None,
            "supplier_code": _first(p, "supplier_code"),
            "supplier_name": _first(p, "supplier_name", "person_name"),
            "invoice_number": _first(p, "invoice_number"),
            "contract_number": _first(p, "contract_number", "deal_number"),
            "warehouse_code": _first(p, "warehouse_code"),
            "warehouse_name": _first(p, "warehouse_name"),
            "currency": _first(p, "currency_code", "currency"),
            "status_code": _first(p, "status_code", "status"),
            "posted": p.get("posted"),
            "note": _first(p, "note", "comment"),
            "lines": len(items),
            "total": _num(_first(p, "total_margin_value", "total_value")),
            "items": [_normalize_receipt_item(it) for it in items],
        })
    return {"count": len(purchases_out), "purchases": purchases_out}


@router.post(
    "/receipt",
    response_model=ReceiptOut,
    status_code=201,
    dependencies=[require_permission("receipt", "create")],
)
async def create_receipt(body: ReceiptCreate, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    client = await get_aslbelgisi_client(db, user.tenant_id)
    tenant_tin = await get_tenant_tin(db, user.tenant_id)

    return await process_receipt(
        db,
        tenant_id=user.tenant_id,
        warehouse_id=body.warehouse_id,
        user_id=user.id,
        codes=body.codes,
        notes=body.notes,
        aslbelgisi_client=client,
        tenant_tin=tenant_tin,
    )


@router.get("/receipt/{document_id}")
async def get_receipt(document_id: uuid.UUID, user: ActiveUser, db: DB):
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.doc_type == DocumentType.RECEIPT,
            Document.tenant_id == user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return {"id": doc.id, "status": doc.status, "created_at": doc.created_at}


@router.post(
    "/putaway/suggest",
    response_model=list[SlottingSuggestion],
    dependencies=[require_permission("putaway", "create")],
)
async def putaway_suggest(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = ...,
    product_id: uuid.UUID = ...,
    batch_id: uuid.UUID | None = None,
    qty: int = 1,
):
    prod_result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == user.tenant_id)
    )
    product = prod_result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    expiry: str | None = None
    if batch_id:
        batch_result = await db.execute(select(Batch).where(Batch.id == batch_id))
        batch = batch_result.scalar_one_or_none()
        expiry = batch.expiry_date if batch else None

    candidates = await suggest_locations(
        db,
        warehouse_id=warehouse_id,
        product=product,
        batch_id=batch_id,
        expiry_date=expiry,
        qty=qty,
    )

    return [
        SlottingSuggestion(
            location_id=c.location.id,
            location_code=c.location.code,
            zone_name=c.zone.name,
            score=c.score,
            reason=c.reason,
        )
        for c in candidates
    ]


@router.post(
    # MUHIM: yo'l avval "/putaway/confirm" edi — bu putaway.py dagi yangi
    # reservation-based confirm bilan TO'QNASHARDI (receipt router oldin ulanib,
    # task-based versiya yangisini soyalardi → TSD 422 "Tasdiqlashda xatolik").
    # Bu eski task-based oqim alohida yo'lga ko'chirildi.
    "/putaway/task-confirm",
    dependencies=[require_permission("putaway", "create")],
)
async def putaway_confirm(body: PutawayConfirm, user: ActiveUser, db: DB):
    """Operator confirms placement: scanned location_id for an open putaway task."""
    task_result = await db.execute(
        select(Task).where(
            Task.id == body.task_id,
            Task.tenant_id == user.tenant_id,
            Task.task_type == TaskType.PUTAWAY,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
        )
    )
    task = task_result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Putaway task not found")

    # Validate the scanned location belongs to the task's warehouse (Location→Zone)
    loc_row = (await db.execute(
        select(Location, Zone)
        .join(Zone, Zone.id == Location.zone_id)
        .where(Location.id == body.location_id)
    )).first()
    if loc_row is None:
        raise HTTPException(status_code=400, detail="Location not found")
    location, zone = loc_row
    if zone.warehouse_id != task.warehouse_id:
        raise HTTPException(status_code=400, detail="Location is in a different warehouse")

    payload = task.payload
    product_id = uuid.UUID(payload["product_id"]) if payload.get("product_id") else None
    batch_id = uuid.UUID(payload["batch_id"]) if payload.get("batch_id") else None
    qty = payload.get("qty", 0)
    marking_code = payload.get("marking_code")

    # If operator placed somewhere other than suggested → log (allowed, with trail)
    suggested = payload.get("suggested_location_id")
    if suggested and suggested != str(body.location_id):
        await exc_svc.record(
            db, tenant_id=user.tenant_id, warehouse_id=task.warehouse_id,
            exc_type=ExceptionType.WRONG_LOCATION, marking_code=marking_code,
            created_by=user.id, severity=30,
            message="Placed in a non-suggested location",
            detail={"suggested": suggested, "actual": str(body.location_id)},
        )

    if product_id and qty:
        await ledger_svc.record(
            db,
            tenant_id=user.tenant_id,
            warehouse_id=task.warehouse_id,
            action=LedgerAction.PUTAWAY,
            qty_delta=qty,
            product_id=product_id,
            batch_id=batch_id,
            marking_code=marking_code,
            to_location_id=body.location_id,
            user_id=user.id,
            document_id=task.document_id,
            reason="putaway_confirmed",
        )

    # Mark the location occupied and bind the marking code to it
    if location.status == LocationStatus.EMPTY:
        location.status = LocationStatus.OCCUPIED
    if marking_code:
        mc = (await db.execute(
            select(MarkingCode).where(MarkingCode.code == marking_code)
        )).scalar_one_or_none()
        if mc is not None:
            mc.location_id = body.location_id

    task.status = TaskStatus.COMPLETED
    task.payload = {**payload, "confirmed_location_id": str(body.location_id)}
    await db.commit()

    return {"task_id": task.id, "status": "completed", "location_id": body.location_id}


@router.post(
    "/putaway/tsd-scan",
    response_model=TsdScanResponse,
    summary="TSD: GTIN skanlab joylash tavsiyasi olish",
)
async def tsd_scan_suggest(body: TsdScanRequest, user: ActiveUser, db: DB):
    """
    TSD qurilma uchun bitta endpoint:
    1. GTIN bo'yicha mahsulotni topadi
    2. Ad-hoc PUTAWAY task yaratadi
    3. Analitikaga asoslangan yacheyka tavsiyalarini qaytaradi
    """
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    # 1. GTIN bo'yicha mahsulot topish
    prod_result = await db.execute(
        select(Product).where(
            Product.gtin == body.gtin,
            Product.tenant_id == user.tenant_id,
            Product.is_active.is_(True),
        )
    )
    product = prod_result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail=f"GTIN {body.gtin} bo'yicha mahsulot topilmadi")

    # 2. Analitikaga asoslangan joylash tavsiyalari
    candidates = await suggest_locations(
        db,
        warehouse_id=body.warehouse_id,
        product=product,
        batch_id=None,
        expiry_date=None,
        qty=body.qty,
        top_n=40,  # ko'proq nomzod — keyin code bo'yicha dedup qilib, turli kataklarni ko'rsatamiz
    )

    # 3. Ad-hoc PUTAWAY task yaratish (keyinchalik confirm uchun kerak)
    top_location_id = str(candidates[0].location.id) if candidates else None
    task = Task(
        tenant_id=user.tenant_id,
        warehouse_id=body.warehouse_id,
        task_type=TaskType.PUTAWAY,
        status=TaskStatus.PENDING,
        payload={
            "product_id": str(product.id),
            "qty": body.qty,
            "source": "tsd_scan",
            "suggested_location_id": top_location_id,
        },
    )
    db.add(task)
    await db.commit()

    product_name = (
        product.name.get("uz")
        or product.name.get("ru")
        or product.name.get("en")
        or str(product.id)
    )

    # Bir katakda bir nechta slot (tier/pos) bir xil code'ga ega —
    # operatorga takror ko'rinmasligi uchun code bo'yicha dedup qilamiz.
    seen_codes: set[str] = set()
    unique_candidates = []
    for c in candidates:
        if c.location.code in seen_codes:
            continue
        seen_codes.add(c.location.code)
        unique_candidates.append(c)

    return TsdScanResponse(
        task_id=task.id,
        product_id=product.id,
        product_name=product_name,
        suggestions=[
            TsdSuggestionItem(
                location_id=c.location.id,
                location_code=c.location.code,
                zone_name=c.zone.name,
                score=round(c.score, 1),
                reason=c.reason,
            )
            for c in unique_candidates[:5]
        ],
    )
