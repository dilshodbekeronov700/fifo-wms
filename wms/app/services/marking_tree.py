"""Asl Belgisi kod daraxtini talab bo'yicha qurish (Buxgalteriya Ocard `checkOwnerDeep`
pastga fazasi). Transport (SSCC) kod → box → unit ierarxiyasini owner-check BFS bilan
tortadi va MarkingCode(parent_code) qatorlari bo'lib saqlaydi → yacheyka panelida
daraxt ko'rinishida chiqadi.

Eslatma: skan paytida owner-check OLIB TASHLANGAN (mahalliy GTIN parse bilan ishlaydi).
Bu servis faqat foydalanuvchi "Kod daraxtini yuklash" tugmasini bosganda ishlaydi —
kvota tejaladi.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import MarkingCode, MarkingCodeStatus, PackageType


def _map_package(api_pkg: str | None, depth: int) -> PackageType:
    """API package_type'ni enum'ga; bo'lmasa chuqurlik bo'yicha taxmin."""
    if api_pkg:
        try:
            return PackageType(api_pkg)
        except ValueError:
            pass
    if depth <= 0:
        return PackageType.BOX_LV_1
    if depth == 1:
        return PackageType.GROUP
    return PackageType.UNIT


async def _find_root(aslbelgisi_client, code: str, max_up: int = 15) -> tuple[str, int]:
    """TEPAGA qidirish: kod parentini owner-check orqali topib, root'gacha ko'tariladi
    (Buxgalteriya Ocard `checkOwnerDeep` 1-fazasi). Yacheykadagi kod unit/box bo'lsa ham
    haqiqiy transport (root) topiladi."""
    current = code
    calls = 0
    seen: set[str] = set()
    while calls < max_up and current not in seen:
        seen.add(current)
        resp = await aslbelgisi_client.owner_check([current])
        calls += 1
        item = resp.by_code().get(current)
        parent = getattr(item, "parent", None) if item else None
        if not parent or parent in seen:
            break
        current = parent
    return current, calls


async def build_code_tree(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    root_code: str,
    location_id: uuid.UUID | None,
    aslbelgisi_client,
    max_depth: int = 6,
) -> dict:
    """Ikki tomonlama: TEPAGA (root topish) → PASTGA (BFS children) → MarkingCode daraxti.
    Kirish kodi unit/box/transport bo'lishidan qat'i nazar to'liq daraxt quriladi
    (Buxgalteriya Ocard `checkOwnerDeep` kabi). Idempotent upsert; har tugun location_id +
    mahalliy GTIN parse orqali mahsulotga bog'lanadi. package_type API'dan olinadi."""
    from app.services.putaway import _find_product_local, _parse_gtin_from_code

    # ── Faza 1: TEPAGA — haqiqiy root ────────────────────────────────────────
    true_root, up_calls = await _find_root(aslbelgisi_client, root_code)

    # Mavjud kodlarni bir marta yuklab olamiz (upsert uchun).
    existing = {
        mc.code: mc for mc in (await db.execute(
            select(MarkingCode).where(MarkingCode.tenant_id == tenant_id)
        )).scalars().all()
    }

    created = updated = 0
    api_calls = up_calls
    parent_of: dict[str, str | None] = {true_root: None}
    frontier = [true_root]
    seen: set[str] = {true_root}
    depth = 0

    # ── Faza 2: PASTGA — root'dan BFS ────────────────────────────────────────
    while frontier and depth < max_depth:
        resp = await aslbelgisi_client.owner_check(frontier)
        api_calls += 1
        by_code = resp.by_code()
        next_frontier: list[str] = []
        for code in frontier:
            oc = by_code.get(code)
            gtin = _parse_gtin_from_code(code)
            product = await _find_product_local(db, tenant_id=tenant_id, gtin=gtin) if gtin else None
            pkg = _map_package(getattr(oc, "package_type", None), depth)
            parent_code = parent_of.get(code)
            mc = existing.get(code)
            if mc is None:
                mc = MarkingCode(
                    tenant_id=tenant_id, code=code, gtin=gtin, package_type=pkg,
                    parent_code=parent_code, mc_status=MarkingCodeStatus.RECEIVED,
                    product_id=product.id if product else None, location_id=location_id,
                )
                db.add(mc)
                existing[code] = mc
                created += 1
            else:
                mc.parent_code = parent_code
                mc.package_type = pkg
                if location_id is not None:
                    mc.location_id = location_id
                if gtin and not mc.gtin:
                    mc.gtin = gtin
                if product and not mc.product_id:
                    mc.product_id = product.id
                updated += 1
            for ch in (getattr(oc, "children", []) or []):
                if ch not in seen:
                    seen.add(ch)
                    parent_of[ch] = code
                    next_frontier.append(ch)
        frontier = next_frontier
        depth += 1

    # ── Faza 3: 9.2 private_codes boyitish — GTIN + muddat + partiya + ishlab chiqarish
    # (Buxgalteriya Ocard 9.2). FEFO/to'liq ma'lumot uchun.
    enriched = 0
    all_codes = [c for c in seen]
    if all_codes:
        try:
            privs = await aslbelgisi_client.private_codes(all_codes)
            api_calls += 1
            by = {p.code: p for p in privs}
            for code in all_codes:
                mc = existing.get(code)
                p = by.get(code)
                if mc is None or p is None:
                    continue
                if p.gtin:
                    mc.gtin = p.gtin
                if p.expiry_date:
                    mc.expiry_date = p.expiry_date
                if getattr(p, "series_number", None):
                    mc.batch_number = p.series_number
                if p.production_date:
                    mc.production_date = p.production_date
                enriched += 1
        except Exception:
            pass  # 9.2 best-effort — ierarxiya baribir saqlanadi (kvota/xato jarayonni to'xtatmaydi)

    await db.commit()
    return {
        "created": created, "updated": updated, "enriched": enriched,
        "api_calls": api_calls, "depth": depth, "root": true_root, "up_levels": up_calls,
    }
