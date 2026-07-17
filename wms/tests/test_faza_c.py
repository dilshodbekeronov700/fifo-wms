"""Faza C — professional WMS funksiyalari testlari.

In-memory SQLite. Qamrov: replenishment (min/max + threshold), cycle-count task
generatsiyasi + variance tuzatish, wave picking birlashtirish + marshrut, RMA tasnif.
"""
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.db.base import Base
from app.models.inventory import (
    AbcClass, Batch, BatchStatus, Product, StockItem, StockStatus,
)
from app.models.task import TaskStatus, TaskType
from app.models.tenant import Tenant
from app.models.warehouse import (
    Location, LocationStatus, LocationType, Warehouse, Zone, ZoneType,
)
from app.services import cycle_count as cc
from app.services import replenishment as rep
from app.services import rma as rma_svc
from app.services import wave as wave_svc


def _run(coro):
    return asyncio.run(coro)


async def _make_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _seed(s, *, min_stock=None, max_stock=None):
    tenant = Tenant(name="t", slug="t", settings={})
    s.add(tenant)
    await s.flush()
    wh = Warehouse(tenant_id=tenant.id, name="WH")
    s.add(wh)
    await s.flush()
    pick_z = Zone(warehouse_id=wh.id, name="PICK", zone_type=ZoneType.PICK, putaway_rules={})
    res_z = Zone(warehouse_id=wh.id, name="RES", zone_type=ZoneType.RESERVE, putaway_rules={})
    ret_z = Zone(warehouse_id=wh.id, name="RET", zone_type=ZoneType.RETURN, putaway_rules={})
    qua_z = Zone(warehouse_id=wh.id, name="QUA", zone_type=ZoneType.QUARANTINE, putaway_rules={})
    s.add_all([pick_z, res_z, ret_z, qua_z])
    await s.flush()

    def _loc(zone, code, r, rk):
        return Location(zone_id=zone.id, code=code, barcode=f"BC-{code}",
                        location_type=LocationType.SHELF, status=LocationStatus.OCCUPIED,
                        row=r, rack=rk, tier=1, position=1, max_pallets=5)
    pick_loc = _loc(pick_z, "P-01", "A", 1)
    res_loc = _loc(res_z, "R-09", "B", 9)
    ret_loc = _loc(ret_z, "RET-01", "C", 1)
    qua_loc = _loc(qua_z, "QUA-01", "C", 2)
    s.add_all([pick_loc, res_loc, ret_loc, qua_loc])
    product = Product(tenant_id=tenant.id, gtin="04600000000001", name={"uz": "P"},
                      abc_class=AbcClass.A, units_per_box=12,
                      min_stock=min_stock, max_stock=max_stock)
    s.add(product)
    await s.flush()
    batch = Batch(product_id=product.id, expiry_date="2027-01-01", status=BatchStatus.AVAILABLE)
    s.add(batch)
    await s.flush()
    return dict(tenant=tenant, wh=wh, product=product, batch=batch,
                pick_loc=pick_loc, res_loc=res_loc, ret_loc=ret_loc, qua_loc=qua_loc)


def _stock(d, loc, qty):
    return StockItem(warehouse_id=d["wh"].id, location_id=loc.id,
                     product_id=d["product"].id, batch_id=d["batch"].id,
                     qty=qty, status=StockStatus.AVAILABLE)


def test_replenishment_min_max_tops_up_to_target():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            d = await _seed(s, min_stock=10, max_stock=50)
            s.add_all([_stock(d, d["pick_loc"], 5), _stock(d, d["res_loc"], 100)])
            await s.flush()
            sugg = await rep.compute_replenishments(s, warehouse_id=d["wh"].id)
            assert len(sugg) == 1
            assert sugg[0].reason == "min_stock"
            assert sugg[0].target == 50
            assert sugg[0].move_qty == 45   # 50 - 5
        await engine.dispose()
    _run(go())


def test_replenishment_threshold_mode_without_min_stock():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            d = await _seed(s)  # min_stock None
            s.add_all([_stock(d, d["pick_loc"], 0), _stock(d, d["res_loc"], 30)])
            await s.flush()
            sugg = await rep.compute_replenishments(s, warehouse_id=d["wh"].id, threshold=0)
            assert len(sugg) == 1
            assert sugg[0].reason == "threshold"
            assert sugg[0].move_qty == 30
        await engine.dispose()
    _run(go())


def test_replenishment_generate_and_execute():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            d = await _seed(s, min_stock=10, max_stock=50)
            s.add_all([_stock(d, d["pick_loc"], 5), _stock(d, d["res_loc"], 100)])
            await s.flush()
            sugg = await rep.compute_replenishments(s, warehouse_id=d["wh"].id)
            tasks = await rep.generate_tasks(
                s, tenant_id=d["tenant"].id, warehouse_id=d["wh"].id, suggestions=sugg)
            assert len(tasks) == 1 and tasks[0].task_type == TaskType.REPLENISH
            # Ikkinchi marta yaratganda takrorlanmaydi.
            again = await rep.generate_tasks(
                s, tenant_id=d["tenant"].id, warehouse_id=d["wh"].id, suggestions=sugg)
            assert again == []

            await rep.execute_move(
                s, tenant_id=d["tenant"].id, warehouse_id=d["wh"].id,
                product_id=d["product"].id, batch_id=d["batch"].id,
                from_location_id=d["res_loc"].id, to_location_id=d["pick_loc"].id,
                qty=45, user_id=None, task_id=tasks[0].id)
            await s.flush()
            assert tasks[0].status == TaskStatus.COMPLETED
            pick = (await s.execute(
                StockItem.__table__.select().where(StockItem.location_id == d["pick_loc"].id)
            )).first()
            res = (await s.execute(
                StockItem.__table__.select().where(StockItem.location_id == d["res_loc"].id)
            )).first()
            assert pick.qty == 50 and res.qty == 55
        await engine.dispose()
    _run(go())


def test_cycle_count_generate_tasks_and_variance():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            d = await _seed(s)
            s.add(_stock(d, d["pick_loc"], 10))
            await s.flush()
            tasks = await cc.generate_count_tasks(
                s, tenant_id=d["tenant"].id, warehouse_id=d["wh"].id, limit=20)
            assert len(tasks) == 1 and tasks[0].task_type == TaskType.COUNT
            # Ikkinchi marta — ochiq task borligi uchun bo'sh.
            again = await cc.generate_count_tasks(
                s, tenant_id=d["tenant"].id, warehouse_id=d["wh"].id)
            assert again == []

            var = await cc.record_count(
                s, tenant_id=d["tenant"].id, warehouse_id=d["wh"].id,
                location_id=d["pick_loc"].id,
                counted=[(d["product"].id, d["batch"].id, 8)],  # 10 kutilgan, 8 sanaldi
                user_id=None, task_id=tasks[0].id)
            await s.flush()
            assert len(var) == 1 and var[0].diff == -2
            assert tasks[0].status == TaskStatus.COMPLETED
            stock = (await s.execute(
                StockItem.__table__.select().where(StockItem.location_id == d["pick_loc"].id)
            )).first()
            assert stock.qty == 8
            summary = await cc.variance_summary(s, warehouse_id=d["wh"].id)
            assert summary["minus_count"] == 1 and summary["minus_units"] == 2
        await engine.dispose()
    _run(go())


def test_wave_groups_by_location_and_routes():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            d = await _seed(s)
            # Ikki buyurtma bir xil pick-face'dan teradi → bitta stopga guruhlanadi.
            s.add(_stock(d, d["pick_loc"], 100))
            await s.flush()
            plan = await wave_svc.build_wave_plan(
                s, warehouse_id=d["wh"].id, lines=[
                    wave_svc.WaveLineRequest(order_line_id="L1", product_id=d["product"].id,
                                             requested_boxes=10, order_id="O1"),
                    wave_svc.WaveLineRequest(order_line_id="L2", product_id=d["product"].id,
                                             requested_boxes=5, order_id="O2"),
                ])
            assert len(plan.stops) == 1                 # bitta yacheyka
            assert len(plan.stops[0].instructions) == 2  # ikki buyurtma
            assert plan.total_boxes == 15
            assert plan.shortfalls == {}
        await engine.dispose()
    _run(go())


def test_rma_dispositions():
    async def go():
        engine, maker = await _make_session()
        async with maker() as s:
            d = await _seed(s)
            res = await rma_svc.process_rma(
                s, tenant_id=d["tenant"].id, warehouse_id=d["wh"].id, user_id=None,
                lines=[
                    rma_svc.RmaLine(product_id=d["product"].id, batch_id=d["batch"].id,
                                    qty=10, disposition=rma_svc.Disposition.RESTOCK),
                    rma_svc.RmaLine(product_id=d["product"].id, batch_id=d["batch"].id,
                                    qty=3, disposition=rma_svc.Disposition.QUARANTINE),
                    rma_svc.RmaLine(product_id=d["product"].id, batch_id=d["batch"].id,
                                    qty=2, disposition=rma_svc.Disposition.SCRAP),
                ])
            await s.flush()
            assert res.restocked == 10 and res.quarantined == 3 and res.scrapped == 2
            # RESTOCK → RETURN zonaga qo'shildi.
            ret = (await s.execute(
                StockItem.__table__.select().where(StockItem.location_id == d["ret_loc"].id)
            )).first()
            assert ret.qty == 10
            # QUARANTINE → karantin zonaga + partiya statusi QUARANTINE.
            await s.refresh(d["batch"])
            assert d["batch"].status == BatchStatus.QUARANTINE
        await engine.dispose()
    _run(go())
