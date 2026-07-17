"""
Exception management (TZ §7.13).

GET   /exceptions               — list open/all exceptions (shift lead monitoring)
POST  /exceptions/{id}/assign   — assign to a user
POST  /exceptions/{id}/resolve  — resolve with a reason
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, get_db, require_permission
from app.models.exception import ExceptionEvent, ExceptionStatus

router = APIRouter(prefix="/exceptions", tags=["exceptions"])
DB = Annotated[AsyncSession, Depends(get_db)]


class ResolveBody(BaseModel):
    resolution: str


class AssignBody(BaseModel):
    assigned_to: uuid.UUID


@router.get("/", dependencies=[require_permission("exception", "view")])
async def list_exceptions(
    user: ActiveUser,
    db: DB,
    status: ExceptionStatus | None = ExceptionStatus.OPEN,
    warehouse_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
):
    q = select(ExceptionEvent).where(ExceptionEvent.tenant_id == user.tenant_id)
    if status:
        q = q.where(ExceptionEvent.status == status)
    if warehouse_id:
        q = q.where(ExceptionEvent.warehouse_id == warehouse_id)
    q = q.order_by(ExceptionEvent.created_at.desc()).limit(min(limit, 500)).offset(offset)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(e.id), "type": e.exc_type.value, "status": e.status.value,
            "severity": e.severity, "marking_code": e.marking_code,
            "message": e.message, "detail": e.detail,
            "assigned_to": str(e.assigned_to) if e.assigned_to else None,
            "created_at": e.created_at,
        }
        for e in rows
    ]


async def _get(db: AsyncSession, user, exc_id: uuid.UUID) -> ExceptionEvent:
    ev = (await db.execute(
        select(ExceptionEvent).where(
            ExceptionEvent.id == exc_id, ExceptionEvent.tenant_id == user.tenant_id
        )
    )).scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="Exception not found")
    return ev


@router.post("/{exc_id}/assign", dependencies=[require_permission("exception", "update")])
async def assign_exception(exc_id: uuid.UUID, body: AssignBody, user: ActiveUser, db: DB):
    ev = await _get(db, user, exc_id)
    ev.assigned_to = body.assigned_to
    ev.status = ExceptionStatus.ACK
    await db.commit()
    return {"id": str(ev.id), "status": ev.status.value, "assigned_to": str(ev.assigned_to)}


@router.post("/{exc_id}/resolve", dependencies=[require_permission("exception", "update")])
async def resolve_exception(exc_id: uuid.UUID, body: ResolveBody, user: ActiveUser, db: DB):
    ev = await _get(db, user, exc_id)
    ev.status = ExceptionStatus.RESOLVED
    ev.resolution = body.resolution
    await db.commit()
    return {"id": str(ev.id), "status": ev.status.value}
