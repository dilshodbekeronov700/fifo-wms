"""Fon workerlar uchun heartbeat registri — /health/ready tekshiruvida ishlatiladi.

Har bir worker o'z sikli boshida `heartbeat("outbox")` chaqiradi. /health/ready
oxirgi heartbeat yoshini WORKER_HEARTBEAT_MAX_AGE bilan solishtiradi — worker qotib
qolgan yoki o'lgan bo'lsa readiness "degraded" bo'ladi (orkestrator qayta ishga
tushirishi mumkin). Jarayon-lokal (in-memory) — bitta instans uchun yetarli.
"""
from __future__ import annotations

import time

_heartbeats: dict[str, float] = {}


def heartbeat(name: str) -> None:
    _heartbeats[name] = time.time()


def snapshot() -> dict[str, float]:
    """{worker_nomi: oxirgi_heartbeat_yoshi_soniyada}."""
    now = time.time()
    return {name: now - ts for name, ts in _heartbeats.items()}
