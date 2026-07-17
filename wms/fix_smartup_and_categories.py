"""
(A) Smartup connector akkauntini admin@ocard ga yangilash (shifrlangan).
(B) Mahsulot kategoriyalarini nomdan to'ldirish + saqlash zonalarining
    kategoriya cheklovini yumshatish (putaway barcha o'lchamlar uchun ishlasin).
"""
import asyncio
import re
import uuid

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.core.crypto import encrypt_credentials, decrypt_credentials
from app.models.connector import ConnectorConfig
from app.models.warehouse import Zone
from app.models.inventory import Product

TENANT = uuid.UUID("8f452934-36d2-412b-87ed-2bf4828d3370")
WAREHOUSE_ID = uuid.UUID("55ea743b-f340-49e9-961f-79c7720d739f")

NEW_CREDS = {
    "base_url": "https://smartup.online",
    "login": "admin@ocard",
    "password": "595959",
    "project_code": "",      # bo'sh — akkaunt standart loyihasi
    "filial_id": "1833",
}


def category_from_name(name: str) -> str | None:
    """'Blanc Bleu (без газа 0,500x12)' -> '0.5L'."""
    if not name:
        return None
    m = re.search(r"(\d+[.,]\d+)", name)
    if not m:
        return None
    try:
        val = float(m.group(1).replace(",", "."))
    except ValueError:
        return None
    return f"{val:g}L"


async def main():
    async with AsyncSessionLocal() as db:
        # ── (A) connector akkaunti ──
        cfg = (await db.execute(
            select(ConnectorConfig).where(
                ConnectorConfig.tenant_id == TENANT,
                ConnectorConfig.connector_type == "smartup",
            )
        )).scalar_one_or_none()
        if cfg is None:
            cfg = ConnectorConfig(
                tenant_id=TENANT, connector_type="smartup",
                credentials=encrypt_credentials(NEW_CREDS), settings={}, is_active=True,
            )
            db.add(cfg)
            print("Connector: yangi yaratildi (admin@ocard)")
        else:
            cfg.credentials = encrypt_credentials(NEW_CREDS)
            cfg.is_active = True
            print("Connector: admin@ocard ga yangilandi")

        # ── (B1) mahsulot kategoriyalari ──
        prods = (await db.execute(
            select(Product).where(Product.tenant_id == TENANT)
        )).scalars().all()
        filled = 0
        for p in prods:
            name = (p.name or {}).get("ru") or (p.name or {}).get("uz") or ""
            cat = category_from_name(name)
            if cat and p.category != cat:
                p.category = cat
                filled += 1
        print(f"Kategoriya to'ldirildi: {filled} mahsulot")

        # ── (B2) saqlash zonalarini yumshatish (kategoriya cheklovini olib tashlash) ──
        zones = (await db.execute(
            select(Zone).where(Zone.warehouse_id == WAREHOUSE_ID)
        )).scalars().all()
        relaxed = 0
        for z in zones:
            rules = dict(z.zone_rules) if hasattr(z, "zone_rules") else dict(z.putaway_rules or {})
            if rules.get("categories"):
                rules.pop("categories", None)
                z.putaway_rules = rules
                relaxed += 1
        print(f"Zona cheklovi yumshatildi: {relaxed} zona")

        await db.commit()
        print("TAYYOR.")


if __name__ == "__main__":
    asyncio.run(main())
