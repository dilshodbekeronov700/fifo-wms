"""Real-time updates via Server-Sent Events (TZ §5.1).

Exposes ``GET /realtime/stream`` which streams JSON events for the current
user's tenant off the in-process :data:`app.core.events.bus`. Because the
browser ``EventSource`` API cannot set request headers, this endpoint accepts
the access token either via the standard ``Authorization: Bearer`` header
(``ActiveUser``) or, as a fallback, a ``?token=`` query parameter.
"""
from __future__ import annotations

import asyncio
import json
from typing import Annotated, AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.events import bus
from app.core.security import decode_token
from app.db.base import get_db
from app.models.auth import Role, User

router = APIRouter(prefix="/realtime", tags=["realtime"])

DB = Annotated[AsyncSession, Depends(get_db)]

# Seconds between heartbeat comments to keep proxies/connections alive.
HEARTBEAT_SECONDS = 15.0


async def _resolve_user(
    db: AsyncSession,
    request: Request,
    token: str | None,
) -> User:
    """Resolve the current user from the Authorization header or ?token= query.

    EventSource cannot send custom headers, so a query-param token is accepted
    as a fallback. Mirrors :func:`app.core.deps.get_current_user`.
    """
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    raw = token
    if raw is None:
        auth = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            raw = auth[7:]
    if not raw:
        raise exc

    try:
        payload = decode_token(raw)
    except JWTError:
        raise exc

    if payload.get("type") != "access":
        raise exc

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise exc

    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == UUID(user_id), User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise exc
    return user


@router.get("/stream")
async def stream(
    request: Request,
    db: DB,
    token: str | None = None,
) -> StreamingResponse:
    """SSE stream of tenant-scoped events. Heartbeats every ~15s; cleans up on
    disconnect."""
    user = await _resolve_user(db, request, token)
    if user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User has no tenant context"
        )

    tenant_id = str(user.tenant_id)
    queue = bus.subscribe(tenant_id)

    async def event_gen() -> AsyncIterator[str]:
        try:
            # Initial comment opens the stream promptly for the client.
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except asyncio.TimeoutError:
                    # Heartbeat comment (ignored by EventSource onmessage).
                    yield ": ping\n\n"
                    continue
                yield f"data: {json.dumps(event, default=str)}\n\n"
        finally:
            bus.unsubscribe(tenant_id, queue)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
