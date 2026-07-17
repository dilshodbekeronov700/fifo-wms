"""Schemas for movement, inventory count, write-off, return, reconciliation."""
from __future__ import annotations
import uuid
from pydantic import BaseModel


# ─── Internal Movement ──────────────────────────────────────────────────────

class MovementLine(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    qty: int
    marking_codes: list[str] = []


class MovementCreate(BaseModel):
    warehouse_id: uuid.UUID
    from_location_id: uuid.UUID
    to_location_id: uuid.UUID
    lines: list[MovementLine]
    reason: str | None = None
    sync_smartup: bool = False  # also report the move to Smartup (mkw/movement$import)


class MovementOut(BaseModel):
    document_id: uuid.UUID
    status: str
    lines_moved: int
    smartup_enqueued: bool = False


# ─── Replenishment suggestion (reserve -> pick face) ─────────────────────────

class ReplenishmentSuggestion(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    from_location_id: uuid.UUID   # reserve location
    from_location_code: str
    to_location_id: uuid.UUID     # pick location
    to_location_code: str
    suggested_qty: int            # how much to move
    pick_qty: int                 # current qty at the pick face
    reserve_qty: int              # current qty in the reserve location


class ReplenishmentOut(BaseModel):
    warehouse_id: uuid.UUID
    suggestions: list[ReplenishmentSuggestion]


# ─── Inventory Count ────────────────────────────────────────────────────────

class CountLine(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    location_id: uuid.UUID
    counted_qty: int
    marking_codes: list[str] = []


class InventoryCountCreate(BaseModel):
    warehouse_id: uuid.UUID
    lines: list[CountLine]
    count_type: str = "cycle"  # "full" | "cycle"
    notes: str | None = None


class CountDiscrepancy(BaseModel):
    product_id: uuid.UUID
    location_id: uuid.UUID
    expected_qty: int
    counted_qty: int
    diff: int


class InventoryCountOut(BaseModel):
    document_id: uuid.UUID
    status: str
    discrepancies: list[CountDiscrepancy]
    smartup_synced: bool


# ─── Write-Off ──────────────────────────────────────────────────────────────

class WriteoffLine(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    location_id: uuid.UUID
    qty: int
    marking_codes: list[str] = []
    reason_code: str  # e.g. "damage", "expired", "lost"


class WriteoffCreate(BaseModel):
    warehouse_id: uuid.UUID
    lines: list[WriteoffLine]
    notes: str | None = None


class WriteoffOut(BaseModel):
    document_id: uuid.UUID
    status: str
    smartup_synced: bool


# ─── Return (Vozvrat) ────────────────────────────────────────────────────────

class ReturnLine(BaseModel):
    product_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    qty: int
    marking_codes: list[str] = []


class ReturnCreate(BaseModel):
    warehouse_id: uuid.UUID
    to_location_id: uuid.UUID
    smartup_return_id: str | None = None
    lines: list[ReturnLine]
    disposition: str = "restock"  # restock | quarantine | writeoff
    notes: str | None = None


class ReturnOut(BaseModel):
    document_id: uuid.UUID
    status: str
    disposition: str
    ledger_action: str  # RETURN_IN | WRITEOFF
    lines_returned: int


# ─── Reconciliation ─────────────────────────────────────────────────────────

class ReconciliationLineOut(BaseModel):
    smartup_product_code: str
    product_id: uuid.UUID | None
    wms_qty: int
    smartup_qty: int
    diff: int
    direction: str


class ReconciliationOut(BaseModel):
    warehouse_id: uuid.UUID
    total_lines: int
    match_count: int
    discrepancy_count: int
    lines: list[ReconciliationLineOut]
