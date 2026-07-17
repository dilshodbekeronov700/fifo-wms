"""IoT sensorlar — harorat/namlik monitoringi (ESP32 + DHT-21)."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Float, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuidpk, created_at, updated_at


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[uuidpk]
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("warehouses.id"), index=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zones.id"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    device_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)  # ESP32 auth
    sensor_type: Mapped[str] = mapped_column(String(40), default="dht21", nullable=False)
    # Ogohlantirish chegaralari
    temp_min: Mapped[float | None] = mapped_column(Float, default=5.0)
    temp_max: Mapped[float | None] = mapped_column(Float, default=25.0)
    hum_min: Mapped[float | None] = mapped_column(Float)
    hum_max: Mapped[float | None] = mapped_column(Float, default=80.0)
    # Oxirgi o'qish (tez ko'rsatish uchun cache)
    last_temp: Mapped[float | None] = mapped_column(Float)
    last_hum: Mapped[float | None] = mapped_column(Float)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[uuidpk]
    sensor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sensors.id"), nullable=False, index=True)
    temperature: Mapped[float | None] = mapped_column(Float)
    humidity: Mapped[float | None] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        Index("ix_reading_sensor_time", "sensor_id", "recorded_at"),
    )
