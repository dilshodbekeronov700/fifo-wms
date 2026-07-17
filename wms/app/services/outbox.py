"""
Outbox pattern — reliable, idempotent delivery for connector calls.

A business operation enqueues an OutboxMessage in the SAME transaction as its
ledger write; a background worker delivers it with exponential backoff. For Asl
Belgisi async documents, delivery returns a documentId which is then polled
(stage 2) until SUCCESS/ERROR.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import OutboxMessage, OutboxStatus

MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 30

# WMS-manbali stock TUZATISHLARI — operator panelda tasdiqlamaguncha YUBORILMAYDI.
# (Boshqa eventlar — change_order_status, attach_marking_codes, disaggregation,
#  aggregation — avtomatik yuboriladi: operator allaqachon harakat qilgan.)
APPROVAL_REQUIRED_EVENTS = {
    "writeoff", "stocktaking", "movement", "mfm_movement", "supplier_return",
}

# Tasdiq kutayotgan xabar uchun sentinel: next_retry_at uzoq kelajakka qo'yiladi,
# shunda get_due (next_retry_at <= now) uni hech qachon olmaydi — schema o'zgarmaydi.
APPROVAL_HOLD = datetime(9999, 1, 1, tzinfo=timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def enqueue(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    connector: str,       # "smartup" | "aslbelgisi"
    event_type: str,
    payload: dict[str, Any],
) -> OutboxMessage:
    # Tasdiq talab qiladigan event? → hold qilamiz (panelda Approve bosilmaguncha).
    requires_approval = event_type in APPROVAL_REQUIRED_EVENTS
    if requires_approval:
        payload = {**payload, "_awaiting_approval": True}
    msg = OutboxMessage(
        tenant_id=tenant_id,
        connector=connector,
        event_type=event_type,
        payload=payload,
        status=OutboxStatus.PENDING,
        attempts=0,
        next_retry_at=APPROVAL_HOLD if requires_approval else _now(),
    )
    db.add(msg)
    return msg


async def list_pending_approval(
    db: AsyncSession, *, tenant_id: uuid.UUID, connector: str = "smartup"
) -> list[OutboxMessage]:
    """Tasdiq kutayotgan push xabarlari (operator navbati)."""
    q = (
        select(OutboxMessage)
        .where(
            OutboxMessage.tenant_id == tenant_id,
            OutboxMessage.connector == connector,
            OutboxMessage.status == OutboxStatus.PENDING,
            OutboxMessage.next_retry_at == APPROVAL_HOLD,
        )
        .order_by(OutboxMessage.created_at)
    )
    return list((await db.execute(q)).scalars())


async def _get_held(
    db: AsyncSession, *, msg_id: uuid.UUID, tenant_id: uuid.UUID
) -> OutboxMessage | None:
    msg = await db.get(OutboxMessage, msg_id)
    if (
        msg is None
        or msg.tenant_id != tenant_id
        or msg.status != OutboxStatus.PENDING
        or msg.next_retry_at != APPROVAL_HOLD
    ):
        return None
    return msg


async def approve(
    db: AsyncSession, *, msg_id: uuid.UUID, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> OutboxMessage | None:
    """Tasdiqlash → darhol yuboriladigan holatga (next_retry_at=now)."""
    msg = await _get_held(db, msg_id=msg_id, tenant_id=tenant_id)
    if msg is None:
        return None
    p = dict(msg.payload or {})
    p.pop("_awaiting_approval", None)
    p["_approved_by"] = str(user_id)
    p["_approved_at"] = _now().isoformat()
    msg.payload = p                 # JSON o'zgarishi aniqlanishi uchun qayta tayinlash
    msg.next_retry_at = _now()
    return msg


async def reject(
    db: AsyncSession, *, msg_id: uuid.UUID, tenant_id: uuid.UUID,
    user_id: uuid.UUID, reason: str,
) -> OutboxMessage | None:
    """Rad etish → FAILED (qayta urinmaydi, yuborilmaydi)."""
    msg = await _get_held(db, msg_id=msg_id, tenant_id=tenant_id)
    if msg is None:
        return None
    p = dict(msg.payload or {})
    p.pop("_awaiting_approval", None)
    p["_rejected"] = True
    p["_rejected_by"] = str(user_id)
    msg.payload = p
    msg.status = OutboxStatus.FAILED
    msg.last_error = f"Operator rad etdi: {(reason or '').strip()[:500]}"
    return msg


async def get_due(
    db: AsyncSession, connector: str | None = None, limit: int = 50
) -> list[OutboxMessage]:
    """Fetch PENDING messages whose next_retry_at has passed, locking rows so
    multiple worker instances don't double-send (FOR UPDATE SKIP LOCKED)."""
    q = (
        select(OutboxMessage)
        .where(
            OutboxMessage.status == OutboxStatus.PENDING,
            (OutboxMessage.next_retry_at.is_(None)) | (OutboxMessage.next_retry_at <= _now()),
        )
        .order_by(OutboxMessage.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    if connector:
        q = q.where(OutboxMessage.connector == connector)
    result = await db.execute(q)
    return list(result.scalars())


def mark_sent(msg: OutboxMessage, *, result_doc_id: str | None = None) -> None:
    msg.attempts += 1
    if result_doc_id:
        # Async doc — keep PENDING-equivalent in a polling state via result fields.
        msg.result_doc_id = result_doc_id
        msg.status = OutboxStatus.SENT
    else:
        msg.status = OutboxStatus.SENT
    msg.last_error = None


def mark_failed(msg: OutboxMessage, error: str) -> None:
    msg.attempts += 1
    msg.last_error = error[:1000]
    if msg.attempts >= MAX_ATTEMPTS:
        msg.status = OutboxStatus.FAILED
    else:
        # Exponential backoff: 30s, 60s, 120s, 240s …
        delay = BACKOFF_BASE_SECONDS * (2 ** (msg.attempts - 1))
        msg.next_retry_at = _now() + timedelta(seconds=delay)
