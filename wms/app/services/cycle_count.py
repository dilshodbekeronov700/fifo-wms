"""
Cycle counting — davriy inventarizatsiya (to'liq to'xtatishsiz).

Professional WMS omborni to'xtatmasdan, muntazam bir nechta yacheykani sanaydi.
Bu yerda ikki qism:
  1. `generate_count_tasks` — bugun sanaladigan yacheykalarni tanlaydi (ABC
     kadensi: A-klass mahsulotli joylar ustuvor), COUNT tasklar yaratadi.
  2. `record_count` — sanoq natijasini kutilgan (StockItem) bilan solishtiradi,
     farqni INVENTORY_PLUS/MINUS ledger yozuvi bilan tuzatadi, taskni yopadi.
  3. `variance_summary` — INVENTORY ledger yozuvlaridan farq statistikasi.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import AbcClass, Product, StockItem, StockStatus
from app.models.ledger import LedgerAction, LedgerEntry
from app.models.task import Task, TaskStatus, TaskType
from app.models.warehouse import Location, Zone
from app.services import ledger as ledger_svc

# ABC ustuvorligi — A eng tez-tez sanaladi.
_ABC_RANK = {AbcClass.A: 0, AbcClass.B: 1, AbcClass.C: 2, None: 3}


@dataclass
class CountVariance:
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    expected: int
    counted: int
    diff: int


async def generate_count_tasks(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    limit: int = 20,
) -> list[Task]:
    """Sanash uchun yacheykalarni tanlaydi (ABC ustuvorligi bo'yicha) va COUNT
    tasklar yaratadi. Ochiq COUNT taski bor yacheykalar chetlab o'tiladi."""
    # Ochiq COUNT tasklaridagi location_id'lar.
    open_tasks = (await db.execute(
        select(Task).where(
            Task.warehouse_id == warehouse_id,
            Task.task_type == TaskType.COUNT,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]),
        )
    )).scalars().all()
    busy = {t.payload.get("location_id") for t in open_tasks}

    rows = (await db.execute(
        select(StockItem, Location.id, Location.code, Product.abc_class)
        .join(Location, StockItem.location_id == Location.id)
        .join(Zone, Location.zone_id == Zone.id)
        .join(Product, StockItem.product_id == Product.id)
        .where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.qty > 0,
            StockItem.status == StockStatus.AVAILABLE,
        )
    )).all()

    # Yacheyka bo'yicha guruhlab, eng yuqori ABC klassini olamiz.
    by_loc: dict[uuid.UUID, dict] = {}
    for stock, loc_id, loc_code, abc in rows:
        if str(loc_id) in busy:
            continue
        entry = by_loc.setdefault(loc_id, {"code": loc_code, "rank": 3})
        entry["rank"] = min(entry["rank"], _ABC_RANK.get(abc, 3))

    ordered = sorted(by_loc.items(), key=lambda kv: kv[1]["rank"])[:limit]

    created: list[Task] = []
    for loc_id, info in ordered:
        task = Task(
            tenant_id=tenant_id, warehouse_id=warehouse_id,
            task_type=TaskType.COUNT, status=TaskStatus.PENDING,
            priority=40 + (3 - info["rank"]) * 10,   # A yuqoriroq ustuvorlik
            payload={"location_id": str(loc_id), "location_code": info["code"]},
        )
        db.add(task)
        created.append(task)
    await db.flush()
    return created


async def record_count(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    location_id: uuid.UUID,
    counted: list[tuple[uuid.UUID, uuid.UUID | None, int]],  # (product_id, batch_id, counted_qty)
    user_id: uuid.UUID | None,
    document_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
) -> list[CountVariance]:
    """Sanoq natijasini kutilgan bilan solishtiradi, farqni ledgerga tuzatadi,
    COUNT taskni yopadi. Farqlar ro'yxatini qaytaradi."""
    variances: list[CountVariance] = []
    for product_id, batch_id, counted_qty in counted:
        stock = (await db.execute(
            select(StockItem).where(
                StockItem.location_id == location_id,
                StockItem.product_id == product_id,
                StockItem.batch_id == batch_id,
            ).with_for_update()
        )).scalar_one_or_none()
        expected = stock.qty if stock else 0
        diff = counted_qty - expected
        if diff == 0:
            continue
        variances.append(CountVariance(product_id, batch_id, expected, counted_qty, diff))
        action = LedgerAction.INVENTORY_PLUS if diff > 0 else LedgerAction.INVENTORY_MINUS
        # Ijobiy farq → to_location, salbiy → from_location (ledger keshni to'g'ri
        # yangilashi uchun qty_delta ishorasiga mos joyni beramiz).
        loc_kw = {"to_location_id": location_id} if diff > 0 else {"from_location_id": location_id}
        await ledger_svc.record(
            db, tenant_id=tenant_id, warehouse_id=warehouse_id,
            action=action, qty_delta=diff,
            product_id=product_id, batch_id=batch_id,
            user_id=user_id, document_id=document_id, reason="cycle_count",
            extra={"expected": expected, "counted": counted_qty}, **loc_kw,
        )

    if task_id is not None:
        task = await db.get(Task, task_id)
        if task is not None and task.tenant_id == tenant_id:
            task.status = TaskStatus.COMPLETED
    await db.flush()
    return variances


async def variance_summary(
    db: AsyncSession, *, warehouse_id: uuid.UUID,
) -> dict:
    """INVENTORY_PLUS/MINUS ledger yozuvlaridan umumiy farq statistikasi."""
    rows = (await db.execute(
        select(LedgerEntry.action, func.count(), func.sum(func.abs(LedgerEntry.qty_delta)))
        .where(
            LedgerEntry.warehouse_id == warehouse_id,
            LedgerEntry.action.in_([LedgerAction.INVENTORY_PLUS, LedgerAction.INVENTORY_MINUS]),
        )
        .group_by(LedgerEntry.action)
    )).all()
    summary = {"plus_count": 0, "plus_units": 0, "minus_count": 0, "minus_units": 0}
    for action, cnt, units in rows:
        if action == LedgerAction.INVENTORY_PLUS:
            summary["plus_count"], summary["plus_units"] = int(cnt), int(units or 0)
        else:
            summary["minus_count"], summary["minus_units"] = int(cnt), int(units or 0)
    summary["total_adjustments"] = summary["plus_count"] + summary["minus_count"]
    summary["net_units"] = summary["plus_units"] - summary["minus_units"]
    return summary
