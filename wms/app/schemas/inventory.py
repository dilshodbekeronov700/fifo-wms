from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.inventory import AbcClass, BatchStatus, PackageType, StockStatus


# ─── Product ───────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    smartup_product_code: str | None = None
    gtin: str | None = None
    name: dict  # {"ru": "...", "uz": "..."}
    uom: str = "unit"
    units_per_box: int | None = None
    boxes_per_pallet: int | None = None
    abc_class: AbcClass | None = None
    weight_kg: float | None = None
    volume_m3: float | None = None


class ProductUpdate(BaseModel):
    """Mahsulotni tahrirlash — barcha maydonlar ixtiyoriy (faqat berilganlari yangilanadi)."""
    smartup_product_code: str | None = None
    gtin: str | None = None
    name: dict | None = None
    uom: str | None = None
    units_per_box: int | None = None
    boxes_per_pallet: int | None = None
    abc_class: AbcClass | None = None
    weight_kg: float | None = None
    volume_m3: float | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    smartup_product_code: str | None
    gtin: str | None
    name: dict
    uom: str
    units_per_box: int | None
    boxes_per_pallet: int | None
    abc_class: AbcClass | None
    is_active: bool

    model_config = {"from_attributes": True}


# ─── Batch ──────────────────────────────────────────────────────────────────

class BatchCreate(BaseModel):
    lot_number: str | None = None
    production_date: str | None = None  # ISO date: "2025-01-15"
    expiry_date: str | None = None


class BatchOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    lot_number: str | None
    production_date: str | None
    expiry_date: str | None
    status: BatchStatus

    model_config = {"from_attributes": True}


# ─── Receipt (Kirim) ────────────────────────────────────────────────────────

class ReceiptCodeItem(BaseModel):
    """Single scanned transport code (SSCC / BOX_LV) from TSD."""
    code: str
    package_type: PackageType = PackageType.BOX_LV_1


class ReceiptCreate(BaseModel):
    warehouse_id: uuid.UUID
    codes: list[ReceiptCodeItem]
    notes: str | None = None


class ReceiptCodeResult(BaseModel):
    code: str
    package_type: PackageType
    gtin: str | None
    nested_count: int
    product_id: uuid.UUID | None
    batch_id: uuid.UUID | None
    ownership_ok: bool
    error: str | None


class ReceiptOut(BaseModel):
    document_id: uuid.UUID
    status: str
    results: list[ReceiptCodeResult]


# ─── Putaway ────────────────────────────────────────────────────────────────

class PutawayConfirm(BaseModel):
    task_id: uuid.UUID
    location_id: uuid.UUID  # operator skanlab tasdiqlagan yacheyka


class SlottingSuggestion(BaseModel):
    location_id: uuid.UUID
    location_code: str
    zone_name: str
    score: float
    reason: str


# ─── TSD Putaway ────────────────────────────────────────────────────────────

class TsdScanRequest(BaseModel):
    gtin: str
    warehouse_id: uuid.UUID
    qty: int = 1


class TsdSuggestionItem(BaseModel):
    location_id: uuid.UUID
    location_code: str
    zone_name: str
    score: float
    reason: str


class TsdScanResponse(BaseModel):
    task_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    suggestions: list[TsdSuggestionItem]


# ─── Pallet scan → putaway suggestion (TSD) ──────────────────────────────────

class PalletScanRequest(BaseModel):
    """TSD scans a transport/pallet code; backend resolves it via Asl Belgisi."""
    warehouse_id: uuid.UUID
    code: str
    top_n: int = 5


class ResolvedCodeOut(BaseModel):
    code: str
    ownership_ok: bool
    reason: str | None = None
    package_type: str | None = None
    product_group_id: int | None = None
    issuer_tin: str | None = None
    gtin: str | None = None
    expiry_date: str | None = None
    production_date: str | None = None
    box_count: int
    unit_count: int
    counting_method: str
    product_id: uuid.UUID | None = None
    product_name: dict | None = None
    batch_id: uuid.UUID | None = None
    children: list[str] = []


class SlotCandidateOut(BaseModel):
    location_id: uuid.UUID
    location_code: str
    zone_id: uuid.UUID
    zone_type: str
    score: float
    reason: str
    factors: dict[str, float] = {}
    remaining_boxes: int = 0


class PutawaySuggestionOut(BaseModel):
    resolved: ResolvedCodeOut
    suggested: SlotCandidateOut | None
    candidates: list[SlotCandidateOut]


# ─── Putaway reservation (bron) → confirm-by-scan ────────────────────────────

class ReserveRequest(BaseModel):
    """Operator accepted a slot (suggested or manual) → hold it.

    The TSD passes back the resolved snapshot from /scan-suggest so no second
    Asl Belgisi round-trip is needed (offline-friendly)."""
    warehouse_id: uuid.UUID
    code: str
    location_id: uuid.UUID
    product_id: uuid.UUID | None = None  # Mahsulot noma'lum bo'lsa None (force=True talab qilinadi)
    batch_id: uuid.UUID | None = None
    qty: int = 1
    unit_count: int = 0
    package_type: str | None = None
    score: float | None = None
    reason: str | None = None
    manual: bool = False
    force: bool = False
    payload: dict = {}


class ConfirmRequest(BaseModel):
    """Joylashni tasdiqlash — IKKI formatni ham qabul qiladi (APK versiya mosligi).

    Yangi oqim (reserve→confirm):  reservation_id + location_barcode
    Eski oqim (tsd-scan→confirm):  task_id + location_id
    Barchasi optional; endpoint qaysi to'plam to'liq bo'lsa, o'shani ishlatadi.
    """
    # Yangi (reservation-based)
    reservation_id: uuid.UUID | None = None
    location_barcode: str | None = None  # operator skanlagan yacheyka QR/DataMatrix
    # Eski (task-based) — backward-compat
    task_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None


class CancelRequest(BaseModel):
    reservation_id: uuid.UUID


class ReservationOut(BaseModel):
    id: uuid.UUID
    warehouse_id: uuid.UUID
    code: str
    package_type: str | None = None
    product_id: uuid.UUID | None = None
    batch_id: uuid.UUID | None = None
    qty: int
    unit_count: int
    location_id: uuid.UUID
    zone_id: uuid.UUID | None = None
    score: float | None = None
    reason: str | None = None
    manual: bool
    status: str
    expires_at: datetime | None = None
    confirmed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LocationOptionOut(BaseModel):
    location_id: uuid.UUID
    code: str
    barcode: str | None = None
    zone_id: uuid.UUID
    zone_type: str
    status: str
    remaining_boxes: int
    can_place: bool
    note: str | None = None


# ─── Stock ──────────────────────────────────────────────────────────────────

class StockItemOut(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    product_id: uuid.UUID
    batch_id: uuid.UUID | None
    qty: int
    qty_booked: int
    status: StockStatus
    pallet_open: bool

    model_config = {"from_attributes": True}
