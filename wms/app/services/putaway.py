"""
Putaway service — scan a pallet/transport code and propose the optimal slot.

Flow (TZ §7.2–7.3):
  1. TSD scans a transport code (SSCC / BOX_LV / aggregate).
  2. Asl Belgisi `owner-check` → ownership + immediate nested children.
  3. `private/codes` → GTIN, expiry, production date (owner-check does NOT carry these).
  4. Resolve Product (by GTIN) + Batch (by expiry); compute box / unit counts.
  5. Directed slotting → ranked candidate locations.

`resolve_scanned_code` is shared with the receipt flow so code resolution lives
in exactly one place.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.aslbelgisi import AslBelgisiClient
from app.models.inventory import (
    Batch, BatchStatus, MarkingCode, MarkingCodeStatus, Product, StockItem,
)
from app.models.ledger import LedgerAction
from app.models.reservation import PutawayReservation, ReservationStatus
from app.models.warehouse import Location, LocationStatus, Zone
from app.services import ledger as ledger_svc
from app.services import slotting as slotting_svc

# How long a reservation is held before it auto-expires (capacity released).
RESERVATION_TTL_MINUTES = 120

# Package types that represent a pallet / transport-level aggregate.
_TRANSPORT_TYPES = {"BOX_LV_1", "BOX_LV_2", "ACC", "SET"}


@dataclass
class ResolvedCode:
    code: str
    ownership_ok: bool
    reason: str | None = None              # set when ownership_ok is False
    package_type: str | None = None
    product_group_id: int | None = None
    issuer_tin: str | None = None
    # quantities
    box_count: int = 0                     # GROUP-level packages
    unit_count: int = 0                    # UNIT-level bottles
    counting_method: str = "unknown"       # children | master | second_level
    # resolved entities
    gtin: str | None = None
    expiry_date: str | None = None
    production_date: str | None = None
    product: Product | None = None
    batch: Batch | None = None
    children: list[str] = field(default_factory=list)


@dataclass
class SlotCandidate:
    location_id: uuid.UUID
    location_code: str
    zone_id: uuid.UUID
    zone_type: str
    score: float
    reason: str
    factors: dict[str, float] = field(default_factory=dict)
    remaining_boxes: int = 0


@dataclass
class PutawaySuggestion:
    resolved: ResolvedCode
    candidates: list[SlotCandidate]
    suggested: SlotCandidate | None


async def _lookup_product(
    db: AsyncSession, *, tenant_id: uuid.UUID, gtin: str | None,
    client: AslBelgisiClient,
) -> Product | None:
    """GTIN bo'yicha WMS Product; topilmasa Asl Belgisi registr'idan yaratadi.

    MUHIM: registr GTIN'ni bilmasa (None qaytarsa) — soxta yozuv YARATILMAYDI.
    Bu box/transport GTIN (registrda yo'q daraja) uchun bolalarga tushishga imkon beradi.
    """
    if not gtin:
        return None
    product = (await db.execute(
        select(Product).where(Product.tenant_id == tenant_id, Product.gtin == gtin)
    )).scalar_one_or_none()
    if product is not None:
        return product
    # WMS'da yo'q — registr'da bormi?
    try:
        info = await client.product_by_gtin(gtin)
    except Exception:
        info = None
    if info is None:
        return None  # bu GTIN registrda yo'q (ehtimol noto'g'ri qadoq darajasi)
    nm = info.get("productName") or {}
    if isinstance(nm, str):
        nm = {"uz": nm, "ru": nm}
    product = Product(
        tenant_id=tenant_id, gtin=gtin, uom="unit",
        name={
            "uz": nm.get("uz") or nm.get("ru") or nm.get("en") or gtin,
            "ru": nm.get("ru") or nm.get("uz") or "",
        },
    )
    db.add(product)
    await db.flush()
    return product


def _parse_gtin_from_code(code: str) -> str | None:
    """GS1 DataMatrix kodidan GTIN (AI '01' → 14 raqam) ni MAHALLIY ajratadi.

    Misol: '0134780094510087217u%..' → '34780094510087'. API kerak emas.
    """
    if not code:
        return None
    s = code.strip()
    # Skaner qo'shgan symbology identifier (]d2, ]C1, ]Q3 ...) ni olib tashlaymiz
    if s.startswith("]") and len(s) >= 3:
        s = s[3:]
    # GS1: AI 01 (GTIN) sobit uzunlik — 14 raqam
    if s.startswith("01") and len(s) >= 16 and s[2:16].isdigit():
        return s[2:16]
    return None


async def _find_product_local(
    db: AsyncSession, *, tenant_id: uuid.UUID, gtin: str | None
) -> Product | None:
    """GTIN bo'yicha WMS mahsulotini topadi — API chaqirmasdan.

    Avval aniq moslik; bo'lmasa qadoq darajasidan qat'i nazar (GTIN-14 ning
    o'rta 12 raqami — savdo birligi — bir xil bo'lsa). Shunday qilib GROUP/BOX
    kodi UNIT mahsulot bilan mos keladi (indikator + nazorat raqami farq qilsa ham).
    """
    if not gtin:
        return None
    p = (await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id, Product.gtin == gtin,
            Product.is_active.is_(True),
        )
    )).scalars().first()
    if p:
        return p
    if len(gtin) == 14 and gtin.isdigit():
        middle = gtin[1:13]  # indikator (0) va nazorat raqamisiz (13) savdo birligi
        p = (await db.execute(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.is_active.is_(True),
                Product.gtin.like(f"_{middle}_"),
            )
        )).scalars().first()
        if p:
            return p
    return None


async def _resolve_via_local_tree(
    db: AsyncSession, *, tenant_id: uuid.UUID, code: str, max_depth: int = 4
) -> tuple[Product | None, list[str]]:
    """Transport/agregat (SSCC) kodni MAHALLIY MarkingCode daraxti orqali hal qiladi.

    Transport kod (00…) ICHIDA GTIN yo'q — uni faqat bolalar (box 01…) orqali topish
    mumkin. Avval bu bolalar owner-check API'dan olinardi; API 429/ishlamasa transport
    kod umuman ishlamasdi. Bu funksiya kirim (receipt) vaqtida `store_marking_tree`
    saqlagan agregatsiya daraxtidan foydalanadi — API'siz, 429'ga bog'liq emas:
        SSCC (00…) → bola box kodlar (01…) → product_id / GTIN → Product.

    Returns: (product, bevosita_bolalar_kodlari)  — bolalar box_count uchun.
    """
    if not code:
        return None, []
    # Kodning o'zi daraxtda bormi — product_id to'g'ridan-to'g'ri biriktirilgan bo'lishi mumkin
    root = (await db.execute(
        select(MarkingCode).where(
            MarkingCode.tenant_id == tenant_id, MarkingCode.code == code
        )
    )).scalar_one_or_none()
    # Bevosita bolalar (box soni — count uchun)
    direct_children = list((await db.execute(
        select(MarkingCode.code).where(
            MarkingCode.tenant_id == tenant_id, MarkingCode.parent_code == code
        )
    )).scalars().all())

    async def _product_from_mc(mc: MarkingCode) -> Product | None:
        if mc.product_id is not None:
            p = await db.get(Product, mc.product_id)
            if p is not None and p.is_active:
                return p
        return await _find_product_local(
            db, tenant_id=tenant_id, gtin=mc.gtin or _parse_gtin_from_code(mc.code)
        )

    if root is not None:
        p = await _product_from_mc(root)
        if p is not None:
            return p, direct_children

    # Daraxt bo'ylab pastga tushib (box → unit) mos mahsulotni qidiramiz
    level = list(direct_children)
    seen: set[str] = set()
    depth = 0
    while level and depth < max_depth:
        rows = (await db.execute(
            select(MarkingCode).where(
                MarkingCode.tenant_id == tenant_id, MarkingCode.code.in_(level)
            )
        )).scalars().all()
        for mc in rows:
            p = await _product_from_mc(mc)
            if p is not None:
                return p, direct_children
        seen.update(level)
        next_level = list((await db.execute(
            select(MarkingCode.code).where(
                MarkingCode.tenant_id == tenant_id, MarkingCode.parent_code.in_(level)
            )
        )).scalars().all())
        level = [c for c in next_level if c not in seen]
        depth += 1

    return None, direct_children


async def resolve_scanned_code(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    code: str,
    client: AslBelgisiClient,
    tin: str,
    deep_count: bool = True,
) -> ResolvedCode:
    """Skanlangan kodni ResolvedCode ga aylantiradi — OWNER-CHECK UMUMAN ISHLATILMAYDI.

    Zavoddagi barcha kodlar bizniki — egalik tekshirish (owner-check) shart emas va
    butunlay olib tashlandi (429/sekinlik yo'q). Mahsulot faqat MAHALLIY topiladi:
      1) Kod ichidagi GTIN (GS1 AI 01) — mahalliy parse → Product (qadoq darajasidan
         qat'i nazar: GTIN-14 ning o'rta 12 raqami bo'yicha box↔unit mos keladi).
      2) Transport SSCC (00…, ichida GTIN yo'q) — kirimda saqlangan MarkingCode
         agregatsiya daraxti orqali (API'siz).
    private/codes faqat amal qilish muddati (FIFO partiya) uchun best-effort
    chaqiriladi; ishlamasa ham jarayon to'xtamaydi.
    """
    local_gtin = _parse_gtin_from_code(code)
    resolved = ResolvedCode(
        code=code,
        ownership_ok=True,        # ← hech qachon blok qilmaymiz
        reason=None,
        package_type=None,
        product_group_id=None,
        issuer_tin=None,
        children=[],
        gtin=local_gtin,
    )

    # ── Amal qilish muddati (FIFO) — best-effort, OWNER-CHECK EMAS ────────────
    try:
        details = await client.private_codes([code])
        if details:
            d = details[0]
            resolved.gtin = d.gtin or resolved.gtin
            resolved.expiry_date = d.expiry_date
            resolved.production_date = d.production_date
    except Exception:
        pass  # API ishlamasa ham — mahalliy GTIN bilan davom etamiz

    # ── Mahsulot: 1) mahalliy GTIN (box/unit) ────────────────────────────────
    product = await _find_product_local(db, tenant_id=tenant_id, gtin=resolved.gtin)
    # ── 2) Transport SSCC: mahalliy agregatsiya daraxti (API'siz) ────────────
    if product is None:
        product, local_children = await _resolve_via_local_tree(
            db, tenant_id=tenant_id, code=code
        )
        if local_children:
            resolved.children = local_children  # box sonini mahalliy beramiz
    resolved.product = product

    # ── Resolve / create Batch by expiry ─────────────────────────────────────
    if resolved.product and resolved.expiry_date:
        resolved.batch = await _get_or_create_batch(
            db, product_id=resolved.product.id, expiry_date=resolved.expiry_date
        )

    # ── Compute box / unit counts (MAHALLIY — API'siz) ───────────────────────
    _compute_counts(resolved)
    return resolved


def _compute_counts(resolved: ResolvedCode) -> None:
    """Box/dona sonini MAHALLIY hisoblaydi — owner-check chaqirmasdan.

    package_type endi owner-check'dan kelmaydi (None). Bitta qadoq (box) deb
    hisoblaymiz; transport SSCC uchun mahalliy daraxtdagi bolalar soni = box soni.
    Pallet deb taxmin qilinmaydi (aks holda capacity noto'g'ri → location_full).
    """
    product = resolved.product
    children = resolved.children
    upb = product.units_per_box if product else None
    resolved.box_count = len(children) or 1
    resolved.unit_count = (upb * resolved.box_count) if upb else (len(children) or upb or 1)
    resolved.counting_method = "children" if children else "assumed_single"


async def _get_or_create_batch(
    db: AsyncSession, *, product_id: uuid.UUID, expiry_date: str
) -> Batch:
    res = await db.execute(
        select(Batch).where(
            Batch.product_id == product_id,
            Batch.expiry_date == expiry_date,
            Batch.status == BatchStatus.AVAILABLE,
        )
    )
    existing = res.scalar_one_or_none()
    if existing:
        return existing
    batch = Batch(product_id=product_id, expiry_date=expiry_date)
    db.add(batch)
    await db.flush()
    return batch


async def scan_and_suggest(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    code: str,
    client: AslBelgisiClient,
    tin: str,
    top_n: int = 5,
) -> PutawaySuggestion:
    """Full scan → MAHALLIY resolve → directed slotting (owner-check YO'Q)."""
    resolved = await resolve_scanned_code(
        db, tenant_id=tenant_id, code=code, client=client, tin=tin
    )

    # Owner-check butunlay olib tashlandi — agregatsiya daraxti kirim (Kirim) vaqtida
    # TSD yuborgan ma'lumotdan saqlanadi; bu yerda API chaqirilmaydi.
    # GTIN bo'yicha mahsulot/bo'sh joy taklif qilinadi.
    candidates: list[SlotCandidate] = []

    if resolved.product is not None:
        # ── Mahsulot topildi: to'liq slotting (ABC, FIFO, capacity, harorat) ──
        product = resolved.product
        raw = await slotting_svc.suggest_locations(
            db,
            warehouse_id=warehouse_id,
            product=product,
            batch_id=resolved.batch.id if resolved.batch else None,
            expiry_date=resolved.expiry_date,
            qty=resolved.box_count or 1,
            unit_count=resolved.unit_count or 0,
            top_n=top_n,
        )
        candidates = [
            SlotCandidate(
                location_id=c.location.id,
                location_code=c.location.code,
                zone_id=c.zone.id,
                zone_type=c.zone.zone_type.value,
                score=c.score,
                reason=c.reason,
                factors=c.factors,
                remaining_boxes=c.remaining_boxes,
            )
            for c in raw
        ]
    else:
        # ── Mahsulot aniqlanmadi (registrda yo'q / sync qilinmagan):
        #    Slotting qoidalarsiz, faqat bo'sh lokatsiyalarni qaytaramiz.
        #    Operator qo'lda tanlaydi — yacheyka qidirish ishlaydi.
        locs = await search_locations(
            db, warehouse_id=warehouse_id,
            product_id=None, batch_id=None,
            qty=resolved.box_count or 1,
            query=None, limit=top_n,
        )
        candidates = [
            SlotCandidate(
                location_id=loc.location_id,
                location_code=loc.code,
                zone_id=loc.zone_id,
                zone_type=loc.zone_type,
                score=0.0,
                reason="product_unknown",
                factors={},
                remaining_boxes=loc.remaining_boxes,
            )
            for loc in locs if loc.can_place
        ]

    return PutawaySuggestion(
        resolved=resolved,
        candidates=candidates,
        suggested=candidates[0] if candidates else None,
    )


# ─── Reservation (bron) → confirm-by-scan flow ───────────────────────────────

class PutawayError(Exception):
    """Operator-facing putaway failure (mapped to HTTP 409/404 in the endpoint)."""


async def _remaining_boxes(
    db: AsyncSession, *, warehouse_id: uuid.UUID, location: Location,
    product: Product, batch_id: uuid.UUID | None,
) -> tuple[int, bool]:
    """Free box capacity of a slot (capacity − stock − pending reservations) and
    whether it currently holds only the same product+batch (mixing check)."""
    occupied = (await db.execute(
        select(func.coalesce(func.sum(StockItem.qty), 0))
        .where(StockItem.location_id == location.id)
    )).scalar_one()
    reserved = (await db.execute(
        select(func.coalesce(func.sum(PutawayReservation.qty), 0))
        .where(
            PutawayReservation.location_id == location.id,
            PutawayReservation.status == ReservationStatus.PENDING,
        )
    )).scalar_one()
    items = (await db.execute(
        select(StockItem).where(StockItem.location_id == location.id)
    )).scalars().all()
    same_only = all(
        s.product_id == product.id and (batch_id is None or s.batch_id == batch_id)
        for s in items
    )
    cap = slotting_svc._capacity_boxes(location, product)
    return cap - int(occupied) - int(reserved), same_only


async def expire_stale_reservations(db: AsyncSession, *, warehouse_id: uuid.UUID) -> int:
    """Mark overdue PENDING reservations EXPIRED so their capacity is released."""
    now = datetime.now(timezone.utc)
    rows = (await db.execute(
        select(PutawayReservation).where(
            PutawayReservation.warehouse_id == warehouse_id,
            PutawayReservation.status == ReservationStatus.PENDING,
            PutawayReservation.expires_at.is_not(None),
            PutawayReservation.expires_at < now,
        )
    )).scalars().all()
    for r in rows:
        r.status = ReservationStatus.EXPIRED
    return len(rows)


async def expire_all_stale_reservations(db: AsyncSession) -> int:
    """Barcha ijaralar (tenant/ombor) bo'yicha muddati o'tgan PENDING bronlarni
    EXPIRED qiladi — fon workeri uchun. `expire_stale_reservations` faqat kimdir
    o'sha omborda reserve/qidiruv qilganda ishlaydi; bu esa vaqt bo'yicha,
    hech kim tegmasa ham, egallangan sig'imni bo'shatadi.

    Har bir bronni EXPIRED belgilaydi va SSE orqali e'lon qiladi (map jonli
    yangilanadi). Yozilgan bronlar sonini qaytaradi.
    """
    now = datetime.now(timezone.utc)
    rows = (await db.execute(
        select(PutawayReservation).where(
            PutawayReservation.status == ReservationStatus.PENDING,
            PutawayReservation.expires_at.is_not(None),
            PutawayReservation.expires_at < now,
        )
    )).scalars().all()
    for r in rows:
        r.status = ReservationStatus.EXPIRED
        _publish_reservation(r.tenant_id, r, "expired")
    return len(rows)


async def reserve_slot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    code: str,
    location_id: uuid.UUID,
    product_id: uuid.UUID | None,
    batch_id: uuid.UUID | None,
    qty: int,
    unit_count: int,
    package_type: str | None,
    score: float | None,
    reason: str | None,
    manual: bool,
    force: bool = False,
    payload: dict,
    user_id: uuid.UUID | None,
) -> PutawayReservation:
    """Hold a slot for a scanned code. Does NOT move stock — that happens on confirm.

    force=True: operator majburlab joylashtiradi (capacity/mixing chekini o'tkazib yuboradi).
    BLOCKED joylarga force ham ta'sir qilmaydi — bu inventar yaxlitligini saqlaydi.
    """
    await expire_stale_reservations(db, warehouse_id=warehouse_id)

    location = await db.get(Location, location_id)
    if location is None or not location.is_active:
        raise PutawayError("location_not_found")
    zone = await db.get(Zone, location.zone_id)
    if zone is None or zone.warehouse_id != warehouse_id:
        raise PutawayError("location_not_found")
    if location.status == LocationStatus.BLOCKED:
        raise PutawayError("location_blocked")

    product: Product | None = None
    if product_id is not None:
        product = await db.get(Product, product_id)
        if product is None:
            raise PutawayError("product_not_found")

    if product is not None:
        remaining, same_only = await _remaining_boxes(
            db, warehouse_id=warehouse_id, location=location,
            product=product, batch_id=batch_id,
        )
        if not force and remaining < max(1, qty):
            raise PutawayError("location_full")
        if not force and not zone.allow_mixed and not same_only:
            raise PutawayError("mixing_not_allowed")

    # Guard against reserving the same code twice while one is still pending.
    dup = (await db.execute(
        select(PutawayReservation).where(
            PutawayReservation.code == code,
            PutawayReservation.status == ReservationStatus.PENDING,
        )
    )).scalar_one_or_none()
    if dup is not None:
        raise PutawayError("already_reserved")

    res = PutawayReservation(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        code=code,
        package_type=package_type,
        product_id=product_id,
        batch_id=batch_id,
        qty=max(1, qty),
        unit_count=unit_count,
        location_id=location_id,
        zone_id=zone.id,
        score=score,
        reason=reason,
        manual=manual,
        status=ReservationStatus.PENDING,
        payload=payload or {},
        reserved_by=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=RESERVATION_TTL_MINUTES),
    )
    db.add(res)
    await db.flush()
    _publish_reservation(tenant_id, res, "reserved")
    return res


async def confirm_putaway(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    reservation_id: uuid.UUID,
    scanned_location: str,
    user_id: uuid.UUID | None,
) -> PutawayReservation:
    """Operator physically scanned the slot's QR/DataMatrix → place the stock.

    Validates the scanned barcode matches the reserved location, then writes the
    PUTAWAY ledger entry, updates stock + location status, stamps the marking
    code's location, and marks the reservation CONFIRMED.
    """
    res = await db.get(PutawayReservation, reservation_id)
    if res is None or res.tenant_id != tenant_id:
        raise PutawayError("reservation_not_found")
    if res.status != ReservationStatus.PENDING:
        raise PutawayError(f"reservation_{res.status.value}")

    location = await db.get(Location, res.location_id)
    if location is None:
        raise PutawayError("location_not_found")

    # Skanlangan slot. Bron qilingan joyga TENG bo'lsa — o'sha. AKS HOLDA operator
    # ISTALGAN boshqa yacheykani skanlagan → shu ombordagi o'sha yacheykaga QAYTA
    # YO'NALTIRAMIZ (faol + bloklanmagan bo'lsa). "Qaysi yacheyka skanlansa — shunga
    # joylash" — qo'lda qidiruv kerak emas.
    scan = (scanned_location or "").strip()
    expected = {location.barcode, location.code, str(location.id)}
    if scan not in {e for e in expected if e}:
        target = (await db.execute(
            select(Location).join(Zone, Zone.id == Location.zone_id).where(
                Zone.warehouse_id == res.warehouse_id,
                Location.is_active.is_(True),
                (Location.barcode == scan) | (Location.code == scan),
            )
        )).scalars().first()
        if target is None:
            raise PutawayError("location_not_found")
        if target.status == LocationStatus.BLOCKED:
            raise PutawayError("location_blocked")
        res.location_id = target.id
        res.zone_id = target.zone_id
        location = target

    # Immutable ledger write (also updates StockItem cache + publishes SSE).
    await ledger_svc.record(
        db,
        tenant_id=tenant_id,
        warehouse_id=res.warehouse_id,
        action=LedgerAction.PUTAWAY,
        qty_delta=res.qty,
        product_id=res.product_id,
        batch_id=res.batch_id,
        marking_code=res.code,
        to_location_id=res.location_id,
        user_id=user_id,
        reason="putaway_confirm",
        extra={"reservation_id": str(res.id), "unit_count": res.unit_count,
               "package_type": res.package_type, "manual": res.manual},
    )

    # Butun agregatsiya daraxtini (res.code + barcha avlodlari) yacheykaga biriktiramiz.
    # Daraxt scan paytida MarkingCode (parent_code) bo'lib saqlangan → BFS bilan yig'amiz.
    tree_codes: list[str] = [res.code]
    frontier: list[str] = [res.code]
    while frontier:
        kids = (await db.execute(
            select(MarkingCode.code).where(
                MarkingCode.tenant_id == tenant_id,
                MarkingCode.parent_code.in_(frontier),
            )
        )).scalars().all()
        new = [k for k in kids if k not in tree_codes]
        if not new:
            break
        tree_codes.extend(new)
        frontier = new
    # payload children (eski oqim bilan moslik uchun) ham qo'shamiz
    for ch in (res.payload or {}).get("children") or []:
        if ch not in tree_codes:
            tree_codes.append(ch)
    await db.execute(
        MarkingCode.__table__.update()
        .where(MarkingCode.tenant_id == tenant_id, MarkingCode.code.in_(tree_codes))
        .values(location_id=res.location_id, mc_status=MarkingCodeStatus.RECEIVED)
    )

    # Yacheyka statusi: 1 yacheyka = max_pallets pallet joyi. Har tasdiqlangan
    # putaway = 1 pallet. Joylangan pallet soni >= max_pallets bo'lsa — BAND,
    # aks holda (qisman to'lgan) QISMAN. (Qutidagi sig'im emas — pallet joyi.)
    maxp = location.max_pallets or 1
    placed = int((await db.execute(
        select(func.count()).select_from(PutawayReservation).where(
            PutawayReservation.location_id == location.id,
            PutawayReservation.status == ReservationStatus.CONFIRMED,
        )
    )).scalar_one()) + 1  # +1 = hozir tasdiqlanayotgan bron
    location.status = LocationStatus.OCCUPIED if placed >= maxp else LocationStatus.PARTIAL

    res.status = ReservationStatus.CONFIRMED
    res.confirmed_by = user_id
    res.confirmed_at = datetime.now(timezone.utc)
    await db.flush()
    _publish_reservation(tenant_id, res, "confirmed")
    return res


async def cancel_reservation(
    db: AsyncSession, *, tenant_id: uuid.UUID, reservation_id: uuid.UUID,
) -> PutawayReservation:
    res = await db.get(PutawayReservation, reservation_id)
    if res is None or res.tenant_id != tenant_id:
        raise PutawayError("reservation_not_found")
    if res.status != ReservationStatus.PENDING:
        raise PutawayError(f"reservation_{res.status.value}")
    res.status = ReservationStatus.CANCELLED
    await db.flush()
    _publish_reservation(tenant_id, res, "cancelled")
    return res


@dataclass
class LocationOption:
    location_id: uuid.UUID
    code: str
    barcode: str | None
    zone_id: uuid.UUID
    zone_type: str
    status: str
    remaining_boxes: int
    can_place: bool
    note: str | None = None


async def search_locations(
    db: AsyncSession,
    *,
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID | None,
    batch_id: uuid.UUID | None,
    qty: int,
    query: str | None,
    limit: int = 25,
) -> list[LocationOption]:
    """Manual location lookup for the operator override (free-text on code/barcode)."""
    await expire_stale_reservations(db, warehouse_id=warehouse_id)
    stmt = (
        select(Location, Zone)
        .join(Zone, Zone.id == Location.zone_id)
        .where(Zone.warehouse_id == warehouse_id, Location.is_active.is_(True))
    )
    if query:
        like = f"%{query.strip().upper()}%"
        stmt = stmt.where(
            func.upper(Location.code).like(like) | func.upper(func.coalesce(Location.barcode, "")).like(like)
        )
    rows = (await db.execute(stmt.limit(limit))).all()

    product = await db.get(Product, product_id) if product_id else None
    out: list[LocationOption] = []
    for loc, zone in rows:
        remaining, same_only = (0, True)
        if product is not None:
            remaining, same_only = await _remaining_boxes(
                db, warehouse_id=warehouse_id, location=loc,
                product=product, batch_id=batch_id,
            )
        else:
            # Mahsulot noma'lum → bo'sh joyni max_pallets bilan taxminlaymiz
            remaining = loc.max_pallets or 1

        note = None
        can = True
        if loc.status == LocationStatus.BLOCKED:
            can, note = False, "bloklangan"
        elif product is not None and remaining < max(1, qty):
            can, note = False, "joy yetarli emas"
        elif product is not None and not zone.allow_mixed and not same_only:
            can, note = False, "aralashtirish taqiqlangan"
        out.append(LocationOption(
            location_id=loc.id, code=loc.code, barcode=loc.barcode,
            zone_id=zone.id, zone_type=zone.zone_type.value,
            status=loc.status.value, remaining_boxes=max(0, remaining),
            can_place=can, note=note,
        ))
    # Placeable first, then by free capacity.
    out.sort(key=lambda o: (not o.can_place, -o.remaining_boxes))
    return out


def _publish_reservation(tenant_id: uuid.UUID, res: PutawayReservation, event: str) -> None:
    """Best-effort SSE so the map/manager view updates live (never breaks the write)."""
    try:
        from app.core.events import bus
        bus.publish(str(tenant_id), {
            "type": "reservation",
            "event": event,
            "reservation_id": str(res.id),
            "location_id": str(res.location_id),
            "code": res.code,
            "status": res.status.value,
        })
    except Exception:
        pass
