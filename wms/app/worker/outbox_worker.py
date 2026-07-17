"""
OutboxMessage delivery worker.

Stage 1: deliver PENDING messages (backoff via outbox service). Asl Belgisi
document sends return a documentId stored on the message.
Stage 2: for messages with a documentId still in flight, poll the document
status (SUCCESS/WARNING/ERROR) and finalise.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.health import heartbeat
from app.db.base import AsyncSessionLocal
from app.models.inventory import OutboxMessage, OutboxStatus
from app.services import outbox as outbox_svc

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds

# event types whose delivery returns an Asl Belgisi documentId to poll
_ASYNC_DOC_EVENTS = {"aggregation", "disaggregation"}


async def _deliver(db: AsyncSession, msg: OutboxMessage) -> None:
    try:
        if msg.connector == "smartup":
            await _dispatch_smartup(db, msg)
            outbox_svc.mark_sent(msg)
        elif msg.connector == "aslbelgisi":
            doc_id = await _dispatch_aslbelgisi(db, msg)
            outbox_svc.mark_sent(msg, result_doc_id=doc_id)
        else:
            logger.warning("Unknown connector in outbox: %s", msg.connector)
            outbox_svc.mark_failed(msg, f"unknown connector {msg.connector}")
        await db.commit()
    except Exception as exc:
        outbox_svc.mark_failed(msg, str(exc))
        await db.commit()
        logger.warning("Outbox %s failed (attempt %s): %s", msg.id, msg.attempts, exc)


async def _dispatch_smartup(db: AsyncSession, msg: OutboxMessage) -> None:
    from app.core.connector_factory import get_smartup_client

    client = await get_smartup_client(db, msg.tenant_id)
    # Approval gate meta kalitlarini (_awaiting_approval, _approved_by, …) Smartup'ga
    # YUBORMAYMIZ — faqat haqiqiy hujjat maydonlarini qoldiramiz.
    p = {k: v for k, v in (msg.payload or {}).items() if not k.startswith("_")}
    if msg.event_type == "attach_marking_codes":
        await client.attach_marking_codes(p["deal_id"], p["products"])
    elif msg.event_type == "change_order_status":
        await client.change_order_status(p["deal_id"], p["status"])
    elif msg.event_type == "stocktaking":
        await client.post_stocktaking(p)
    elif msg.event_type == "writeoff":
        await client.post_writeoff(p)
    elif msg.event_type == "movement":
        await client.post_movement(p)
    elif msg.event_type == "mfm_movement":
        await client.post_cross_org_movement(p)
    elif msg.event_type == "mfm_movement_status":
        await client.change_cross_org_movement_status(p["movement_id"], p["status"])
    elif msg.event_type == "supplier_return":
        await client.post_supplier_return(p)
    else:
        raise ValueError(f"Unknown smartup event_type: {msg.event_type}")


async def _dispatch_aslbelgisi(db: AsyncSession, msg: OutboxMessage) -> str | None:
    from app.core.connector_factory import get_aslbelgisi_client

    client = await get_aslbelgisi_client(db, msg.tenant_id)
    p = msg.payload
    if msg.event_type == "disaggregation":
        return await client.send_disaggregation(p)
    if msg.event_type == "aggregation":
        return await client.send_aggregation(p)
    raise ValueError(f"Unknown aslbelgisi event_type: {msg.event_type}")


async def _poll_async_docs(db: AsyncSession) -> None:
    """Stage 2 — poll Asl Belgisi document results that are still in flight."""
    from app.core.connector_factory import get_aslbelgisi_client

    rows = (await db.execute(
        select(OutboxMessage).where(
            OutboxMessage.status == OutboxStatus.SENT,
            OutboxMessage.result_doc_id.is_not(None),
            OutboxMessage.result_status.is_(None),
            OutboxMessage.connector == "aslbelgisi",
        ).limit(50)
    )).scalars().all()

    for msg in rows:
        try:
            client = await get_aslbelgisi_client(db, msg.tenant_id)
            doc = await client.get_doc(msg.result_doc_id)
            status = (doc.get("status") or doc.get("documentInfos", {}).get("status"))
            if status in ("SUCCESS", "ERROR", "WARNING"):
                msg.result_status = status
                if status == "ERROR":
                    msg.last_error = "document processing ERROR"
            await db.commit()
        except Exception as exc:
            logger.warning("Doc poll failed for %s: %s", msg.result_doc_id, exc)


async def run_outbox_worker() -> None:
    logger.info("Outbox worker started (poll_interval=%ss)", POLL_INTERVAL)
    while True:
        heartbeat("outbox")
        try:
            async with AsyncSessionLocal() as db:
                due = await outbox_svc.get_due(db, limit=50)
                for msg in due:
                    await _deliver(db, msg)
            async with AsyncSessionLocal() as db:
                await _poll_async_docs(db)
        except Exception as exc:
            logger.error("Outbox worker iteration error: %s", exc)
        await asyncio.sleep(POLL_INTERVAL)
