"""
Wave picking — bir nechta buyurtmani bitta "to'lqin"ga birlashtirib terish.

Har buyurtmani alohida terish o'rniga, ularni birlashtirib, yacheyka bo'yicha
guruhlab, S-shaklidagi marshrutda tartiblangan YAGONA terish ro'yxatini beramiz.
Operator har yacheykaga bir marta boradi va u yerdan barcha buyurtmalar uchun
kerakli qutilarni oladi — yurish masofasi keskin kamayadi.

Bu bosqich REJALASHTIRISH (read-only) — stokni band qilmaydi. Bajarish mavjud
shipment/pick oqimi orqali amalga oshiriladi. FEFO/FIFO tartibi
`picking.build_pick_plan` orqali saqlanadi.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import picking as picking_svc
from app.services.route_optimizer import optimise_route


@dataclass
class WaveLineRequest:
    order_line_id: str
    product_id: uuid.UUID
    requested_boxes: int
    order_id: str | None = None


@dataclass
class WavePickInstruction:
    order_id: str | None
    order_line_id: str
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    take_qty: int
    marking_codes: list[str]


@dataclass
class WaveStop:
    sequence: int
    location_id: uuid.UUID
    location_code: str
    instructions: list[WavePickInstruction] = field(default_factory=list)


@dataclass
class WavePlan:
    warehouse_id: uuid.UUID
    stops: list[WaveStop]
    shortfalls: dict[str, int]           # order_line_id -> ta'minlanmagan qutilar
    total_lines: int
    total_boxes: int


async def build_wave_plan(
    db: AsyncSession,
    *,
    warehouse_id: uuid.UUID,
    lines: list[WaveLineRequest],
) -> WavePlan:
    """Bir nechta buyurtma qatoridan birlashtirilgan, marshrutlangan terish rejasi."""
    by_location: dict[uuid.UUID, WaveStop] = {}
    location_objs: dict[uuid.UUID, object] = {}
    shortfalls: dict[str, int] = {}
    total_boxes = 0

    for ln in lines:
        plan = await picking_svc.build_pick_plan(
            db, warehouse_id=warehouse_id, product_id=ln.product_id,
            order_line_id=ln.order_line_id, requested_boxes=ln.requested_boxes,
        )
        if plan.shortfall > 0:
            shortfalls[ln.order_line_id] = plan.shortfall
        for al in plan.allotments:
            loc = al.location
            location_objs.setdefault(loc.id, loc)
            stop = by_location.get(loc.id)
            if stop is None:
                stop = by_location[loc.id] = WaveStop(
                    sequence=0, location_id=loc.id, location_code=loc.code,
                )
            stop.instructions.append(WavePickInstruction(
                order_id=ln.order_id, order_line_id=ln.order_line_id,
                product_id=ln.product_id, batch_id=al.stock_item.batch_id,
                take_qty=al.take_qty, marking_codes=al.marking_codes,
            ))
            total_boxes += al.take_qty

    # Yacheykalarni S-shaklidagi marshrutda tartiblaymiz.
    ordered = optimise_route([location_objs[lid] for lid in by_location])
    stops: list[WaveStop] = []
    for rs in ordered:
        stop = by_location[rs.location.id]
        stop.sequence = rs.sequence
        stops.append(stop)

    return WavePlan(
        warehouse_id=warehouse_id, stops=stops, shortfalls=shortfalls,
        total_lines=len(lines), total_boxes=total_boxes,
    )
