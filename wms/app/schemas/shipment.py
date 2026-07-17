from __future__ import annotations
import uuid
from pydantic import BaseModel


# ── Orders (pull from Smartup for the manager) ───────────────────────────────

class ShipmentOrderLine(BaseModel):
    product_unit_id: str
    product_code: str
    gtin: str | None = None
    product_name: str | None = None       # WMS Product'dan boyitiladi
    expiry_date: str | None = None        # Smartup qatoridan (FEFO)
    qty_ordered: float
    uom: str
    product_id: uuid.UUID | None = None   # resolved WMS product (None = unmapped)
    available_boxes: int | None = None     # current free stock for this SKU


class ShipmentOrder(BaseModel):
    deal_id: str
    order_number: str
    status: str
    customer_tin: str | None = None
    customer_name: str | None = None
    total_amount: float | None = None
    order_date: str | None = None
    delivery_date: str | None = None
    with_marking: str | None = None
    lines: list[ShipmentOrderLine] = []


# ── Pick task creation ───────────────────────────────────────────────────────

class OrderLineIn(BaseModel):
    """One line from a Smartup order, translated to WMS terms.

    Either `product_id` or `gtin` must resolve to a WMS product. When created
    from a Smartup deal_id the lines are filled in automatically.
    """
    order_line_id: str
    product_id: uuid.UUID | None = None
    gtin: str | None = None
    product_code: str | None = None       # Smartup product_code (asosiy mapping kaliti)
    product_unit_id: str | None = None
    requested_boxes: int


class PickTaskCreate(BaseModel):
    warehouse_id: uuid.UUID
    smartup_deal_id: str
    # Optional explicit lines; if omitted, lines are pulled from the Smartup deal.
    lines: list[OrderLineIn] = []


class PickStop(BaseModel):
    sequence: int
    location_id: uuid.UUID
    location_code: str
    product_id: uuid.UUID
    take_qty: int
    marking_codes: list[str]
    is_partial_pallet: bool


class ValidationIssue(BaseModel):
    order_line_id: str
    kind: str           # "unmapped_gtin" | "over_pick" | "shortfall"
    detail: str
    requested: int | None = None
    available: int | None = None


class PickTaskOut(BaseModel):
    document_id: uuid.UUID
    task_id: uuid.UUID | None
    deal_id: str
    shortfall_lines: list[str]          # order_line_ids with qty shortfall
    issues: list[ValidationIssue] = []
    route: list[PickStop] = []


# ── Scan validation (TSD) ────────────────────────────────────────────────────

class ScanValidateRequest(BaseModel):
    """TSD sends scanned code; server validates against open pick task."""
    task_id: uuid.UUID
    scanned_code: str
    location_id: uuid.UUID | None = None


class ScanValidateResponse(BaseModel):
    accepted: bool
    reason: str | None = None
    task_completed: bool = False
    package_type: str | None = None
    gtin: str | None = None
    remaining: int | None = None        # codes still to scan for this task


# ── Confirm shipment ─────────────────────────────────────────────────────────

class ShipmentConfirmRequest(BaseModel):
    document_id: uuid.UUID


class ShipmentConfirmResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    codes_attached: int
    smartup_enqueued: bool
    disaggregation_enqueued: int = 0     # how many partial-pallet docs queued
