"""In-process async pub/sub event bus for real-time SSE fan-out (TZ §5.1).

A single module-level :data:`bus` singleton keeps, per tenant, a set of
``asyncio.Queue`` subscribers. Producers call :meth:`EventBus.publish` with a
tenant id and a JSON-serialisable event dict; every queue subscribed to that
tenant receives a copy. SSE endpoints :meth:`subscribe` to obtain a queue and
:meth:`unsubscribe` it on disconnect.

This is intentionally simple and single-process. For multi-worker deployments
swap the backing store for Redis pub/sub behind the same interface.
"""
from __future__ import annotations

import asyncio
from typing import Any


class EventBus:
    """Per-tenant async fan-out of events to subscriber queues."""

    def __init__(self, max_queue: int = 1000) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._max_queue = max_queue

    def subscribe(self, tenant_id: str) -> asyncio.Queue:
        """Register and return a new queue receiving events for ``tenant_id``."""
        q: asyncio.Queue = asyncio.Queue(maxsize=self._max_queue)
        self._subscribers.setdefault(str(tenant_id), set()).add(q)
        return q

    def unsubscribe(self, tenant_id: str, q: asyncio.Queue) -> None:
        """Remove ``q`` from a tenant's subscriber set; cleans up empty sets."""
        subs = self._subscribers.get(str(tenant_id))
        if not subs:
            return
        subs.discard(q)
        if not subs:
            self._subscribers.pop(str(tenant_id), None)

    def publish(self, tenant_id: str, event: dict[str, Any]) -> None:
        """Best-effort, non-blocking fan-out of ``event`` to a tenant's queues.

        Full queues (slow/dead consumers) are skipped rather than blocking the
        caller, so publishing never stalls a request or DB write.
        """
        subs = self._subscribers.get(str(tenant_id))
        if not subs:
            return
        for q in list(subs):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                continue


# Module-level singleton used across the app.
bus = EventBus()
