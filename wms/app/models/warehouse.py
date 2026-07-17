from __future__ import annotations
import uuid
from enum import Enum as PyEnum
from sqlalchemy import String, ForeignKey, Boolean, Float, Enum as SaEnum, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, uuidpk, created_at, updated_at


class ZoneType(str, PyEnum):
    RESERVE = "reserve"
    PICK = "pick"
    OPEN_PALLET = "open_pallet"
    STAGING = "staging"
    DOCK = "dock"
    QUARANTINE = "quarantine"
    RETURN = "return"


class LocationType(str, PyEnum):
    PALLET = "pallet"
    SHELF = "shelf"
    FLOOR = "floor"


class LocationStatus(str, PyEnum):
    EMPTY = "empty"
    OCCUPIED = "occupied"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500))
    smartup_warehouse_code: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    tenant: Mapped["Tenant"] = relationship(back_populates="warehouses")
    zones: Mapped[list["Zone"]] = relationship(back_populates="warehouse")


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[uuidpk]
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    zone_type: Mapped[ZoneType] = mapped_column(SaEnum(ZoneType), nullable=False)
    # Layout coordinates (for 2D map)
    x: Mapped[float | None] = mapped_column(Float)
    y: Mapped[float | None] = mapped_column(Float)
    width: Mapped[float | None] = mapped_column(Float)
    height: Mapped[float | None] = mapped_column(Float)
    # Whether mixed SKU/batch per location is allowed
    allow_mixed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Admin-editable putaway routing rules (UI-driven). Empty = accept everything.
    # Shape: {"blocked": bool, "abc": ["A"], "categories": ["19L"],
    #         "product_ids": [...], "min_volume_m3": .., "max_volume_m3": ..}
    putaway_rules: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    warehouse: Mapped["Warehouse"] = relationship(back_populates="zones")
    locations: Mapped[list["Location"]] = relationship(back_populates="zone")


class Location(Base):
    """Single storage cell / slot — e.g. A-01-03-02 (Row-Rack-Tier-Position)."""

    __tablename__ = "locations"

    id: Mapped[uuidpk]
    zone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("zones.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # human-readable, unique per warehouse
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True)  # Code128/QR on label
    location_type: Mapped[LocationType] = mapped_column(SaEnum(LocationType), nullable=False)
    status: Mapped[LocationStatus] = mapped_column(
        SaEnum(LocationStatus), default=LocationStatus.EMPTY, nullable=False
    )
    # Physical position
    row: Mapped[str | None] = mapped_column(String(20))
    rack: Mapped[int | None] = mapped_column(Integer)
    tier: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[int | None] = mapped_column(Integer)
    # Capacity
    max_weight_kg: Mapped[float | None] = mapped_column(Float)
    max_pallets: Mapped[int | None] = mapped_column(Integer)
    # Layout (for map rendering)
    x: Mapped[float | None] = mapped_column(Float)
    y: Mapped[float | None] = mapped_column(Float)
    # Physical geometry (map editor) — mm o'lchamlar, burilish (gradus), rack guruhi
    length_mm: Mapped[int | None] = mapped_column(Integer)
    width_mm: Mapped[int | None] = mapped_column(Integer)
    height_mm: Mapped[int | None] = mapped_column(Integer)
    rotation: Mapped[float | None] = mapped_column(Float)
    rack_group: Mapped[str | None] = mapped_column(String(50), index=True)
    extra: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    zone: Mapped["Zone"] = relationship(back_populates="locations")
