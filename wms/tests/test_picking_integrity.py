"""Faza A — inventar yaxlitligi testlari (picking + rezervatsiya muddati).

In-memory SQLite (tashqi servissiz, pytest-asyncio'siz). Isbotlaydi:
  * FEFO tartibi — muddati yaqin partiya birinchi teriladi,
  * karantin partiya pick rejasidan chetlab o'tiladi,
  * ketma-ket booking mavjud miqdordan oshib ketmaydi (over-book yo'q),
  * muddati o'tgan PENDING bron global sweep bilan EXPIRED bo'ladi.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — barcha jadvallarni ro'yxatga oladi
from app.db.base import Base
from app.models.inventory import (
    AbcClass, Batch, BatchStatus, Product, StockItem, StockStatus,
)
from app.models.reservation import PutawayReservation, ReservationStatus
from app.models.tenant import Tenant
from app.models.warehouse import (
    Location, LocationStatus, LocationType, Warehouse, Zone, ZoneType,
)
from app.services import picking as pk
from app.services import putaway as pw


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
    pick = Zone(warehouse_id=wh.id, name="PICK", zone_type=ZoneType.PICK, x=1, y=1, putaway_rules={})
    s.add(pick)
    await s.flush()
    loc_a = Location(zone_id=pick.id, code="A-01", barcode="LOC-A",
                     location_type=LocationType.PALLET, status=LocationStatus.OCCUPIED,
                     row="A", rack=1, tier=1, position=1, max_pallets=1, x=2, y=2)
    loc_b = Location(zone_id=pick.id, code="A-02", barcode="LOC-B",
                     location_type=LocationType.PALLET, status=LocationStatus.OCCUPIED,
                     row="A", rack=2, tier=1, position=1, max_pallets=1, x=3, y=3)
    s.add_all([loc_a, loc_b])
    product = Product(tenant_id=tenant.id, gtin="04601234567890", name={"uz": "Suv"},
                      abc_class=AbcClass.A, boxes_per_pallet=50, units_per_box=12)
    s.add(product)
    await s.flush()
    return tenant, wh, pick, loc_a, loc_b, product


def test_fefo_orders_earliest_expiry_first():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            tenant, wh, pick, loc_a, loc_b, product = await _seed(s)
            far = Batch(product_id=product.id, expiry_date="2027-12-01",
                        status=BatchStatus.AVAILABLE)
            near = Batch(product_id=product.id, expiry_date="2026-08-01",
                         status=BatchStatus.AVAILABLE)
            s.add_all([far, near])
            await s.flush()
            s.add_all([
                StockItem(warehouse_id=wh.id, location_id=loc_a.id, product_id=product.id,
                          batch_id=far.id, qty=10, status=StockStatus.AVAILABLE),
                StockItem(warehouse_id=wh.id, location_id=loc_b.id, product_id=product.id,
                          batch_id=near.id, qty=10, status=StockStatus.AVAILABLE),
            ])
            await s.flush()

            plan = await pk.build_pick_plan(
                s, warehouse_id=wh.id, product_id=product.id,
                order_line_id="L1", requested_boxes=5,
            )
            assert plan.allotments, "kandidat kutilgan edi"
            # Muddati yaqin (2026-08) partiya birinchi teriladi.
            assert plan.allotments[0].stock_item.batch_id == near.id
            assert plan.shortfall == 0
        await engine.dispose()
    _run(go())


def test_quarantine_batch_excluded_from_pick():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            tenant, wh, pick, loc_a, loc_b, product = await _seed(s)
            q = Batch(product_id=product.id, expiry_date="2026-08-01",
                      status=BatchStatus.QUARANTINE)
            ok = Batch(product_id=product.id, expiry_date="2027-12-01",
                       status=BatchStatus.AVAILABLE)
            s.add_all([q, ok])
            await s.flush()
            s.add_all([
                StockItem(warehouse_id=wh.id, location_id=loc_a.id, product_id=product.id,
                          batch_id=q.id, qty=10, status=StockStatus.AVAILABLE),
                StockItem(warehouse_id=wh.id, location_id=loc_b.id, product_id=product.id,
                          batch_id=ok.id, qty=10, status=StockStatus.AVAILABLE),
            ])
            await s.flush()

            plan = await pk.build_pick_plan(
                s, warehouse_id=wh.id, product_id=product.id,
                order_line_id="L1", requested_boxes=100,
            )
            picked = {a.stock_item.batch_id for a in plan.allotments}
            assert q.id not in picked, "karantin partiya terilmasligi kerak"
            assert ok.id in picked
            # Faqat AVAILABLE 10 quti mavjud → 90 quti kam.
            assert plan.shortfall == 90
        await engine.dispose()
    _run(go())


def test_execute_pick_plan_does_not_overbook():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            tenant, wh, pick, loc_a, loc_b, product = await _seed(s)
            batch = Batch(product_id=product.id, expiry_date="2027-01-01",
                          status=BatchStatus.AVAILABLE)
            s.add(batch)
            await s.flush()
            s.add(StockItem(warehouse_id=wh.id, location_id=loc_a.id, product_id=product.id,
                            batch_id=batch.id, qty=10, status=StockStatus.AVAILABLE))
            await s.flush()

            # Ikkita order har biri 8 quti so'raydi — reja tuzilganda ikkalasi ham
            # 8 tani ko'radi (10 mavjud). Ketma-ket execute qilinganda ikkinchisi
            # faqat qolgan 2 tani booking qilishi kerak (over-book bo'lmasin).
            p1 = await pk.build_pick_plan(s, warehouse_id=wh.id, product_id=product.id,
                                          order_line_id="L1", requested_boxes=8)
            p2 = await pk.build_pick_plan(s, warehouse_id=wh.id, product_id=product.id,
                                          order_line_id="L2", requested_boxes=8)

            await pk.execute_pick_plan(s, tenant_id=tenant.id, warehouse_id=wh.id,
                                       user_id=None, document_id=None, plan=p1)
            await pk.execute_pick_plan(s, tenant_id=tenant.id, warehouse_id=wh.id,
                                       user_id=None, document_id=None, plan=p2)
            await s.flush()

            stock = (await s.execute(
                StockItem.__table__.select().where(StockItem.location_id == loc_a.id)
            )).first()
            # qty_booked hech qachon qty (10) dan oshmaydi — CHECK constraint saqlanadi.
            assert stock.qty_booked == 10
            assert stock.qty_booked <= stock.qty
        await engine.dispose()
    _run(go())


def test_expire_all_stale_reservations():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            tenant, wh, pick, loc_a, loc_b, product = await _seed(s)
            past = datetime.now(timezone.utc) - timedelta(minutes=5)
            future = datetime.now(timezone.utc) + timedelta(minutes=120)
            stale = PutawayReservation(
                tenant_id=tenant.id, warehouse_id=wh.id, code="C-STALE",
                location_id=loc_a.id, qty=1, status=ReservationStatus.PENDING,
                payload={}, expires_at=past,
            )
            fresh = PutawayReservation(
                tenant_id=tenant.id, warehouse_id=wh.id, code="C-FRESH",
                location_id=loc_b.id, qty=1, status=ReservationStatus.PENDING,
                payload={}, expires_at=future,
            )
            s.add_all([stale, fresh])
            await s.flush()

            n = await pw.expire_all_stale_reservations(s)
            await s.flush()
            assert n == 1, "faqat muddati o'tgan bron EXPIRED bo'lishi kerak"
            await s.refresh(stale)
            await s.refresh(fresh)
            assert stale.status == ReservationStatus.EXPIRED
            assert fresh.status == ReservationStatus.PENDING
        await engine.dispose()
    _run(go())
