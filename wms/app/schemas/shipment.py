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
    product_price: float | None = None
    price_type_code: str | None = None
    vat_percent: float | None = None
    batch_number: str | None = None
    warehouse_code: str | None = None
    sold_amount: float | None = None


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
    # Smartup "Заказы" ustunlari
    working_zone: str | None = None
    payment_type_code: str | None = None
    price_type_code: str | None = None
    delivery_address: str | None = None
    delivery_number: str | None = None
    contract_number: str | None = None
    note: str | None = None
    discount_value: float | None = None
    discount_kind: str | None = None
    weight_netto: float | None = None
    weight_brutto: float | None = None
    litre: float | None = None
    sales_manager_name: str | None = None
    expeditor_name: str | None = None
    driver_name: str | None = None
    self_shipment: str | None = None
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
    product_name: str | None = None       # Smartup nomi (mapping yo'q qatorларni ko'rsatish uchun)
    product_unit_id: str | None = None
    uom: str | None = None                 # buyurtma birligi (UNIT/dona → quti'ga aylantiramiz)
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
    product_code: str | None = None
    product_name: str | None = None
    take_qty: int
    marking_codes: list[str]
    is_partial_pallet: bool
    # FEFO/FIFO manba ma'lumotlari (Asl Belgisidan kelgan partiya) — yig'uvchiga ko'rsatiladi.
    lot_number: str | None = None
    production_date: str | None = None
    expiry_date: str | None = None


class ValidationIssue(BaseModel):
    order_line_id: str
    kind: str           # "unmapped_gtin" | "unmapped_product" | "over_pick" | "shortfall"
    detail: str
    requested: int | None = None
    available: int | None = None
    product_code: str | None = None     # yig'uvchiga ko'rsatish uchun (qaysi mahsulot)
    product_name: str | None = None
    gtin: str | None = None


class PickTaskOut(BaseModel):
    document_id: uuid.UUID
    task_id: uuid.UUID | None
    deal_id: str
    shortfall_lines: list[str]          # order_line_ids with qty shortfall
    issues: list[ValidationIssue] = []
    route: list[PickStop] = []
    # Tanlangan skladda qoldiq bo'lmasa — tovarlar QAYSI skladda borligi (bir bosishda o'tish uchun)
    alt_warehouse: dict | None = None


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
