"""ERP-yozuv (Smartup'ga o'zgartirish yuborish) ruxsati — rol asosida, sozlanadigan.

Qaysi rollar Smartup'ga YOZISH (buyurtma statusi, marka biriktirish, ko'chirish push...)
qila olishini tenant'ning Smartup connector settings'ida saqlaymiz:
    ConnectorConfig.settings["erp_write_roles"] = ["tenant_admin", "warehouse_manager"]
Superadmin har doim ruxsatli. Sozlamalar bo'limidan o'zgartiriladi.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import ConnectorConfig

DEFAULT_ERP_WRITE_ROLES = ["tenant_admin", "warehouse_manager"]


async def _smartup_cfg(db: AsyncSession, tenant_id: uuid.UUID) -> ConnectorConfig | None:
    return (await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.tenant_id == tenant_id,
            ConnectorConfig.connector_type == "smartup",
        )
    )).scalar_one_or_none()


async def get_erp_write_roles(db: AsyncSession, tenant_id: uuid.UUID) -> list[str]:
    cfg = await _smartup_cfg(db, tenant_id)
    roles = (cfg.settings or {}).get("erp_write_roles") if cfg else None
    if isinstance(roles, list) and roles:
        return [str(r) for r in roles]
    return list(DEFAULT_ERP_WRITE_ROLES)


async def set_erp_write_roles(db: AsyncSession, tenant_id: uuid.UUID, roles: list[str]) -> list[str]:
    cfg = await _smartup_cfg(db, tenant_id)
    if cfg is None:
        raise ValueError("Smartup connector sozlanmagan")
    settings = dict(cfg.settings or {})
    settings["erp_write_roles"] = [str(r) for r in roles]
    cfg.settings = settings
    await db.commit()
    return settings["erp_write_roles"]


def user_can_write_erp(user, allowed_roles: list[str]) -> bool:
    if getattr(user, "is_superadmin", False):
        return True
    return any(r.name in allowed_roles for r in getattr(user, "roles", []))
