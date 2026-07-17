"""Smartup mahsulotlarini WMS'ga sinxronlash (admin@ocard akkaunti bilan)."""
import asyncio
import uuid

from app.db.base import AsyncSessionLocal
from app.connectors.smartup import SmartupClient
from app.services import sync as sync_svc

TENANT = uuid.UUID("8f452934-36d2-412b-87ed-2bf4828d3370")


async def main():
    client = SmartupClient(
        base_url="https://smartup.online",
        login="admin@ocard",
        password="595959",
        project_code="",        # bo'sh — akkaunt standart loyihasi
        filial_id="1833",
    )
    async with AsyncSessionLocal() as db:
        result = await sync_svc.sync_products(
            db, tenant_id=TENANT, client=client, begin_modified_on="01.01.2020"
        )
        await db.commit()
        print(f"fetched={result.fetched} created={result.created} updated={result.updated}")


if __name__ == "__main__":
    asyncio.run(main())
