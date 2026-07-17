"""
Putaway reservation expiry worker.

A directed-putaway reservation holds a slot's capacity for RESERVATION_TTL_MINUTES.
If the operator never confirms (walked away, TSD died, shift ended), that capacity
would stay blocked forever — the slotting engine keeps subtracting it and the slot
looks fuller than it is.

`expire_stale_reservations` only runs opportunistically (when someone reserves or
searches in that same warehouse). This worker sweeps ALL tenants/warehouses on a
fixed cadence so stale holds are released even when nobody touches that warehouse.
"""
from __future__ import annotations

import asyncio
import logging

from app.core.health import heartbeat
from app.db.base import AsyncSessionLocal
from app.services.putaway import expire_all_stale_reservations

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 60  # every minute — TTL is 120 min, so ≤1 min lag is negligible


async def run_reservation_expiry_worker() -> None:
    logger.info("Reservation-expiry worker started (interval=%ss)", CHECK_INTERVAL)
    while True:
        heartbeat("reservation_expiry")
        try:
            async with AsyncSessionLocal() as db:
                n = await expire_all_stale_reservations(db)
                if n:
                    await db.commit()
                    logger.info("Expired %s stale putaway reservation(s)", n)
        except Exception as exc:
            logger.error("Reservation-expiry iteration error: %s", exc)
        await asyncio.sleep(CHECK_INTERVAL)
