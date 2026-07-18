"""
Reconciliation engine — WMS Ledger ↔ ERP (Smartup) inventory balance.

Computes WMS on-hand per (product, batch) by summing immutable LedgerEntry
deltas for a warehouse, then optionally compares against Smartup's reported
inventory balance and (optionally) cross-checks owned marking codes via
Asl Belgisi.

Entry point (imported by app/api/v1/endpoints/operations.py):

    async def run_reconciliation(
        db, *, tenant_id, warehouse_id,
        smartup_client=None, aslbelgisi_client=None,
    ) -> dict

The returned dict is fully JSON-serialisable.

This module performs NO network or DB access at import time.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import Product, Batch, MarkingCode, MarkingCodeStatus
from app.models.warehouse import Warehouse
from app.models.ledger import LedgerEntry


def _friendly_erp_error(exc: Exception) -> str:
    """Smartup balance$export xatolarini tushunarli o'zbekcha xabarga aylantiradi.

    Asosiy sabab odatda Smartup tomonidagi TASHKILOT sozlamasi (integratsiya bitta
    aniq filialiga biriktirilmagan / filial kodi bo'sh) — bu WMS bug'i emas.
    """
    msg = str(exc)
    table = {
        "A02-24-070": "Smartup tashkilot kodini talab qilyapti, lekin joriy filialning kodi bo'sh. "
                      "Smartup'da integratsiyani bitta aniq tashkilotga (filial_code bilan) biriktiring.",
        "A02-24-048": "Yuborilgan filial_code joriy Smartup tashkilotiga mos emas. "
                      "Sozlamalar → Smartup → filial_code'ni joriy tashkilotga to'g'rilang.",
        "A02-24-042": "Bunday filial_code Smartup'da topilmadi. To'g'ri tashkilot kodini kiriting.",
        "A02-24-012": "Skladning Smartup kodi joriy tashkilotda topilmadi. Sklad kodini to'g'rilang.",
    }
    for code, friendly in table.items():
        if code in msg:
            return f"{friendly} (Smartup: {code})"
    # Tarmoq / boshqa xatolar
    if "SmartupApiError" in type(exc).__name__ or "Smartup" in msg:
        return f"Smartup bilan bog'lanishda xatolik: {msg[:140]}"
    return f"{type(exc).__name__}: {msg[:140]}"


class DiffDirection(str, Enum):
    """Per-line outcome of comparing WMS on-hand to ERP balance."""
    MATCH = "match"           # wms_qty == smartup_qty (both present, equal)
    WMS_MORE = "wms_more"     # WMS has more than ERP
    ERP_MORE = "erp_more"     # ERP has more than WMS
    MISSING = "missing"       # present in exactly one system (or no ERP data)


# Smartup balance lookups are reported per product code (smartup_product_code),
# not per batch, so WMS quantities are aggregated to product level before
# comparing against the ERP. Batch-level detail is still surfaced in the report.


def _classify(wms_qty: int, erp_qty: int, *, have_erp: bool) -> DiffDirection:
    """Decide the direction for a compared line."""
    if not have_erp:
        # No ERP figure to compare against -> WMS-only view.
        return DiffDirection.MISSING
    if wms_qty == erp_qty:
        return DiffDirection.MATCH
    if wms_qty > erp_qty:
        return DiffDirection.WMS_MORE
    return DiffDirection.ERP_MORE


async def _wms_onhand_by_product_batch(
    db: AsyncSession,
    *,
    warehouse_id: uuid.UUID,
) -> dict[tuple[uuid.UUID | None, uuid.UUID | None], int]:
    """Sum ledger qty_delta grouped by (product_id, batch_id) for a warehouse."""
    result = await db.execute(
        select(
            LedgerEntry.product_id,
            LedgerEntry.batch_id,
            func.coalesce(func.sum(LedgerEntry.qty_delta), 0).label("qty"),
        )
        .where(LedgerEntry.warehouse_id == warehouse_id)
        .group_by(LedgerEntry.product_id, LedgerEntry.batch_id)
    )
    return {
        (row.product_id, row.batch_id): int(row.qty or 0)
        for row in result.all()
    }


def _product_name(prod) -> str | None:
    """WMS Product.name (dict {uz, ru}) → ko'rsatish uchun bitta string."""
    if prod is None:
        return None
    n = prod.name
    if isinstance(n, dict):
        return n.get("uz") or n.get("ru") or next(iter(n.values()), None)
    return n or None


async def _smartup_balance_by_code(
    smartup_client,
    *,
    warehouse_code: str,
    names: dict[str, str] | None = None,
) -> dict[str, int]:
    """Fetch Smartup inventory balance and key it by product code.

    Smartup `mkw/balance$export` qatorlari maydonlari:
      product_code  — mahsulot kodi (WMS.smartup_product_code bilan mos)
      quantity      — qoldiq miqdori
      warehouse_id / warehouse_code / batch_number / expiry_date ...
    Smartup skladlarida `warehouse_code` ko'pincha null — shuning uchun
    filial bo'yicha BARCHA qoldiqni so'raymiz (warehouse filtrsiz) va
    product_code bo'yicha yig'amiz.
    """
    # Balance — JORIY KUN snapshot'i (begin=end=today). Smartup oynasi cheklangan
    # (~30 kun; keng oyna 0 qaytaradi), bir kun esa shu kungi qoldiqni beradi.
    today = datetime.now(timezone.utc).date()
    begin_date = today.strftime("%d.%m.%Y")
    end_date = today.strftime("%d.%m.%Y")

    # Haqiqiy sklad kodi bo'lsa filtrlaymiz; aks holda (null/placeholder/"*") — hammasi.
    wh_codes = [warehouse_code] if (warehouse_code and warehouse_code not in ("001wrh", "", "*")) else []

    rows = await smartup_client.get_inventory_balance(
        warehouse_codes=wh_codes,
        begin_date=begin_date,
        end_date=end_date,
    )
    balance: dict[str, int] = {}
    for item in rows or []:
        code = str(item.get("product_code", "") or "").strip()
        if not code:
            continue
        try:
            qty = int(float(item.get("quantity", 0) or 0))
        except (TypeError, ValueError):
            qty = 0
        balance[code] = balance.get(code, 0) + qty
        if names is not None and code not in names:
            nm = item.get("product_name") or item.get("product_unit_name")
            if nm:
                names[code] = str(nm)
    return balance


async def run_reconciliation(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    smartup_client=None,
    aslbelgisi_client=None,
    smartup_warehouse_code: str | None = None,
) -> dict:
    """Run a stock reconciliation for one warehouse.

    Returns a JSON-serialisable report. When ``smartup_client`` is None the
    report is a WMS-only view (every line marked ``missing``, all counted as
    ``only_wms`` in the summary).

    ``smartup_warehouse_code`` is accepted for backward-compatibility with older
    callers but is optional: when omitted the warehouse's configured code is
    looked up from the DB.
    """
    generated_at = datetime.now(timezone.utc).isoformat()

    # ── 1. WMS on-hand per (product, batch) from the ledger ──────────────────
    wms_onhand = await _wms_onhand_by_product_batch(db, warehouse_id=warehouse_id)

    # Collect referenced product / batch ids for label resolution.
    product_ids = {p for (p, _b) in wms_onhand if p is not None}
    batch_ids = {b for (_p, b) in wms_onhand if b is not None}

    products: dict[uuid.UUID, Product] = {}
    if product_ids:
        res = await db.execute(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.id.in_(list(product_ids)),
            )
        )
        products = {p.id: p for p in res.scalars()}

    batches: dict[uuid.UUID, Batch] = {}
    if batch_ids:
        res = await db.execute(
            select(Batch).where(Batch.id.in_(list(batch_ids)))
        )
        batches = {b.id: b for b in res.scalars()}

    # WMS quantity aggregated per smartup product code (for ERP comparison).
    wms_qty_by_code: dict[str, int] = {}
    for (prod_id, _batch_id), qty in wms_onhand.items():
        prod = products.get(prod_id) if prod_id else None
        code = (prod.smartup_product_code or "") if prod else ""
        if code:
            wms_qty_by_code[code] = wms_qty_by_code.get(code, 0) + qty

    # ── 2. Smartup balance (optional) ────────────────────────────────────────
    smartup_by_code: dict[str, int] = {}
    smartup_name_by_code: dict[str, str] = {}
    have_erp = False
    erp_error: str | None = None

    if smartup_client is not None:
        if not smartup_warehouse_code:
            wh = await db.get(Warehouse, warehouse_id)
            smartup_warehouse_code = wh.smartup_warehouse_code if wh else None
        if smartup_warehouse_code:
            try:
                smartup_by_code = await _smartup_balance_by_code(
                    smartup_client, warehouse_code=smartup_warehouse_code,
                    names=smartup_name_by_code,
                )
                have_erp = True
            except Exception as exc:  # network/ERP failure -> degrade gracefully
                erp_error = _friendly_erp_error(exc)
        else:
            erp_error = "Skladga Smartup kodi biriktirilmagan (Sozlamalar → sklad)."

    # ── 3. Build per (product, batch) report lines ───────────────────────────
    lines: list[dict] = []
    summary = {"match": 0, "mismatch": 0, "only_wms": 0, "only_erp": 0}

    # ERP balance is per product code; attribute it to the line(s) by code.
    # To avoid double-counting, the ERP qty is shown against the aggregated WMS
    # qty for that code on the first batch line, and as remainder thereafter.
    # We keep it simple and report ERP qty per code on a product-level basis:
    # each batch line shows wms_qty (its own) and the code's total erp_qty so a
    # reviewer can reconcile; direction uses the product-code aggregates.
    seen_codes: set[str] = set()

    for (prod_id, batch_id), wms_qty in sorted(
        wms_onhand.items(),
        key=lambda kv: (str(kv[0][0]), str(kv[0][1])),
    ):
        prod = products.get(prod_id) if prod_id else None
        code = (prod.smartup_product_code or "") if prod else ""
        batch = batches.get(batch_id) if batch_id else None
        batch_label = None
        if batch is not None:
            batch_label = batch.lot_number or batch.expiry_date or str(batch.id)

        if have_erp and code:
            # Compare at product-code granularity using aggregated WMS qty.
            agg_wms = wms_qty_by_code.get(code, 0)
            erp_qty = smartup_by_code.get(code, 0)
            direction = _classify(agg_wms, erp_qty, have_erp=True)
            line_erp_qty = erp_qty
            line_diff = agg_wms - erp_qty
        else:
            line_erp_qty = 0
            line_diff = wms_qty
            direction = DiffDirection.MISSING

        lines.append({
            "product_id": str(prod_id) if prod_id else None,
            "product_code": code or None,
            "product_name": _product_name(prod) or (smartup_name_by_code.get(code) if code else None),
            "batch": batch_label,
            "wms_qty": wms_qty,
            "smartup_qty": line_erp_qty if (have_erp and code) else None,
            "diff": line_diff,
            "direction": direction.value,
        })

        if code:
            seen_codes.add(code)

    # ── 4. ERP codes with no WMS stock (only_erp) ────────────────────────────
    if have_erp:
        # Map known codes -> product for labelling ERP-only rows.
        all_products: dict[str, Product] = {}
        res = await db.execute(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.smartup_product_code.isnot(None),
            )
        )
        for p in res.scalars():
            if p.smartup_product_code:
                all_products[p.smartup_product_code] = p

        for code, erp_qty in sorted(smartup_by_code.items()):
            if code in wms_qty_by_code:
                continue  # already represented by a WMS line
            p = all_products.get(code)
            lines.append({
                "product_id": str(p.id) if p else None,
                "product_code": code,
                "product_name": _product_name(p) or smartup_name_by_code.get(code),
                "batch": None,
                "wms_qty": 0,
                "smartup_qty": erp_qty,
                "diff": -erp_qty,
                "direction": DiffDirection.ERP_MORE.value,
            })

    # ── 5. Summary (counted at product-code granularity) ─────────────────────
    if have_erp:
        all_codes = set(wms_qty_by_code) | set(smartup_by_code)
        for code in all_codes:
            w = wms_qty_by_code.get(code)
            e = smartup_by_code.get(code)
            if w is not None and e is None:
                summary["only_wms"] += 1
            elif w is None and e is not None:
                summary["only_erp"] += 1
            elif w == e:
                summary["match"] += 1
            else:
                summary["mismatch"] += 1
    else:
        # WMS-only view: every distinct product code counts as only_wms.
        summary["only_wms"] = len({
            (prod.smartup_product_code or str(pid))
            for (pid, _b) in wms_onhand
            for prod in [products.get(pid)]
        })

    # ── Umumiy ko'lichestvo + nomenklatura (foydalanuvchi so'rovi) ───────────
    totals = {
        "wms_total_units": int(sum(wms_qty_by_code.values())),
        "wms_nomenclature": len([c for c, q in wms_qty_by_code.items() if q]),
        "smartup_total_units": int(sum(smartup_by_code.values())) if have_erp else None,
        "smartup_nomenclature": len([c for c, q in smartup_by_code.items() if q]) if have_erp else None,
    }

    report: dict = {
        "generated_at": generated_at,
        "warehouse_id": str(warehouse_id),
        "smartup_warehouse_code": smartup_warehouse_code,
        "erp_compared": have_erp,
        "lines": lines,
        "summary": summary,
        "totals": totals,
    }
    if erp_error:
        report["erp_error"] = erp_error

    # ── 6. Optional Asl Belgisi owned-codes cross-check ──────────────────────
    if aslbelgisi_client is not None:
        try:
            res = await db.execute(
                select(func.count(MarkingCode.id)).where(
                    MarkingCode.tenant_id == tenant_id,
                    MarkingCode.mc_status.in_([
                        MarkingCodeStatus.RECEIVED,
                        MarkingCodeStatus.APPLIED,
                        MarkingCodeStatus.INTRODUCED,
                    ]),
                )
            )
            report["marking_codes_on_hand"] = int(res.scalar_one() or 0)
        except Exception as exc:  # never fail the whole report on a side-check
            report["aslbelgisi_error"] = f"{type(exc).__name__}: {exc}"

    return report


async def run_reconciliation_all_warehouses(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    smartup_client=None,
) -> dict:
    """Tenant'ning BARCHA faol skladlari uchun svereka — worker/panel uchun.

    Har sklad bo'yicha summary qaytaradi (lines'siz, yengil). Panelda
    `last_reconciliation` sifatida saqlash uchun mo'ljallangan.
    """
    whs = (await db.execute(
        select(Warehouse).where(
            Warehouse.tenant_id == tenant_id,
            Warehouse.is_active.is_(True),
        )
    )).scalars().all()

    warehouses: list[dict] = []
    totals = {"match": 0, "mismatch": 0, "only_wms": 0, "only_erp": 0}
    for wh in whs:
        rep = await run_reconciliation(
            db, tenant_id=tenant_id, warehouse_id=wh.id, smartup_client=smartup_client,
        )
        s = rep.get("summary", {})
        for k in totals:
            totals[k] += int(s.get(k, 0) or 0)
        warehouses.append({
            "warehouse_id": str(wh.id),
            "warehouse_name": wh.name,
            "erp_compared": rep.get("erp_compared", False),
            "summary": s,
            "erp_error": rep.get("erp_error"),
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": totals,
        "warehouses": warehouses,
    }
