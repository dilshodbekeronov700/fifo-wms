"""Faza C — replenishment, cycle-count, wave, RMA uchun so'rov/javob sxemalari."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


# ─── Replenishment ────────────────────────────────────────────────────────────
class ReplenishItem(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    from_location_id: uuid.UUID
    from_location_code: str
    to_location_id: uuid.UUID
    to_location_code: str
    move_qty: int
    pick_qty: int
    reserve_qty: int
    target: int
    reason: str


class ReplenishPlanOut(BaseModel):
    warehouse_id: uuid.UUID
    suggestions: list[ReplenishItem]


class ReplenishGenerateOut(BaseModel):
    created: int
    task_ids: list[uuid.UUID]


class ReplenishExecuteIn(BaseModel):
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    from_location_id: uuid.UUID
    to_location_id: uuid.UUID
    qty: int = Field(gt=0)
    task_id: uuid.UUID | None = None


# ─── Cycle count ──────────────────────────────────────────────────────────────
class CycleGenerateIn(BaseModel):
    warehouse_id: uuid.UUID
    limit: int = Field(default=20, ge=1, le=200)


class CycleTaskOut(BaseModel):
    task_id: uuid.UUID
    location_id: uuid.UUID
    location_code: str
    priority: int


class CycleGenerateOut(BaseModel):
    created: int
    tasks: list[CycleTaskOut]


class CycleCountLine(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    counted_qty: int = Field(ge=0)


class CycleRecordIn(BaseModel):
    warehouse_id: uuid.UUID
    location_id: uuid.UUID
    lines: list[CycleCountLine]
    task_id: uuid.UUID | None = None


class CycleVarianceOut(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    expected: int
    counted: int
    diff: int


class CycleRecordOut(BaseModel):
    variances: list[CycleVarianceOut]


# ─── Wave picking ─────────────────────────────────────────────────────────────
class WaveLineIn(BaseModel):
    order_line_id: str
    product_id: uuid.UUID
    requested_boxes: int = Field(gt=0)
    order_id: str | None = None


class WavePlanIn(BaseModel):
    warehouse_id: uuid.UUID
    lines: list[WaveLineIn]


class WaveInstructionOut(BaseModel):
    order_id: str | None
    order_line_id: str
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    take_qty: int
    marking_codes: list[str]


class WaveStopOut(BaseModel):
    sequence: int
    location_id: uuid.UUID
    location_code: str
    instructions: list[WaveInstructionOut]


class WavePlanOut(BaseModel):
    warehouse_id: uuid.UUID
    stops: list[WaveStopOut]
    shortfalls: dict[str, int]
    total_lines: int
    total_boxes: int


# ─── RMA ──────────────────────────────────────────────────────────────────────
class RmaLineIn(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    qty: int = Field(gt=0)
    disposition: str  # restock | quarantine | scrap
    location_id: uuid.UUID | None = None
    marking_codes: list[str] | None = None


class RmaCreateIn(BaseModel):
    warehouse_id: uuid.UUID
    lines: list[RmaLineIn]
    external_id: str | None = None
    notes: str | None = None


class RmaOut(BaseModel):
    document_id: uuid.UUID
    restocked: int
    quarantined: int
    scrapped: int
