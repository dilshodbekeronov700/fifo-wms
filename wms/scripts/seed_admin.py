"""
Bootstrap script: create an admin user + a demo tenant/warehouse/zones/locations
/products so the app can be tried end-to-end.

Run:  poetry run python -m scripts.seed_admin
Login: admin@wms.uz / admin123
Idempotent — safe to run repeatedly.
"""
import asyncio

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.base import AsyncSessionLocal
from app.models.auth import User
from app.models.inventory import AbcClass, Product
from app.models.tenant import Tenant
from app.models.warehouse import (
    Location, LocationStatus, LocationType, Warehouse, Zone, ZoneType,
)

ADMIN_EMAIL = "admin@wms.uz"
ADMIN_PASSWORD = "admin123"


async def get_or_create(db, model, defaults=None, **filters):
    row = (await db.execute(select(model).filter_by(**filters))).scalar_one_or_none()
    if row:
        return row, False
    row = model(**filters, **(defaults or {}))
    db.add(row)
    await db.flush()
    return row, True


async def main() -> None:
    async with AsyncSessionLocal() as db:
        tenant, _ = await get_or_create(
            db, Tenant, slug="demo",
            defaults={"name": "Demo Suv Zavodi", "settings": {}},
        )

        admin = (await db.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        )).scalar_one_or_none()
        if admin is None:
            admin = User(
                tenant_id=tenant.id,
                email=ADMIN_EMAIL,
                full_name="Administrator",
                hashed_password=hash_password(ADMIN_PASSWORD),
                is_active=True,
                is_superadmin=True,  # full access for trying everything
            )
            db.add(admin)

        wh, _ = await get_or_create(
            db, Warehouse, tenant_id=tenant.id, name="Tayyor mahsulot skladi",
            defaults={"smartup_warehouse_code": "001wrh"},
        )

        # Zones: a dock (drives proximity), reserve, pick — with coordinates
        dock, _ = await get_or_create(
            db, Zone, warehouse_id=wh.id, name="Dok (yuklash)",
            defaults={"zone_type": ZoneType.DOCK, "x": 900, "y": 300,
                      "width": 120, "height": 200, "putaway_rules": {}},
        )
        reserve, _ = await get_or_create(
            db, Zone, warehouse_id=wh.id, name="Rezerv 19L",
            defaults={"zone_type": ZoneType.RESERVE, "x": 80, "y": 60,
                      "width": 400, "height": 120,
                      "putaway_rules": {"categories": ["19L"]}},
        )
        pick, _ = await get_or_create(
            db, Zone, warehouse_id=wh.id, name="Pick 0.5L",
            defaults={"zone_type": ZoneType.PICK, "x": 80, "y": 420,
                      "width": 400, "height": 120,
                      "putaway_rules": {"categories": ["0.5L"]}},
        )

        # Demo yacheykalar — FAQAT ombor butunlay bo'sh bo'lsa (birinchi fresh deploy).
        # Aks holda real stellajlar (UI/generateRack orqali yaratilgan A-01-1…F-16-6)
        # bilan to'qnashadi va nol-padded dublikat (A-01-01…) paydo bo'lardi.
        loc_count = (await db.execute(
            select(func.count()).select_from(Location)
            .join(Zone, Zone.id == Location.zone_id)
            .where(Zone.warehouse_id == wh.id)
        )).scalar()
        if not loc_count:
            for zone, prefix, base_x, base_y in [
                (reserve, "A", 90, 70), (pick, "B", 90, 430),
            ]:
                for i in range(1, 7):
                    await get_or_create(
                        db, Location, zone_id=zone.id, code=f"{prefix}-01-{i}",
                        defaults={
                            "location_type": LocationType.PALLET,
                            "status": LocationStatus.EMPTY,
                            "row": prefix, "rack": 1, "tier": ((i - 1) // 2) + 1,
                            "position": ((i - 1) % 2) + 1,
                            "max_pallets": 2, "x": base_x, "y": base_y,
                        },
                    )

        # Demo products (19L + 0.5L) — category drives zone routing
        await get_or_create(
            db, Product, tenant_id=tenant.id, smartup_product_code="P19",
            defaults={"name": {"ru": "Вода 19л", "uz": "Suv 19L"},
                      "gtin": "04600000000019", "category": "19L",
                      "units_per_box": 1, "abc_class": AbcClass.A,
                      "weight_kg": 19.0, "volume_m3": 0.019},
        )
        await get_or_create(
            db, Product, tenant_id=tenant.id, smartup_product_code="P05",
            defaults={"name": {"ru": "Вода 0.5л", "uz": "Suv 0.5L"},
                      "gtin": "04600000000005", "category": "0.5L",
                      "units_per_box": 12, "abc_class": AbcClass.B,
                      "weight_kg": 6.0, "volume_m3": 0.006},
        )

        await db.commit()

    print("✓ Seed complete")
    print(f"  Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"  Tenant: Demo Suv Zavodi  ·  Warehouse: Tayyor mahsulot skladi")


if __name__ == "__main__":
    asyncio.run(main())
