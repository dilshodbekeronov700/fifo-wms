"""
Picking & Shipment endpoints (TZ §7.6 — Outbound).

GET  /shipment/orders            — Smartup buyurtmalarini olish (terish uchun)
POST /shipment/pick-task         — Zakaz asosida terish vazifasini yaratish
GET  /shipment/pick-task/{id}    — Vazifa holati + marshrut
POST /shipment/scan              — TSD: kodni skanlash va validatsiya
POST /shipment/confirm/{doc_id}  — Terish tugadi → Smartup ga yuborish
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connector_factory import (
    get_aslbelgisi_client, get_business_place_id, get_smartup_client,
    get_tenant_tin,
)
from app.core.deps import (
    ActiveUser, ensure_warehouse_access, get_db, require_permission,
)
from app.models.inventory import (
    Document, DocumentStatus, DocumentType, MarkingCode, PackageType, Product,
    StockItem, StockStatus,
)
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.shipment import (
    OrderLineIn, PickStop, PickTaskCreate, PickTaskOut,
    ScanValidateRequest, ScanValidateResponse,
    ShipmentConfirmResponse, ShipmentOrder, ShipmentOrderLine,
    ValidationIssue,
)
from app.services import documents as doc_svc
from app.services import outbox as outbox_svc
from app.services.picking import (
    AllotmentLine, PickPlan,
    build_disaggregation_body, build_pick_plan, confirm_shipment,
    execute_pick_plan, open_partial_pallet,
)
from app.services.route_optimizer import optimise_route

router = APIRouter(prefix="/shipment", tags=["shipment"])
DB = Annotated[AsyncSession, Depends(get_db)]

# Buyurtma statuslari — jonli order$export + Smartup UI bilan tasdiqlangan (2026-07-18):
#   B#N = Новый (yangi, terilishi kerak)          — Smartup "Новый" bilan aniq mos (88=88)
#   B#V = Band/tasdiqlangan (jarayonda, teriladi)
#   B#S = Отгружен (allaqachon jo'natilgan)        — Smartup "Отгружен" bilan mos (25=25)
#   C   = Доставлен (yetkazilgan) · D = Черновик (qoralama)
#   A   = ARXIV — Smartup faol ro'yxatda KO'RSATMAYDI (638 ta). Ilgari bu yerga
#         xato kiritilgani uchun "ochiq" ro'yxat 749 gacha shishardi.
# Terilishi kerak (ochiq) = B#N + B#V. "Barcha" ko'rinishi ham arxivni (A) chiqarib tashlaydi,
# shunda WMS soni Smartup UI (~327) bilan mos keladi.
# Smartup UI `order_list:get_widget_data` javobidan TASDIQLANGAN status→nom xaritasi
# (Chrome orqali jonli tekshirilgan, 2026-07-21):
#   D=Черновик, B#N=Новый, B#E=В обработке, B#W=В ожидании, B#S=Отгружен,
#   B#V=Доставлен (Yetkazilgan!).  granted_statuses = [D,B#N,B#E,B#W,B#S,B#V].
# DIQQAT: "C" — Smartup faol "Заказы" ro'yxatida KO'RSATILMAYDI (granted emas —
#   yopilgan/arxiv-yaqin holat). Shuning uchun WMS ham C ni chiqarib tashlaydi.
#   (Ilgari C=Доставлен, B#V=Tasdiqlangan deb xato qilingan edi — teskari edi.)
# "Barcha" = Smartup UI "Все заказы" bilan AYNAN bir xil to'plam → son mos keladi.
ALL_ORDER_STATUSES = ["D", "B#N", "B#E", "B#W", "B#S", "B#V"]
# Terilishi kerak (ochiq) = hali jo'natilmagan/yetkazilmagan: Yangi + jarayonda + kutilmoqda.
OPEN_ORDER_STATUSES = ["B#N", "B#E", "B#W"]


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _resolve_product_by_gtin(
    db: AsyncSession, tenant_id: uuid.UUID, gtin: str | None
) -> Product | None:
    if not gtin:
        return None
    res = await db.execute(
        select(Product).where(Product.tenant_id == tenant_id, Product.gtin == gtin)
    )
    return res.scalars().first()


async def _resolve_product(
    db: AsyncSession, tenant_id: uuid.UUID, product_code: str | None, gtin: str | None
) -> Product | None:
    """Smartup order qatorini WMS mahsulotga bog'lash: smartup_product_code (aniq,
    keyin '_N' qo'shimchasiz), so'ng GTIN fallback. Smartup order_products'da GTIN YO'Q,
    shuning uchun asosiy kalit — product_code."""
    candidates: list[str] = []
    if product_code:
        candidates.append(product_code)
        if "_" in product_code:
            candidates.append(product_code.split("_")[0])
    for c in candidates:
        if not c:
            continue
        prod = (await db.execute(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.smartup_product_code == c,
                Product.is_active.is_(True),
            )
        )).scalars().first()
        if prod is not None:
            return prod
    return await _resolve_product_by_gtin(db, tenant_id, gtin)


async def _available_boxes(
    db: AsyncSession, *, warehouse_id: uuid.UUID, product_id: uuid.UUID
) -> int:
    """Bitta SKU uchun bo'sh qoldiq (pick-task validatsiyasida — kichik N)."""
    res = await db.execute(
        select(func.coalesce(func.sum(StockItem.qty - StockItem.qty_booked), 0)).where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.product_id == product_id,
            StockItem.status == StockStatus.AVAILABLE,
        )
    )
    return int(res.scalar_one() or 0)


async def _availability_map(
    db: AsyncSession, *, warehouse_id: uuid.UUID
) -> dict[uuid.UUID, int]:
    """Ombordagi BARCHA SKU uchun bo'sh (band qilinmagan) GROUP-quti qoldig'i —
    BITTA guruhlangan so'rovda. Avval har order-qatorда alohida so'rov qilinardi
    (N+1) — yuzlab buyurtmaда bu Neon (US) latency bilan timeout'ga olib kelardi.
    (qty_booked <= qty — CHECK constraint, shuning uchun sum manfiy bo'lmaydi.)"""
    res = await db.execute(
        select(StockItem.product_id, func.sum(StockItem.qty - StockItem.qty_booked))
        .where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.status == StockStatus.AVAILABLE,
        )
        .group_by(StockItem.product_id)
    )
    return {pid: int(total or 0) for pid, total in res.all()}


# ── GET orders (pull from Smartup) ───────────────────────────────────────────

@router.get(
    "/orders",
    response_model=list[ShipmentOrder],
    dependencies=[require_permission("shipment", "view")],
)
async def get_shipment_orders(
    user: ActiveUser,
    db: DB,
    warehouse_id: uuid.UUID = Query(...),
    statuses: Annotated[list[str] | None, Query()] = None,
    all_statuses: bool = Query(False),
    begin_modified_on: str | None = Query(None),
    end_modified_on: str | None = Query(None),
):
    """Pull Smartup orders so the manager can start a pick.

    Default: faqat OCHIQ (terilishi kerak) buyurtmalar (B#N/B#V). `all_statuses=true`
    bo'lsa — arxiv (A) dan tashqari BARCHA buyurtmalar (yetkazilgan/jo'natilgan/qoralama
    ham) — Smartup UI ro'yxati bilan mos (~327). Lines WMS product_id + mavjudlik bilan
    boyitiladi."""
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    wh = await ensure_warehouse_access(db, user, warehouse_id)

    client = await get_smartup_client(db, user.tenant_id)
    wh_codes = doc_svc.warehouse_filter(wh.smartup_warehouse_code)
    # all_statuses → arxivdan (A) tashqari HAMMASI (Smartup UI kabi ~327).
    # Aks holda faqat ochiq (terilishi kerak) — B#N/B#V.
    effective_statuses = statuses or (ALL_ORDER_STATUSES if all_statuses else OPEN_ORDER_STATUSES)
    orders = await client.get_orders(
        statuses=effective_statuses,
        warehouse_codes=wh_codes,
        begin_modified_on=begin_modified_on,
        end_modified_on=end_modified_on,
    )

    out: list[ShipmentOrder] = []
    # Barcha SKU mavjudligini BIR marta olamiz (N+1 emas).
    avail_map = await _availability_map(db, warehouse_id=warehouse_id)
    # Smartup order_products'da GTIN/nom YO'Q — faqat product_code. WMS Product'dan
    # (smartup_product_code, keyin gtin) boyitamiz: nom + gtin + qoldiq.
    prod_cache: dict[str, Product | None] = {}

    async def _resolve(code: str, gtin: str | None) -> Product | None:
        key = f"c:{code}" if code else f"g:{gtin}"
        if key not in prod_cache:
            prod_cache[key] = await _resolve_product(db, user.tenant_id, code, gtin)
        return prod_cache[key]

    for o in orders:
        lines: list[ShipmentOrderLine] = []
        for ln in o.lines:
            prod = await _resolve(ln.product_code, ln.gtin)
            avail = avail_map.get(prod.id, 0) if prod else None
            pname = None
            if prod is not None and isinstance(prod.name, dict):
                pname = prod.name.get("uz") or prod.name.get("ru")
            lines.append(ShipmentOrderLine(
                product_unit_id=ln.product_unit_id,
                product_code=ln.product_code,
                gtin=ln.gtin or (prod.gtin if prod else None),
                product_name=ln.product_name or pname,
                expiry_date=ln.expiry_date,
                qty_ordered=ln.qty_ordered,
                uom=ln.uom,
                product_id=prod.id if prod else None,
                available_boxes=avail,
                product_price=ln.product_price,
                price_type_code=ln.price_type_code,
                vat_percent=ln.vat_percent,
                batch_number=ln.batch_number,
                warehouse_code=ln.warehouse_code,
                sold_amount=ln.sold_amount,
            ))
        out.append(ShipmentOrder(
            deal_id=o.deal_id,
            order_number=o.order_number,
            status=o.status,
            customer_tin=o.customer_tin,
            customer_name=o.customer_name,
            total_amount=o.total_amount,
            order_date=o.order_date,
            delivery_date=o.delivery_date,
            with_marking=o.with_marking,
            working_zone=o.working_zone,
            payment_type_code=o.payment_type_code,
            price_type_code=o.price_type_code,
            delivery_address=o.delivery_address,
            delivery_number=o.delivery_number,
            contract_number=o.contract_number,
            note=o.note,
            discount_value=o.discount_value,
            discount_kind=o.discount_kind,
            weight_netto=o.weight_netto,
            weight_brutto=o.weight_brutto,
            litre=o.litre,
            sales_manager_name=o.sales_manager_name,
            expeditor_name=o.expeditor_name,
            driver_name=o.driver_name,
            self_shipment=o.self_shipment,
            lines=lines,
        ))
    return out


# ── Create pick task ─────────────────────────────────────────────────────────

@router.post(
    "/pick-task",
    response_model=PickTaskOut,
    status_code=201,
    dependencies=[require_permission("shipment", "create")],
)
async def create_pick_task(body: PickTaskCreate, user: ActiveUser, db: DB):
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    wh = await ensure_warehouse_access(db, user, body.warehouse_id)

    issues: list[ValidationIssue] = []

    # 1. Resolve order lines — either explicit, or pulled from the Smartup deal.
    lines: list[OrderLineIn] = list(body.lines)
    line_product_unit: dict[str, str] = {}
    if not lines:
        client = await get_smartup_client(db, user.tenant_id)
        wh_codes = doc_svc.warehouse_filter(wh.smartup_warehouse_code)
        orders = await client.get_orders(
            statuses=OPEN_ORDER_STATUSES, warehouse_codes=wh_codes
        )
        order = next((o for o in orders if o.deal_id == body.smartup_deal_id), None)
        if order is None:
            raise HTTPException(
                status_code=404,
                detail=f"Smartup deal {body.smartup_deal_id} ochiq buyurtmalar orasida topilmadi",
            )
        for idx, ln in enumerate(order.lines):
            lines.append(OrderLineIn(
                order_line_id=f"{order.deal_id}:{ln.product_unit_id or idx}",
                gtin=ln.gtin,
                product_code=ln.product_code,
                product_unit_id=ln.product_unit_id,
                requested_boxes=int(ln.qty_ordered),
            ))

    # 2. Resolve product_id (GTIN→SKU) + validate availability per line.
    resolved_lines: list[tuple[OrderLineIn, uuid.UUID]] = []
    for ln in lines:
        product_id = ln.product_id
        if product_id is None:
            prod = await _resolve_product(db, user.tenant_id, ln.product_code, ln.gtin)
            if prod is None:
                issues.append(ValidationIssue(
                    order_line_id=ln.order_line_id,
                    kind="unmapped_product",
                    detail=f"Mahsulot topilmadi (kod={ln.product_code}, gtin={ln.gtin}) — WMS'da mapping yo'q",
                ))
                continue
            product_id = prod.id

        avail = await _available_boxes(
            db, warehouse_id=body.warehouse_id, product_id=product_id
        )
        if ln.requested_boxes > avail:
            issues.append(ValidationIssue(
                order_line_id=ln.order_line_id,
                kind="over_pick",
                detail="Requested quantity exceeds available stock",
                requested=ln.requested_boxes,
                available=avail,
            ))
            # over-pick is flagged but we still allocate what we can (shortfall)
        if ln.product_unit_id:
            line_product_unit[ln.order_line_id] = ln.product_unit_id
        resolved_lines.append((ln, product_id))

    if not resolved_lines:
        raise HTTPException(
            status_code=422,
            detail={"message": "No pickable lines", "issues": [i.model_dump() for i in issues]},
        )

    # 3. Document header.
    doc = Document(
        tenant_id=user.tenant_id,
        warehouse_id=body.warehouse_id,
        doc_type=DocumentType.SHIPMENT,
        status=DocumentStatus.IN_PROGRESS,
        external_id=body.smartup_deal_id,
        smartup_id=body.smartup_deal_id,
        created_by=user.id,
        extra={"product_units": line_product_unit},
    )
    db.add(doc)
    await db.flush()

    # 4. Build FEFO/FIFO pick plans per line.
    plans: list[PickPlan] = []
    shortfall_lines: list[str] = []
    for ln, product_id in resolved_lines:
        plan = await build_pick_plan(
            db,
            warehouse_id=body.warehouse_id,
            product_id=product_id,
            order_line_id=ln.order_line_id,
            requested_boxes=ln.requested_boxes,
        )
        plans.append(plan)
        if plan.shortfall > 0:
            shortfall_lines.append(ln.order_line_id)
            issues.append(ValidationIssue(
                order_line_id=ln.order_line_id,
                kind="shortfall",
                detail="Could not fully allocate requested boxes",
                requested=ln.requested_boxes,
                available=ln.requested_boxes - plan.shortfall,
            ))

    # 5. Execute plans (BOOK stock) and handle partial pallets.
    all_codes: list[str] = []
    disagg_count = 0
    for plan in plans:
        codes = await execute_pick_plan(
            db,
            tenant_id=user.tenant_id,
            warehouse_id=body.warehouse_id,
            user_id=user.id,
            document_id=doc.id,
            plan=plan,
        )
        all_codes.extend(codes)

        # Partial pallet handling per allotment.
        for al in plan.allotments:
            if not al.is_partial_pallet:
                continue
            stock = al.stock_item
            leftover = max(0, stock.qty - stock.qty_booked)
            await open_partial_pallet(
                db,
                tenant_id=user.tenant_id,
                warehouse_id=body.warehouse_id,
                user_id=user.id,
                document_id=doc.id,
                source_stock=stock,
                leftover_boxes=leftover,
            )
            # Enqueue Asl Belgisi disaggregation of the broken pallet.
            disagg = await _maybe_enqueue_disaggregation(
                db, tenant_id=user.tenant_id, product_id=plan.order_line_product_id,
                location_id=stock.location_id, taken_codes=al.marking_codes,
            )
            if disagg:
                disagg_count += 1

    # 6. Optimise route over all allotment locations.
    all_allotments: list[AllotmentLine] = [al for p in plans for al in p.allotments]
    unique_locations = {al.location.id: al.location for al in all_allotments}
    route_stops = optimise_route(list(unique_locations.values()))
    loc_seq = {stop.location.id: stop.sequence for stop in route_stops}

    # Yig'ish varag'ida ko'rsatish uchun mahsulot nomi/kodini oldindan yuklaymiz.
    prod_ids = {pid for _, pid in resolved_lines}
    prod_by_id: dict[uuid.UUID, Product] = {}
    if prod_ids:
        res = await db.execute(select(Product).where(Product.id.in_(prod_ids)))
        prod_by_id = {p.id: p for p in res.scalars()}

    def _pname(prod: Product | None) -> str | None:
        if prod is not None and isinstance(prod.name, dict):
            return prod.name.get("uz") or prod.name.get("ru")
        return None

    route: list[PickStop] = []
    for al in sorted(all_allotments, key=lambda a: loc_seq.get(a.location.id, 999)):
        prod = prod_by_id.get(al.stock_item.product_id)
        route.append(PickStop(
            sequence=loc_seq.get(al.location.id, 0),
            location_id=al.location.id,
            location_code=al.location.code,
            product_id=al.stock_item.product_id,
            product_code=prod.smartup_product_code if prod else None,
            product_name=_pname(prod),
            take_qty=al.take_qty,
            marking_codes=al.marking_codes,
            is_partial_pallet=al.is_partial_pallet,
            lot_number=al.batch.lot_number if al.batch else None,
            production_date=al.batch.production_date if al.batch else None,
            expiry_date=al.batch.expiry_date if al.batch else None,
        ))

    # 7. PICK task for TSD.
    task = Task(
        tenant_id=user.tenant_id,
        warehouse_id=body.warehouse_id,
        task_type=TaskType.PICK,
        status=TaskStatus.PENDING,
        document_id=doc.id,
        payload={
            "deal_id": body.smartup_deal_id,
            "codes": all_codes,
            "product_units": line_product_unit,
            "route": [
                {
                    "location_id": str(s.location_id),
                    "product_id": str(s.product_id),
                    "order_line_id": _line_for_product(resolved_lines, s.product_id),
                    "take_qty": s.take_qty,
                    "marking_codes": s.marking_codes,
                }
                for s in route
            ],
        },
    )
    db.add(task)
    await db.commit()

    return PickTaskOut(
        document_id=doc.id,
        task_id=task.id,
        deal_id=body.smartup_deal_id,
        shortfall_lines=shortfall_lines,
        issues=issues,
        route=route,
    )


def _line_for_product(
    resolved_lines: list[tuple[OrderLineIn, uuid.UUID]], product_id: uuid.UUID
) -> str | None:
    for ln, pid in resolved_lines:
        if pid == product_id:
            return ln.order_line_id
    return None


async def _maybe_enqueue_disaggregation(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    location_id: uuid.UUID,
    taken_codes: list[str],
) -> bool:
    """If the broken pallet has a transport (BOX_LV_*) parent code, enqueue an
    Asl Belgisi disaggregation doc (payload = doc body dict)."""
    if not taken_codes:
        return False
    # Find the parent pallet (transport) code at this location.
    res = await db.execute(
        select(MarkingCode).where(
            MarkingCode.location_id == location_id,
            MarkingCode.product_id == product_id,
            MarkingCode.package_type.in_([PackageType.BOX_LV_1, PackageType.BOX_LV_2]),
        ).limit(1)
    )
    parent = res.scalar_one_or_none()
    if parent is None:
        return False

    tin = await get_tenant_tin(db, tenant_id)
    bp_id = await get_business_place_id(db, tenant_id)
    body = build_disaggregation_body(
        tin=tin,
        business_place_id=bp_id,
        parent_code=parent.code,
        child_codes=taken_codes,
        business_datetime=datetime.now(timezone.utc).isoformat(),
    )
    await outbox_svc.enqueue(
        db, tenant_id=tenant_id, connector="aslbelgisi",
        event_type="disaggregation", payload=body,
    )
    return True


# ── Get pick task ────────────────────────────────────────────────────────────

@router.get(
    "/pick-task/{task_id}",
    dependencies=[require_permission("shipment", "view")],
)
async def get_pick_task(task_id: uuid.UUID, user: ActiveUser, db: DB):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.tenant_id == user.tenant_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": task.id,
        "status": task.status,
        "document_id": task.document_id,
        "payload": task.payload,
    }


# ── Scan validate (TSD) ──────────────────────────────────────────────────────

@router.post(
    "/scan",
    response_model=ScanValidateResponse,
    dependencies=[require_permission("shipment", "update")],
)
async def scan_validate(body: ScanValidateRequest, user: ActiveUser, db: DB):
    """
    TSD scans a GROUP code during picking. We:
      1. Resolve ownership via Asl Belgisi owner_check (must be ours).
      2. Confirm the code belongs to this pick task (GTIN→SKU of an open line).
      3. Accept (remove from remaining list) or reject with a reason.
    """
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    task_result = await db.execute(
        select(Task).where(
            Task.id == body.task_id,
            Task.tenant_id == user.tenant_id,
            Task.task_type == TaskType.PICK,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
        )
    )
    task = task_result.scalar_one_or_none()
    if task is None:
        return ScanValidateResponse(accepted=False, reason="Task not found or already completed")

    expected_codes: list[str] = task.payload.get("codes", [])

    # Code must be part of this order's plan.
    if body.scanned_code not in expected_codes:
        mc_result = await db.execute(
            select(MarkingCode).where(MarkingCode.code == body.scanned_code)
        )
        mc = mc_result.scalar_one_or_none()
        if mc is None:
            return ScanValidateResponse(accepted=False, reason="Code not found in system")
        return ScanValidateResponse(
            accepted=False,
            reason="Code does not belong to this order",
            package_type=mc.package_type.value if mc.package_type else None,
            gtin=mc.gtin,
        )

    # Ownership / status check via Asl Belgisi.
    pkg_type: str | None = None
    gtin: str | None = None
    try:
        client = await get_aslbelgisi_client(db, user.tenant_id)
        tin = await get_tenant_tin(db, user.tenant_id)
        oc = await client.owner_check([body.scanned_code], tin)
        if not oc.is_owned(body.scanned_code):
            reason = (
                "Code owned by another TIN"
                if body.scanned_code in oc.forbidden_codes
                else "Code not found in Asl Belgisi"
            )
            return ScanValidateResponse(accepted=False, reason=reason)
        info = oc.by_code().get(body.scanned_code)
        if info:
            pkg_type = info.package_type
    except HTTPException:
        # Connector not configured — fall back to local validation only.
        pass
    except Exception:
        # Network/owner-check failure — do not block the picker on infra issues.
        pass

    if pkg_type is None or gtin is None:
        mc_result = await db.execute(
            select(MarkingCode).where(MarkingCode.code == body.scanned_code)
        )
        mc = mc_result.scalar_one_or_none()
        if mc is not None:
            pkg_type = pkg_type or (mc.package_type.value if mc.package_type else None)
            gtin = gtin or mc.gtin

    if task.status == TaskStatus.PENDING:
        task.status = TaskStatus.IN_PROGRESS

    remaining = [c for c in expected_codes if c != body.scanned_code]
    task.payload = {**task.payload, "codes": remaining}

    task_done = len(remaining) == 0
    if task_done:
        task.status = TaskStatus.COMPLETED

    await db.commit()
    return ScanValidateResponse(
        accepted=True,
        reason=None,
        task_completed=task_done,
        package_type=pkg_type,
        gtin=gtin,
        remaining=len(remaining),
    )


# ── Confirm shipment → Smartup ────────────────────────────────────────────────

@router.post(
    "/confirm/{document_id}",
    response_model=ShipmentConfirmResponse,
    dependencies=[require_permission("shipment", "update")],
)
async def confirm_shipment_endpoint(
    document_id: uuid.UUID,
    user: ActiveUser,
    db: DB,
):
    """
    All picks done → BOOK→SHIPMENT ledger → enqueue Smartup attach_marking_codes
    + change_order_status(B#S) via outbox → Document COMPLETED.
    """
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == user.tenant_id,
            Document.doc_type == DocumentType.SHIPMENT,
            Document.status == DocumentStatus.IN_PROGRESS,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Shipment document not found")

    task_result = await db.execute(
        select(Task).where(
            Task.document_id == document_id, Task.task_type == TaskType.PICK
        )
    )
    task = task_result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=400, detail="No pick task associated with this document")

    payload = task.payload
    deal_id: str = payload.get("deal_id", "")
    route_items: list[dict] = payload.get("route", [])
    # order_line_id → product_unit_id mapping for Smartup
    product_units: dict[str, str] = payload.get("product_units", {}) or doc.extra.get("product_units", {})

    all_codes: list[str] = []
    smartup_lines_list: list[dict] = []

    for item in route_items:
        loc_id = uuid.UUID(item["location_id"])
        prod_id = uuid.UUID(item["product_id"])
        qty = item["take_qty"]
        codes = item.get("marking_codes", [])
        all_codes.extend(codes)

        # BOOK → SHIPMENT ledger.
        await confirm_shipment(
            db,
            tenant_id=user.tenant_id,
            warehouse_id=doc.warehouse_id,
            user_id=user.id,
            document_id=document_id,
            product_id=prod_id,
            location_id=loc_id,
            qty=qty,
            marking_codes=codes,
        )

        # Group codes by product_unit_id for Smartup attach.
        order_line_id = item.get("order_line_id")
        pu_id = product_units.get(order_line_id or "", str(prod_id))
        existing = next((l for l in smartup_lines_list if l["product_unit_id"] == pu_id), None)
        if existing:
            existing["marking_codes"].extend(codes)
        else:
            smartup_lines_list.append({"product_unit_id": pu_id, "marking_codes": codes})

    # Enqueue Smartup integration via outbox (reliable, retried by worker).
    smartup_enqueued = False
    if deal_id:
        await outbox_svc.enqueue(
            db, tenant_id=user.tenant_id, connector="smartup",
            event_type="attach_marking_codes",
            payload={"deal_id": deal_id, "products": smartup_lines_list},
        )
        await outbox_svc.enqueue(
            db, tenant_id=user.tenant_id, connector="smartup",
            event_type="change_order_status",
            payload={"deal_id": deal_id, "status": "B#S"},
        )
        smartup_enqueued = True

    doc.status = DocumentStatus.COMPLETED
    if task.status != TaskStatus.COMPLETED:
        task.status = TaskStatus.COMPLETED
    await db.commit()

    return ShipmentConfirmResponse(
        document_id=document_id,
        status="completed",
        codes_attached=len(all_codes),
        smartup_enqueued=smartup_enqueued,
    )


# ── ERP'ga buyurtma statusini yuborish (rol asosida himoyalangan) ────────────
from pydantic import BaseModel as _BM  # noqa: E402
from app.services import erp_policy as _erp_pol  # noqa: E402


class OrderStatusPush(_BM):
    deal_id: str
    status: str


@router.post(
    "/order-status",
    dependencies=[require_permission("shipment", "create")],
)
async def push_order_status(body: OrderStatusPush, user: ActiveUser, db: DB):
    """Smartup'dagi REAL buyurtma statusini o'zgartiradi.

    Rol asosida: faqat `erp_write_roles` dagi rollar (Sozlamalardan sozlanadi)
    yoki superadmin yuborishi mumkin. Frontend yuborishdan oldin ogohlantiradi.
    """
    if user.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    allowed = await _erp_pol.get_erp_write_roles(db, user.tenant_id)
    if not _erp_pol.user_can_write_erp(user, allowed):
        raise HTTPException(
            status_code=403,
            detail="Sizning rolingizga ERP'ga yozish ruxsati yo'q (Sozlamalar → ERP-yozuv ruxsati).",
        )
    client = await get_smartup_client(db, user.tenant_id)
    ok = await client.change_order_status(body.deal_id, body.status)
    return {"deal_id": body.deal_id, "status": body.status, "success": bool(ok)}
