"""End-to-end logic test for the reserve → confirm-by-scan putaway flow.

Uses an in-memory SQLite DB (no external services, no pytest-asyncio). Proves:
  * directed slotting ranks a near-dock PICK slot above a far RESERVE slot,
  * reserving a slot holds its capacity (it stops being offered),
  * confirming with the correct location barcode moves stock + marks the slot,
  * scanning the wrong barcode is rejected,
  * a full slot is rejected.
"""
import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all tables
from app.db.base import Base
from app.models.inventory import AbcClass, Batch, Product, StockItem
from app.models.reservation import ReservationStatus
from app.models.tenant import Tenant
from app.models.warehouse import (
    Location, LocationStatus, LocationType, Warehouse, Zone, ZoneType,
)
from app.services import putaway as pw
from app.services import slotting


def _run(coro):
    return asyncio.run(coro)


async def _make_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, maker


async def _seed(s):
    tenant = Tenant(name="t", slug="t", settings={})
    s.add(tenant)
    await s.flush()
    wh = Warehouse(tenant_id=tenant.id, name="WH")
    s.add(wh)
    await s.flush()

    dock = Zone(warehouse_id=wh.id, name="DOCK", zone_type=ZoneType.DOCK, x=0, y=0, putaway_rules={})
    pick = Zone(warehouse_id=wh.id, name="PICK", zone_type=ZoneType.PICK, x=1, y=1, putaway_rules={})
    reserve = Zone(warehouse_id=wh.id, name="RES", zone_type=ZoneType.RESERVE, x=50, y=50, putaway_rules={})
    s.add_all([dock, pick, reserve])
    await s.flush()

    near = Location(zone_id=pick.id, code="A-01-01-01", barcode="LOC-NEAR",
                    location_type=LocationType.PALLET, status=LocationStatus.EMPTY,
                    row="A", rack=1, tier=1, position=1, max_pallets=1, x=2, y=2)
    far = Location(zone_id=reserve.id, code="B-09-03-01", barcode="LOC-FAR",
                   location_type=LocationType.PALLET, status=LocationStatus.EMPTY,
                   row="B", rack=9, tier=3, position=1, max_pallets=1, x=49, y=49)
    s.add_all([near, far])

    product = Product(tenant_id=tenant.id, gtin="04601234567890", name={"uz": "Suv 0.5L"},
                      abc_class=AbcClass.A, boxes_per_pallet=50, units_per_box=12, weight_kg=0.6)
    s.add(product)
    await s.flush()
    batch = Batch(product_id=product.id, expiry_date="2027-01-01")
    s.add(batch)
    await s.flush()
    return tenant, wh, product, batch, near, far


def test_slotting_prefers_near_dock_pick():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            tenant, wh, product, batch, near, far = await _seed(s)
            cands = await slotting.suggest_locations(
                s, warehouse_id=wh.id, product=product, batch_id=batch.id,
                expiry_date="2027-01-01", qty=50, unit_count=600, top_n=5,
            )
            assert cands, "expected candidates"
            assert cands[0].location.id == near.id, "near-dock PICK should rank first"
            assert cands[0].factors, "per-factor breakdown must be populated"
        await engine.dispose()
    _run(go())


def test_reserve_holds_capacity_then_confirm_places_stock():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            tenant, wh, product, batch, near, far = await _seed(s)
            res = await pw.reserve_slot(
                s, tenant_id=tenant.id, warehouse_id=wh.id, code="00123456789012345678",
                location_id=near.id, product_id=product.id, batch_id=batch.id,
                qty=50, unit_count=600, package_type="BOX_LV_1", score=99.0,
                reason="test", manual=False, payload={"children": ["c1", "c2"]}, user_id=None,
            )
            assert res.status == ReservationStatus.PENDING

            cands = await slotting.suggest_locations(
                s, warehouse_id=wh.id, product=product, batch_id=batch.id, qty=50, top_n=5,
            )
            assert near.id not in {c.location.id for c in cands}, "reserved slot must be excluded"

            # Mavjud bo'lmagan yacheyka barcode'i skanlansa — rad etiladi.
            # (Haqiqiy boshqa yacheyka skanlansa, o'sha yacheykaga qayta yo'naltiriladi.)
            with pytest.raises(pw.PutawayError):
                await pw.confirm_putaway(s, tenant_id=tenant.id, reservation_id=res.id,
                                         scanned_location="LOC-NOWHERE", user_id=None)

            done = await pw.confirm_putaway(s, tenant_id=tenant.id, reservation_id=res.id,
                                            scanned_location="LOC-NEAR", user_id=None)
            assert done.status == ReservationStatus.CONFIRMED

            await s.refresh(near)
            assert near.status == LocationStatus.OCCUPIED
            stock = (await s.execute(
                StockItem.__table__.select().where(StockItem.location_id == near.id)
            )).first()
            assert stock is not None and stock.qty == 50
        await engine.dispose()
    _run(go())


def test_full_slot_reservation_rejected():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            tenant, wh, product, batch, near, far = await _seed(s)
            s.add(StockItem(warehouse_id=wh.id, location_id=near.id,
                            product_id=product.id, batch_id=batch.id, qty=50))
            await s.flush()
            with pytest.raises(pw.PutawayError):
                await pw.reserve_slot(
                    s, tenant_id=tenant.id, warehouse_id=wh.id, code="00999",
                    location_id=near.id, product_id=product.id, batch_id=batch.id,
                    qty=50, unit_count=600, package_type="BOX_LV_1", score=1.0,
                    reason="x", manual=True, payload={}, user_id=None,
                )
        await engine.dispose()
    _run(go())
