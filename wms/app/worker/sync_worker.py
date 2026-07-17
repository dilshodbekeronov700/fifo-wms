"""
Avto-pull worker — Smartup'dan ma'lumotni JADVAL bo'yicha tortadi (kadensli).

Har bir oqim (flow) o'z intervaliga ega va Smartup limitlariga rioya qiladi
(References 100/kun, 7-kun oynasi). Faqat PULL (tortish) — WMS→Smartup push
operator tasdig'i bilan (outbox approval gate).

Oqimlar:
  - products        — mr/inventory$export        (References, kamdan-kam: 6 soat)
  - orders          — tdeal/order$export (B#W)   (tez-tez: 15 daqiqa, read-only snapshot)
  - inputs          — mkw/input$export           (30 daqiqa, read-only staging)
  - reconciliation  — mkw/balance$export svereka (60 daqiqa)
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.models.connector import ConnectorConfig

logger = logging.getLogger(__name__)

BASE_TICK = 60          # har 60s da due oqimlarni tekshiramiz
STARTUP_DELAY = 90      # ishga tushgach kutish (boshqa init tugasin)

# (flow nomi, interval soniya)
PULL_FLOWS: list[tuple[str, int]] = [
    ("orders",         15 * 60),
    ("inputs",         30 * 60),
    ("products",        6 * 3600),   # References 100/kun → kuniga bir necha marta
    ("reconciliation", 60 * 60),
]


def _due(settings: dict, flow: str, interval: int, now: datetime) -> bool:
    """Oxirgi ishga tushishdan beri interval o'tganmi?"""
    last = settings.get(f"last_{flow}_run_at")
    if not last:
        return True
    try:
        prev = datetime.fromisoformat(last)
    except ValueError:
        return True
    return (now - prev).total_seconds() >= interval


async def _run_flow(db, cfg, client, flow: str, sync_svc) -> dict:
    """Bitta oqimni bajaradi va snapshot/summary qaytaradi."""
    settings = dict(cfg.settings or {})
    begin = sync_svc.clamp_begin(settings.get(sync_svc.watermark_key(flow)))

    if flow == "products":
        # References: inkremental. Mavjud (eski) kalit "last_product_sync" (birlik).
        res = await sync_svc.sync_products(
            db, tenant_id=cfg.tenant_id, client=client,
            begin_modified_on=settings.get("last_product_sync"),
        )
        return {"fetched": res.fetched, "created": res.created, "updated": res.updated}

    if flow == "orders":
        return await sync_svc.sync_orders(
            db, tenant_id=cfg.tenant_id, client=client, begin_modified_on=begin)

    if flow == "inputs":
        return await sync_svc.sync_inputs(
            db, tenant_id=cfg.tenant_id, client=client, begin_modified_on=begin)

    if flow == "reconciliation":
        from app.services import reconciliation as rec_svc
        return await rec_svc.run_reconciliation_all_warehouses(
            db, tenant_id=cfg.tenant_id, smartup_client=client)

    raise ValueError(f"Noma'lum flow: {flow}")


async def pull_now(db, *, tenant_id, flows: list[str] | None = None) -> dict:
    """Bitta tenant uchun pull oqimlarini DARHOL bajaradi (vaqt jadvalisiz).

    Inson "Yangilash" tugmasini bosganda chaqiriladi — Smartup'dan ma'lumot
    avtomatik yuklanadi. Har oqim alohida commit qilinadi; bittasi xato bersa
    boshqalari davom etadi.
    """
    from app.core.connector_factory import get_smartup_client
    from app.services import sync as sync_svc

    flows = flows or [f for f, _ in PULL_FLOWS]
    cfg = (await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.tenant_id == tenant_id,
            ConnectorConfig.connector_type == "smartup",
            ConnectorConfig.is_active.is_(True),
        )
    )).scalar_one_or_none()
    if cfg is None:
        raise ValueError("Smartup connector sozlanmagan yoki faol emas")

    client = await get_smartup_client(db, tenant_id)
    results: dict[str, dict] = {}
    for flow in flows:
        try:
            snapshot = await _run_flow(db, cfg, client, flow, sync_svc)
            settings = dict(cfg.settings or {})
            settings[f"last_{flow}_run_at"] = sync_svc.now_ts()
            if flow == "products":
                settings["last_product_sync"] = sync_svc.now_iso()
            else:
                settings[sync_svc.watermark_key(flow)] = sync_svc.now_iso()
            if flow == "reconciliation":
                settings["last_reconciliation"] = snapshot
            else:
                settings[f"{flow}_snapshot"] = {**snapshot, "at": sync_svc.now_ts()}
            cfg.settings = settings
            await db.commit()
            results[flow] = {"ok": True, **(snapshot if isinstance(snapshot, dict) else {})}
        except Exception as exc:
            await db.rollback()
            results[flow] = {"ok": False, "error": str(exc)[:200]}
            logger.warning("pull_now tenant=%s flow=%s xato: %s", tenant_id, flow, exc)
    return results


async def _tick() -> None:
    from app.core.connector_factory import get_smartup_client
    from app.services import sync as sync_svc

    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        cfgs = (await db.execute(
            select(ConnectorConfig).where(
                ConnectorConfig.connector_type == "smartup",
                ConnectorConfig.is_active.is_(True),
            )
        )).scalars().all()

        for cfg in cfgs:
            client = None
            for flow, interval in PULL_FLOWS:
                settings = dict(cfg.settings or {})
                if not _due(settings, flow, interval, now):
                    continue
                try:
                    if client is None:
                        client = await get_smartup_client(db, cfg.tenant_id)
                    snapshot = await _run_flow(db, cfg, client, flow, sync_svc)
                    # Watermarklarni yangilaymiz (qayta o'qiymiz — _run_flow commit qilgan bo'lishi mumkin)
                    settings = dict(cfg.settings or {})
                    settings[f"last_{flow}_run_at"] = sync_svc.now_ts()
                    if flow == "products":
                        # Eski kalit (birlik) — panel/endpoint mosligi uchun.
                        settings["last_product_sync"] = sync_svc.now_iso()
                    else:
                        settings[sync_svc.watermark_key(flow)] = sync_svc.now_iso()
                    if flow == "reconciliation":
                        settings["last_reconciliation"] = snapshot
                    else:
                        settings[f"{flow}_snapshot"] = {**snapshot, "at": sync_svc.now_ts()}
                    cfg.settings = settings
                    await db.commit()
                    logger.info("Pull tenant=%s flow=%s: %s", cfg.tenant_id, flow, snapshot)
                except Exception as exc:  # bitta oqim/tenant xatosi qolganini to'xtatmasin
                    await db.rollback()
                    logger.warning("Pull tenant=%s flow=%s xato: %s", cfg.tenant_id, flow, exc)


async def run_sync_worker() -> None:
    logger.info("Avto-pull worker ishga tushdi (tick=%ss, flows=%s)",
                BASE_TICK, [f for f, _ in PULL_FLOWS])
    await asyncio.sleep(STARTUP_DELAY)
    while True:
        try:
            await _tick()
        except Exception:
            logger.exception("Avto-pull worker iteratsiyasi xato berdi")
        await asyncio.sleep(BASE_TICK)
