"""
Master-data synchronisation.

Pulls SKUs from Smartup `mr/inventory$export` and upserts WMS Products. The
last sync watermark is stored on the connector's settings so subsequent runs are
incremental (begin_modified_on). Optionally enriches via Asl Belgisi GTIN lookup.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.smartup import SmartupClient
from app.models.inventory import Product

if TYPE_CHECKING:
    from app.connectors.aslbelgisi import AslBelgisiClient


@dataclass
class SyncResult:
    fetched: int
    created: int
    updated: int


def _name_dict(raw: dict) -> dict:
    name = raw.get("name") or raw.get("short_name") or ""
    return {"ru": name, "uz": name}


def _category_from_litr(raw: dict) -> str | None:
    litr = raw.get("litr")
    if litr in (None, "", "0"):
        return None
    try:
        val = float(str(litr).replace(",", "."))
    except ValueError:
        return str(litr)
    return f"{val:g}L"


async def sync_products(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client: SmartupClient,
    begin_modified_on: str | None = None,
) -> SyncResult:
    rows = await client.get_product_references(begin_modified_on=begin_modified_on)
    created = updated = 0

    for raw in rows:
        code = str(raw.get("code") or "").strip()
        if not code:
            continue

        existing = (await db.execute(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.smartup_product_code == code,
            )
        )).scalar_one_or_none()

        gtin = (str(raw.get("gtin")).strip() or None) if raw.get("gtin") else None
        # Smartup'da bitta GTIN'ga bir nechta inventar kodi bo'lishi mumkin
        # (masalan "<gtin>_1"). WMS'da esa (tenant, gtin) faol mahsulot bo'yicha
        # UNIKAL. Kod bo'yicha topilmasa — GTIN bo'yicha qaraymiz; aks holda yangi
        # qator dublikat GTIN bilan `uq_product_tenant_gtin_active` ni buzadi.
        if existing is None and gtin:
            existing = (await db.execute(
                select(Product).where(
                    Product.tenant_id == tenant_id,
                    Product.gtin == gtin,
                    Product.is_active.is_(True),
                )
            )).scalar_one_or_none()
            # GTIN bo'yicha topilsa-yu, hali smartup kodi bo'lmasa — shu kodni biriktiramiz.
            if existing is not None and not existing.smartup_product_code:
                existing.smartup_product_code = code

        box_quant = raw.get("box_quant")
        units_per_box = int(box_quant) if box_quant not in (None, "", "0") else None
        weight = raw.get("weight_netto") or raw.get("weight_brutto")
        try:
            weight_kg = float(str(weight).replace(",", ".")) if weight else None
        except ValueError:
            weight_kg = None

        if existing is None:
            db.add(Product(
                tenant_id=tenant_id,
                smartup_product_code=code,
                gtin=gtin,
                name=_name_dict(raw),
                uom=raw.get("measure_code") or "unit",
                units_per_box=units_per_box,
                category=_category_from_litr(raw),
                weight_kg=weight_kg,
                is_active=(raw.get("state") != "P"),  # 'P' often = passive
            ))
            created += 1
        else:
            # GTIN'ni faqat bo'sh bo'lsa to'ldiramiz — mavjudini boshqa kodning
            # GTIN'iga almashtirsak yana unikal-konstraint buziladi.
            if gtin and not existing.gtin:
                existing.gtin = gtin
            existing.name = _name_dict(raw) if raw.get("name") else existing.name
            if units_per_box:
                existing.units_per_box = units_per_box
            cat = _category_from_litr(raw)
            if cat:
                existing.category = cat
            if weight_kg is not None:
                existing.weight_kg = weight_kg
            updated += 1

    await db.commit()
    return SyncResult(fetched=len(rows), created=created, updated=updated)


async def sync_aslbelgisi_products(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client: "AslBelgisiClient",
) -> dict:
    """Asl Belgisi product-registry dan mahsulotlarni guruh bo'yicha WMS'ga yozadi."""
    synced = created = updated = 0
    errors: list[str] = []

    for group in client.PRODUCT_GROUPS:
        try:
            items = await client.list_products(group)
        except Exception as e:
            errors.append(f"{group}: {e}")
            continue

        for it in items:
            gtin = (it.get("gtin") or "").strip()
            if not gtin:
                continue

            name_raw = it.get("productName") or {}
            if isinstance(name_raw, str):
                name_raw = {"uz": name_raw, "ru": name_raw}
            name_json = {
                "uz": name_raw.get("uz") or name_raw.get("ru") or name_raw.get("en") or gtin,
                "ru": name_raw.get("ru") or name_raw.get("uz") or "",
            }

            existing = (await db.execute(
                select(Product).where(
                    Product.tenant_id == tenant_id,
                    Product.gtin == gtin,
                )
            )).scalar_one_or_none()

            if existing is None:
                db.add(Product(
                    tenant_id=tenant_id,
                    gtin=gtin,
                    name=name_json,
                    category=group,
                    uom="unit",
                ))
                created += 1
            else:
                existing.name = name_json
                existing.category = group
                updated += 1
            synced += 1

    await db.flush()
    return {"synced": synced, "created": created, "updated": updated, "errors": errors}


def now_iso() -> str:
    """Smartup sana formati (dd.mm.yyyy) — begin_modified_on va panel ko'rsatkichi."""
    return datetime.now(timezone.utc).strftime("%d.%m.%Y")


def now_ts() -> str:
    """To'liq ISO timestamp — worker kadensi uchun (last_<flow>_run_at)."""
    return datetime.now(timezone.utc).isoformat()


def watermark_key(flow: str) -> str:
    """Per-flow sana watermark kaliti (panel + begin_modified_on)."""
    return f"last_{flow}_sync"


def clamp_begin(last_sync_ddmmyyyy: str | None, *, window_days: int = 7) -> str:
    """begin_modified_on ni Smartup 7-kun oynasiga clamp qiladi.

    Smartup eski sanani qabul qilmaydi (oyna ~7 kun). Watermark yo'q yoki juda
    eski bo'lsa — bugun minus window_days dan boshlaymiz.
    """
    floor = datetime.now(timezone.utc).date() - timedelta(days=window_days)
    if last_sync_ddmmyyyy:
        try:
            d = datetime.strptime(last_sync_ddmmyyyy, "%d.%m.%Y").date()
            return max(d, floor).strftime("%d.%m.%Y")
        except ValueError:
            pass
    return floor.strftime("%d.%m.%Y")


async def sync_orders(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client: SmartupClient,
    begin_modified_on: str | None = None,
) -> dict:
    """Smartup'dan ochiq (terilishi kerak) buyurtmalarni tortadi (read-only snapshot).

    Jismoniy terish vazifasi (stock band qiladi) operator tomonidan
    /shipment/pick-task orqali yaratiladi — bu yerda faqat ko'rinish uchun
    snapshot olamiz (avto-pull, lekin avto-allokatsiya YO'Q).

    Status kodlari (order$export + Smartup UI bilan tasdiqlangan 2026-07-18):
    `B#N`=Новый (yangi, teriladi), `B#V`=jarayonda (teriladi), `B#S`=Отгружен,
    `C`=Доставлен, `D`=qoralama, `A`=ARXIV (Smartup faol ro'yxatda ko'rsatmaydi).
    Ochiq (terilishi kerak) ish = B#N + B#V. (Ilgari xato `A` qo'shilgani uchun
    snapshot ~749 gacha shishardi — A=638 arxiv edi.)
    """
    orders = await client.get_orders(
        statuses=["B#N", "B#V"], begin_modified_on=begin_modified_on
    )
    return {
        "fetched": len(orders),
        "deal_ids": [o.deal_id for o in orders][:200],
    }


async def sync_inputs(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client: SmartupClient,
    begin_modified_on: str | None = None,
) -> dict:
    """Smartup zavod kirimlarini tortadi (read-only staging).

    Jismoniy kirim baribir TSD skani orqali (process_receipt) tasdiqlanadi;
    bu yerda kutilayotgan kirimlar ko'rinishi uchun snapshot olamiz.
    """
    inputs = await client.get_inputs(begin_modified_on=begin_modified_on)
    return {"fetched": len(inputs)}
