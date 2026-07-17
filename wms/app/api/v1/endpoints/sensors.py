"""
IoT sensorlar — harorat/namlik (ESP32 + DHT-21).

Ingest (qurilmadan):
  POST /sensors/ingest        — device_key bilan, auth talab qilmaydi (API-key sifatida device_key)
O'qish (UI):
  GET  /sensors               — sensorlar ro'yxati (oxirgi qiymat + holat)
  POST /sensors               — sensor qo'shish
  PATCH/DELETE /sensors/{id}
  GET  /sensors/{id}/history  — tarix (grafik uchun)
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ActiveUser, get_db, require_permission
from app.models.sensor import Sensor, SensorReading

router = APIRouter(prefix="/sensors", tags=["sensors"])
DB = Annotated[AsyncSession, Depends(get_db)]


# ─── Schemas ──────────────────────────────────────────────────────────────────
class IngestBody(BaseModel):
    device_key: str
    temperature: float | None = None
    humidity: float | None = None


class SensorCreate(BaseModel):
    name: str
    device_key: str
    warehouse_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    sensor_type: str = "dht21"
    temp_min: float | None = 5.0
    temp_max: float | None = 25.0
    hum_min: float | None = None
    hum_max: float | None = 80.0


class SensorUpdate(BaseModel):
    name: str | None = None
    zone_id: uuid.UUID | None = None
    temp_min: float | None = None
    temp_max: float | None = None
    hum_min: float | None = None
    hum_max: float | None = None
    is_active: bool | None = None


def _status(s: Sensor) -> str:
    """online / offline / alert / no-data."""
    if s.last_seen is None:
        return "no-data"
    age = (datetime.now(timezone.utc) - s.last_seen).total_seconds()
    if age > 300:  # 5 daqiqa ko'rinmasa — offline
        return "offline"
    t, h = s.last_temp, s.last_hum
    if t is not None and ((s.temp_min is not None and t < s.temp_min) or (s.temp_max is not None and t > s.temp_max)):
        return "alert"
    if h is not None and ((s.hum_min is not None and h < s.hum_min) or (s.hum_max is not None and h > s.hum_max)):
        return "alert"
    return "online"


def _out(s: Sensor) -> dict:
    return {
        "id": str(s.id), "name": s.name, "device_key": s.device_key,
        "warehouse_id": str(s.warehouse_id) if s.warehouse_id else None,
        "zone_id": str(s.zone_id) if s.zone_id else None,
        "sensor_type": s.sensor_type,
        "temp_min": s.temp_min, "temp_max": s.temp_max, "hum_min": s.hum_min, "hum_max": s.hum_max,
        "last_temp": s.last_temp, "last_hum": s.last_hum,
        "last_seen": s.last_seen.isoformat() if s.last_seen else None,
        "status": _status(s), "is_active": s.is_active,
    }


# ─── Ingest (qurilmadan — device_key auth) ───────────────────────────────────
@router.post("/ingest")
async def ingest(body: IngestBody, db: DB):
    key = (body.device_key or "").strip()   # bo'sh joylarni tozalaymiz (mos kelmaslik oldini olish)
    sensor = (await db.execute(
        select(Sensor).where(func.trim(Sensor.device_key) == key).order_by(Sensor.created_at)
    )).scalars().first()   # dublikat kalit bo'lsa ham birinchisini olamiz (500 oldini olish)
    if sensor is None:
        raise HTTPException(status_code=404, detail="Unknown device_key")
    now = datetime.now(timezone.utc)
    db.add(SensorReading(
        sensor_id=sensor.id, temperature=body.temperature, humidity=body.humidity, recorded_at=now,
    ))
    sensor.last_temp = body.temperature
    sensor.last_hum = body.humidity
    sensor.last_seen = now
    await db.commit()
    return {"ok": True, "status": _status(sensor)}


# ─── UI ───────────────────────────────────────────────────────────────────────
@router.get("/", dependencies=[require_permission("analytics", "view")])
async def list_sensors(user: ActiveUser, db: DB, warehouse_id: uuid.UUID | None = None):
    q = select(Sensor).where(Sensor.tenant_id == user.tenant_id, Sensor.is_active.is_(True))
    if warehouse_id:
        q = q.where(Sensor.warehouse_id == warehouse_id)
    rows = (await db.execute(q)).scalars().all()
    return [_out(s) for s in rows]


@router.post("/", status_code=201, dependencies=[require_permission("analytics", "view")])
async def create_sensor(body: SensorCreate, user: ActiveUser, db: DB):
    data = body.model_dump()
    key = (data.get("device_key") or "").strip()
    data["device_key"] = key
    # Bu device_key allaqachon bormi? (unique) — aniq xabar beramiz (500 emas)
    dup = (await db.execute(
        select(Sensor).where(func.trim(Sensor.device_key) == key)
    )).scalars().first()
    if dup is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Bu device_key allaqachon ishlatilgan: \"{dup.name}\". Mavjud sensorни ishlating yoki boshqa key bering.",
        )
    s = Sensor(tenant_id=user.tenant_id, **data)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return _out(s)


@router.patch("/{sensor_id}", dependencies=[require_permission("analytics", "view")])
async def update_sensor(sensor_id: uuid.UUID, body: SensorUpdate, user: ActiveUser, db: DB):
    s = await db.get(Sensor, sensor_id)
    if s is None or s.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Sensor not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    await db.commit()
    await db.refresh(s)
    return _out(s)


@router.delete("/{sensor_id}", status_code=204, dependencies=[require_permission("analytics", "view")])
async def delete_sensor(sensor_id: uuid.UUID, user: ActiveUser, db: DB):
    s = await db.get(Sensor, sensor_id)
    if s is None or s.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Sensor not found")
    s.is_active = False
    await db.commit()


@router.get("/{sensor_id}/history", dependencies=[require_permission("analytics", "view")])
async def history(sensor_id: uuid.UUID, user: ActiveUser, db: DB, hours: int = 24):
    s = await db.get(Sensor, sensor_id)
    if s is None or s.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Sensor not found")
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (await db.execute(
        select(SensorReading).where(
            SensorReading.sensor_id == sensor_id, SensorReading.recorded_at >= since,
        ).order_by(SensorReading.recorded_at)
    )).scalars().all()
    return [
        {"t": r.recorded_at.isoformat(), "temp": r.temperature, "hum": r.humidity}
        for r in rows
    ]
