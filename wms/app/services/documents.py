"""
Smartup import-body builders for Phase 5 operations.

These helpers translate WMS internal documents (movement, inventory count,
write-off) into the JSON shapes that the Smartup ERP `mkw/*$import` endpoints
expect. They resolve WMS product_id/batch_id/location_id into Smartup codes
(smartup_product_code, smartup_warehouse_code) so the worker / connector can
post them verbatim.

Conventions (per smartup_integration memory):
  - Dates: dd.mm.yyyy
  - Idempotency: external_id == the WMS Document id
  - Inventory count: stocktaking uses balance_quantity (expected) vs quantity (counted)
  - Movement: warehouse_code (from) -> warehouse_code (to) at warehouse granularity
  - Writeoff: writeoff_items with reason_code

The builders never touch the DB session beyond reads; the endpoint layer commits.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import Product
from app.models.warehouse import Warehouse


def _today() -> str:
    return date.today().strftime("%d.%m.%Y")


async def _product_code_map(
    db: AsyncSession, product_ids: set[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """Resolve WMS product ids -> Smartup product codes (falls back to the id)."""
    if not product_ids:
        return {}
    result = await db.execute(
        select(Product.id, Product.smartup_product_code).where(Product.id.in_(product_ids))
    )
    return {pid: (code or str(pid)) for pid, code in result.all()}


async def _warehouse_code(db: AsyncSession, warehouse_id: uuid.UUID) -> str:
    wh = await db.get(Warehouse, warehouse_id)
    if wh and wh.smartup_warehouse_code:
        return wh.smartup_warehouse_code
    return str(warehouse_id)


# Sklad uchun haqiqiy Smartup kodi yo'q bo'lsa — bu "placeholder"lar filtr SIFATIDA
# ishlatilmaydi (aks holda Smartup 0 qaytaradi). None → filial bo'yicha hammasi.
# "*" — tashkilot skladining Smartup kodi null (kod bilan filtrlab bo'lmaydi);
# butun filial qoldig'ini olamiz, lekin svereka SOLISHTIRISHI bajariladi.
PLACEHOLDER_WAREHOUSE_CODES = {"", "001wrh", "*"}


def warehouse_filter(smartup_warehouse_code: str | None) -> list[str] | None:
    """Smartup so'rovlari uchun warehouse_codes filtri.

    Haqiqiy kod bo'lsa [code], placeholder/bo'sh bo'lsa None (filial bo'yicha
    BARCHA ma'lumot) — shunda Chiqim/Kirim sahifalari bo'sh ko'rinmaydi.
    """
    if smartup_warehouse_code and smartup_warehouse_code not in PLACEHOLDER_WAREHOUSE_CODES:
        return [smartup_warehouse_code]
    return None


# ─── Movement (mkw/movement$import) ──────────────────────────────────────────

async def build_movement_body(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    lines: list[dict],
    reason: str | None = None,
) -> dict:
    """Build a Smartup internal-movement import body.

    `lines` items: {"product_id": UUID, "qty": int, "marking_codes": [..]}.
    Movement in Smartup is warehouse->warehouse; intra-warehouse cell moves are
    reported with the same warehouse_code on both sides (informational sync).
    """
    product_ids = {line["product_id"] for line in lines}
    codes = await _product_code_map(db, product_ids)
    wh_code = await _warehouse_code(db, warehouse_id)

    items = [
        {
            "product_code": codes.get(line["product_id"], str(line["product_id"])),
            "quantity": line["qty"],
            "marking_codes": (line.get("marking_codes") or [])[:50],
        }
        for line in lines
    ]
    return {
        "movement": [
            {
                "external_id": str(document_id),
                "movement_date": _today(),
                "from_warehouse_code": wh_code,
                "to_warehouse_code": wh_code,
                "notes": reason or "",
                "movement_items": items,
            }
        ]
    }


# ─── Inventory count / stocktaking (mkw/stocktaking$import) ───────────────────

async def build_stocktaking_body(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    lines: list[dict],
) -> dict:
    """Build a Smartup stocktaking import body.

    `lines` items: {"product_id": UUID, "expected_qty": int, "counted_qty": int,
                    "marking_codes": [..]}.
    Smartup expects balance_quantity (system/expected) vs quantity (counted).
    """
    product_ids = {line["product_id"] for line in lines}
    codes = await _product_code_map(db, product_ids)
    wh_code = await _warehouse_code(db, warehouse_id)

    items = [
        {
            "product_code": codes.get(line["product_id"], str(line["product_id"])),
            "balance_quantity": line["expected_qty"],
            "quantity": line["counted_qty"],
            "marking_codes": (line.get("marking_codes") or [])[:50],
        }
        for line in lines
    ]
    return {
        "stocktaking": [
            {
                "external_id": str(document_id),
                "stocktaking_date": _today(),
                "warehouse_code": wh_code,
                "stocktaking_items": items,
            }
        ]
    }


# ─── Write-off (mkw/writeoff$import) ─────────────────────────────────────────

async def build_writeoff_body(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    lines: list[dict],
    notes: str | None = None,
) -> dict:
    """Build a Smartup write-off import body.

    `lines` items: {"product_id": UUID, "qty": int, "reason_code": str,
                    "marking_codes": [..]}.
    """
    product_ids = {line["product_id"] for line in lines}
    codes = await _product_code_map(db, product_ids)
    wh_code = await _warehouse_code(db, warehouse_id)

    items = [
        {
            "product_code": codes.get(line["product_id"], str(line["product_id"])),
            "quantity": line["qty"],
            "reason_code": line["reason_code"],
            "marking_codes": (line.get("marking_codes") or [])[:50],
        }
        for line in lines
    ]
    return {
        "writeoff": [
            {
                "external_id": str(document_id),
                "writeoff_date": _today(),
                "warehouse_code": wh_code,
                "notes": notes or "",
                "writeoff_items": items,
            }
        ]
    }
