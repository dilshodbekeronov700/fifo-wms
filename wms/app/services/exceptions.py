"""Exception logging/escalation helper (TZ §7.13)."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exception import ExceptionEvent, ExceptionType


async def record(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    exc_type: ExceptionType,
    warehouse_id: uuid.UUID | None = None,
    marking_code: str | None = None,
    message: str | None = None,
    severity: int = 50,
    created_by: uuid.UUID | None = None,
    detail: dict[str, Any] | None = None,
) -> ExceptionEvent:
    ev = ExceptionEvent(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        exc_type=exc_type,
        marking_code=marking_code,
        message=message,
        severity=severity,
        created_by=created_by,
        detail=detail or {},
    )
    db.add(ev)
    return ev
