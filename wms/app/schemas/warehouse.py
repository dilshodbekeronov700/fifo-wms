from __future__ import annotations
import uuid
from pydantic import BaseModel
from app.models.warehouse import ZoneType, LocationType, LocationStatus


class WarehouseCreate(BaseModel):
    name: str
    address: str | None = None
    smartup_warehouse_code: str | None = None


class WarehouseOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    address: str | None
    smartup_warehouse_code: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ZoneCreate(BaseModel):
    name: str
    zone_type: ZoneType
    allow_mixed: bool = False
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None


class SetRackCellsRequest(BaseModel):
    """Stellaj yacheykalarini idempotent o'rnatish: {base}-{etaj}-{joy} (etaj×joy grid)."""
    zone_id: uuid.UUID
    base_code: str
    tiers: int = 1       # etaj soni
    positions: int = 1   # har etajdagi joy soni


class ZoneUpdate(BaseModel):
    """Xarita muharriri — zona nomi/turi/koordinatasi (partial update)."""
    name: str | None = None
    zone_type: ZoneType | None = None
    allow_mixed: bool | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None


class ZoneOut(BaseModel):
    id: uuid.UUID
    warehouse_id: uuid.UUID
    name: str
    zone_type: ZoneType
    allow_mixed: bool
    is_active: bool
    putaway_rules: dict = {}
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None

    model_config = {"from_attributes": True}


class LocationCreate(BaseModel):
    code: str
    barcode: str | None = None
    location_type: LocationType = LocationType.PALLET
    row: str | None = None
    rack: int | None = None
    tier: int | None = None
    position: int | None = None
    max_weight_kg: float | None = None
    max_pallets: int | None = None
    x: float | None = None
    y: float | None = None
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    rotation: float | None = None
    rack_group: str | None = None


class LocationUpdate(BaseModel):
    """Xarita muharriri — barcha maydon ixtiyoriy (partial update)."""
    code: str | None = None
    barcode: str | None = None
    location_type: LocationType | None = None
    status: LocationStatus | None = None
    row: str | None = None
    rack: int | None = None
    tier: int | None = None
    position: int | None = None
    max_weight_kg: float | None = None
    max_pallets: int | None = None
    x: float | None = None
    y: float | None = None
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    rotation: float | None = None
    rack_group: str | None = None


class BulkLocationCreate(BaseModel):
    zone_id: uuid.UUID
    locations: list[LocationCreate]


class RackGenerateRequest(BaseModel):
    """Bitta rack/blokdan ko'plab yacheyka generatsiyasi."""
    zone_id: uuid.UUID
    rack_group: str                  # blok nomi, masalan "A"
    row: str | None = None           # qator yorlig'i (Q-1...)
    cols: int                        # ustunlar soni
    tiers: int = 3                   # etajlar
    positions: int = 2               # har katakda pallet
    x: float = 0.0                   # boshlang'ich X (m)
    y: float = 0.0                   # boshlang'ich Y (m)
    cell_w: float = 1.95             # katak kengligi (m)
    code_prefix: str | None = None   # kod prefiksi (default = rack_group)
    max_weight_kg: float | None = None
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None


class LocationOut(BaseModel):
    id: uuid.UUID
    zone_id: uuid.UUID
    code: str
    barcode: str | None
    location_type: LocationType
    status: LocationStatus
    row: str | None
    rack: int | None
    tier: int | None
    position: int | None
    max_weight_kg: float | None
    max_pallets: int | None
    x: float | None
    y: float | None
    length_mm: int | None
    width_mm: int | None
    height_mm: int | None
    rotation: float | None
    rack_group: str | None
    is_active: bool

    model_config = {"from_attributes": True}
