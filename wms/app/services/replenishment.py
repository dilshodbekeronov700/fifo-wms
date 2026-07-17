"""
Replenishment engine — reserve zonadan pick-face'ni to'ldirish.

Professional WMS'da pick-face (terish yuzasi) tovar tugab qolmasligi uchun
avtomatik to'ldiriladi. Trigger — SKU'ning `min_stock` darajasi (safety stock):
pick-face qty shu darajaga tushsa, `max_stock` (target)gacha ko'tariladi.
`min_stock` o'rnatilmagan bo'lsa, arzon `threshold` parametri ishlatiladi.

Manba — RESERVE zonadagi eng ko'p mavjud stok. Ko'chirish miqdori =
min(kerak, reserve'da mavjud). Har taklif REPLENISH Task sifatida yozilishi
mumkin (operator TSD'da bajaradi), yoki darhol MOVE ledger yozuvi bilan bajariladi.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import Product, StockItem, StockStatus
from app.models.ledger import LedgerAction
from app.models.task import Task, TaskStatus, TaskType
from app.models.warehouse import Location, Zone, ZoneType
from app.services import ledger as ledger_svc


@dataclass
class ReplenishSuggestion:
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    from_location_id: uuid.UUID
    from_location_code: str
    to_location_id: uuid.UUID
    to_location_code: str
    move_qty: int
    pick_qty: int          # pick-face hozirgi miqdori
    reserve_qty: int       # manbada mavjud
    target: int            # to'ldirishdan keyingi maqsad daraja
    reason: str            # "min_stock" | "threshold"


async def compute_replenishments(
    db: AsyncSession,
    *,
    warehouse_id: uuid.UUID,
    threshold: int = 0,
) -> list[ReplenishSuggestion]:
    """Pick-face pastga tushgan SKU'lar uchun reserve→pick to'ldirish takliflari."""
    rows = (await db.execute(
        select(StockItem, Location.code, Zone.zone_type)
        .join(Location, StockItem.location_id == Location.id)
        .join(Zone, Location.zone_id == Zone.id)
        .where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.status == StockStatus.AVAILABLE,
        )
    )).all()

    pick_faces: dict[tuple, tuple] = {}       # key -> (stock, code)
    reserves: dict[tuple, list[tuple]] = {}   # key -> [(stock, code)]
    for stock, code, ztype in rows:
        key = (stock.product_id, stock.batch_id)
        if ztype == ZoneType.PICK:
            if key not in pick_faces or stock.qty < pick_faces[key][0].qty:
                pick_faces[key] = (stock, code)
        elif ztype == ZoneType.RESERVE:
            reserves.setdefault(key, []).append((stock, code))

    # Kerakli mahsulotlarning min/max darajalarini bir marta yuklaymiz.
    product_ids = {k[0] for k in pick_faces}
    products: dict[uuid.UUID, Product] = {}
    if product_ids:
        for p in (await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )).scalars():
            products[p.id] = p

    out: list[ReplenishSuggestion] = []
    for key, (pick_stock, pick_code) in pick_faces.items():
        product = products.get(key[0])
        min_stock = product.min_stock if product else None
        max_stock = product.max_stock if product else None

        if min_stock is not None:
            if pick_stock.qty > min_stock:
                continue
            target = max_stock if (max_stock and max_stock > min_stock) else min_stock
            reason = "min_stock"
        else:
            if pick_stock.qty > threshold:
                continue
            target = None       # threshold rejimida reserve'dagi hammasini ko'chiramiz
            reason = "threshold"

        reserve_list = reserves.get(key)
        if not reserve_list:
            continue
        reserve_stock, reserve_code = max(reserve_list, key=lambda r: r[0].qty)
        reserve_avail = reserve_stock.qty - reserve_stock.qty_booked
        if reserve_avail <= 0:
            continue

        need = (target - pick_stock.qty) if target is not None else reserve_avail
        move_qty = min(need, reserve_avail)
        if move_qty <= 0:
            continue

        out.append(ReplenishSuggestion(
            product_id=key[0], batch_id=key[1],
            from_location_id=reserve_stock.location_id, from_location_code=reserve_code,
            to_location_id=pick_stock.location_id, to_location_code=pick_code,
            move_qty=move_qty, pick_qty=pick_stock.qty, reserve_qty=reserve_stock.qty,
            target=target if target is not None else pick_stock.qty + move_qty,
            reason=reason,
        ))
    return out


async def generate_tasks(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    suggestions: list[ReplenishSuggestion],
    priority: int = 60,
) -> list[Task]:
    """Takliflardan REPLENISH tasklar yaratadi (bir xil manba→maqsad uchun
    ochiq task bo'lsa takrorlamaydi)."""
    existing = (await db.execute(
        select(Task).where(
            Task.warehouse_id == warehouse_id,
            Task.task_type == TaskType.REPLENISH,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]),
        )
    )).scalars().all()
    open_keys = {
        (t.payload.get("product_id"), t.payload.get("from_location_id"),
         t.payload.get("to_location_id"))
        for t in existing
    }

    created: list[Task] = []
    for s in suggestions:
        key = (str(s.product_id), str(s.from_location_id), str(s.to_location_id))
        if key in open_keys:
            continue
        task = Task(
            tenant_id=tenant_id, warehouse_id=warehouse_id,
            task_type=TaskType.REPLENISH, status=TaskStatus.PENDING, priority=priority,
            payload={
                "product_id": str(s.product_id),
                "batch_id": str(s.batch_id) if s.batch_id else None,
                "from_location_id": str(s.from_location_id),
                "to_location_id": str(s.to_location_id),
                "move_qty": s.move_qty, "reason": s.reason, "target": s.target,
            },
        )
        db.add(task)
        created.append(task)
        open_keys.add(key)
    await db.flush()
    return created


async def execute_move(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    product_id: uuid.UUID,
    batch_id: uuid.UUID | None,
    from_location_id: uuid.UUID,
    to_location_id: uuid.UUID,
    qty: int,
    user_id: uuid.UUID | None,
    task_id: uuid.UUID | None = None,
) -> None:
    """Reserve→pick fizik ko'chirishni ledgerga yozadi (MOVE) va, agar berilgan
    bo'lsa, tegishli REPLENISH taskni COMPLETED qiladi. Manbada yetarli mavjud
    stok borligini qulflab tekshiradi (over-move'ning oldini oladi)."""
    if qty <= 0:
        raise ValueError("qty must be positive")

    src = (await db.execute(
        select(StockItem).where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.location_id == from_location_id,
            StockItem.product_id == product_id,
            StockItem.batch_id == batch_id,
        ).with_for_update()
    )).scalar_one_or_none()
    if src is None or (src.qty - src.qty_booked) < qty:
        raise ValueError("insufficient_reserve_stock")

    await ledger_svc.record(
        db, tenant_id=tenant_id, warehouse_id=warehouse_id,
        action=LedgerAction.MOVE, qty_delta=-qty,
        product_id=product_id, batch_id=batch_id,
        from_location_id=from_location_id, user_id=user_id, reason="replenishment",
    )
    await ledger_svc.record(
        db, tenant_id=tenant_id, warehouse_id=warehouse_id,
        action=LedgerAction.MOVE, qty_delta=qty,
        product_id=product_id, batch_id=batch_id,
        to_location_id=to_location_id, user_id=user_id, reason="replenishment",
    )

    if task_id is not None:
        task = await db.get(Task, task_id)
        if task is not None and task.tenant_id == tenant_id:
            task.status = TaskStatus.COMPLETED
    await db.flush()
