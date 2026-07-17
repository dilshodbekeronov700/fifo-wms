"""
Asl Belgisi apiKey auto-refresh worker.

Business User apiKeys expire after ≤90 days. This worker periodically checks
every active Asl Belgisi connector and, if the key is near expiry (or the check
fails), refreshes it and stores the new (encrypted) key — so the integration
never breaks because a key silently expired.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.connectors.aslbelgisi import AslBelgisiClient
from app.core.crypto import decrypt_credentials, encrypt_credentials
from app.core.health import heartbeat
from app.db.base import AsyncSessionLocal
from app.models.connector import ConnectorConfig

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 6 * 60 * 60       # every 6 hours
REFRESH_BEFORE_DAYS = 7            # refresh when ≤7 days remain


def _expires_soon(expires_on: str | None) -> bool:
    if not expires_on:
        return False
    try:
        dt = datetime.fromisoformat(expires_on.replace("Z", "+00:00"))
    except ValueError:
        return False
    return (dt - datetime.now(timezone.utc)).days <= REFRESH_BEFORE_DAYS


async def _refresh_one(db, cfg: ConnectorConfig) -> None:
    creds = decrypt_credentials(cfg.credentials)
    client = AslBelgisiClient(
        api_key=creds.get("api_key", ""),
        base_url=creds.get("base_url", ""),
        tin=creds.get("tin", ""),
    )
    try:
        info = await client.check_api_key()
    except Exception as exc:
        logger.warning("apiKey check failed for tenant %s: %s", cfg.tenant_id, exc)
        return

    if not _expires_soon(info.get("expiresOn")):
        return

    try:
        new_key = await client.refresh_api_key()
    except Exception as exc:
        logger.error("apiKey refresh failed for tenant %s: %s", cfg.tenant_id, exc)
        return

    creds["api_key"] = new_key
    cfg.credentials = encrypt_credentials(creds)
    await db.commit()
    logger.info("apiKey refreshed for tenant %s", cfg.tenant_id)


async def run_key_refresh_worker() -> None:
    logger.info("Key-refresh worker started (interval=%ss)", CHECK_INTERVAL)
    while True:
        heartbeat("key_refresh")
        try:
            async with AsyncSessionLocal() as db:
                rows = (await db.execute(
                    select(ConnectorConfig).where(
                        ConnectorConfig.connector_type == "aslbelgisi",
                        ConnectorConfig.is_active.is_(True),
                    )
                )).scalars().all()
                for cfg in rows:
                    await _refresh_one(db, cfg)
        except Exception as exc:
            logger.error("Key-refresh iteration error: %s", exc)
        await asyncio.sleep(CHECK_INTERVAL)
