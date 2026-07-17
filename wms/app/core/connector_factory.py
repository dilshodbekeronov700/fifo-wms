"""
Factory: build connector clients from per-tenant DB config.

Registry-driven (see app.connectors.base / registry): the factory does not know
about specific connectors, it looks up the spec and calls its builder with the
decrypted credentials. Credentials are encrypted at rest (app.core.crypto).
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.connectors.registry  # noqa: F401 — populates the connector registry
from app.connectors.aslbelgisi import AslBelgisiClient
from app.connectors.base import get_spec
from app.connectors.smartup import SmartupClient
from app.core.crypto import decrypt_credentials
from app.models.connector import ConnectorConfig


async def get_connector(db: AsyncSession, tenant_id: uuid.UUID, connector_type: str) -> Any:
    """Build a connector client of the given type for the tenant."""
    cfg = await _get_config(db, tenant_id, connector_type)
    creds = decrypt_credentials(cfg.credentials)
    spec = get_spec(connector_type)
    return spec.builder(creds, cfg.settings or {})


async def get_smartup_client(db: AsyncSession, tenant_id: uuid.UUID) -> SmartupClient:
    return await get_connector(db, tenant_id, "smartup")


async def get_aslbelgisi_client(db: AsyncSession, tenant_id: uuid.UUID) -> AslBelgisiClient:
    return await get_connector(db, tenant_id, "aslbelgisi")


async def get_tenant_tin(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    cfg = await _get_config(db, tenant_id, "aslbelgisi")
    return decrypt_credentials(cfg.credentials).get("tin", "")


async def get_business_place_id(db: AsyncSession, tenant_id: uuid.UUID) -> int | str | None:
    cfg = await _get_config(db, tenant_id, "aslbelgisi")
    return decrypt_credentials(cfg.credentials).get("business_place_id")


async def _get_config(
    db: AsyncSession, tenant_id: uuid.UUID, connector_type: str
) -> ConnectorConfig:
    result = await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.tenant_id == tenant_id,
            ConnectorConfig.connector_type == connector_type,
            ConnectorConfig.is_active.is_(True),
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(
            status_code=503,
            detail=f"{connector_type} connector not configured for this tenant",
        )
    return cfg
