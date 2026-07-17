"""Yengil async circuit breaker — tashqi connectorlar uchun.

Tenacity qayta urinish (retry) o'tkinchi xatolarni hal qiladi, lekin tashqi tizim
(Smartup / Asl Belgisi) uzoq vaqt ishlamay qolsa, har chaqiruv 3 marta urinib,
backoff bilan sekin cascadeli ishlamay qolishga olib keladi. Circuit breaker buni
to'xtatadi: ketma-ket N xatodan keyin "ochiladi" va RESET_SECONDS davomida DARHOL
CircuitOpenError bilan qaytaradi (tashqi tizimni ham, o'zimizni ham bo'shatadi).

Holatlar:
    CLOSED     — normal; xatolar sanaladi.
    OPEN       — fail-fast; reset vaqti tugagach HALF_OPEN.
    HALF_OPEN  — bitta sinov chaqiruvi; muvaffaqiyat → CLOSED, xato → yana OPEN.

Vaqt monotonic() orqali (Date.now emas) — test/monkeypatch uchun `_now` almashtiriladi.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.core.config import settings


class CircuitOpenError(Exception):
    """Circuit ochiq — chaqiruv urinilmadi (tashqi tizim ishlamayapti deb hisoblanadi)."""

    def __init__(self, name: str, retry_after: float) -> None:
        self.name = name
        self.retry_after = retry_after
        super().__init__(f"circuit '{name}' open; retry after ~{retry_after:.0f}s")


@dataclass
class CircuitBreaker:
    name: str
    fail_threshold: int = field(default_factory=lambda: settings.CIRCUIT_FAIL_THRESHOLD)
    reset_seconds: float = field(default_factory=lambda: settings.CIRCUIT_RESET_SECONDS)
    _now = staticmethod(time.monotonic)

    failures: int = 0
    opened_at: float | None = None
    half_open: bool = False

    def _time(self) -> float:
        return type(self)._now()

    def before_call(self) -> None:
        if self.opened_at is None:
            return
        elapsed = self._time() - self.opened_at
        if elapsed < self.reset_seconds:
            raise CircuitOpenError(self.name, self.reset_seconds - elapsed)
        # Reset vaqti tugadi — bitta sinov chaqiruviga ruxsat (half-open).
        self.half_open = True

    def on_success(self) -> None:
        self.failures = 0
        self.opened_at = None
        self.half_open = False

    def on_failure(self) -> None:
        if self.half_open:
            # Sinov chaqiruvi ham muvaffaqiyatsiz — yana ochamiz.
            self.opened_at = self._time()
            self.half_open = False
            return
        self.failures += 1
        if self.failures >= self.fail_threshold:
            self.opened_at = self._time()

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        if self.half_open:
            return "half_open"
        return "open"


# Kalit bo'yicha jarayon-lokal registr (connector turi + base_url).
_registry: dict[str, CircuitBreaker] = {}


def get_breaker(key: str) -> CircuitBreaker:
    br = _registry.get(key)
    if br is None:
        br = _registry[key] = CircuitBreaker(name=key)
    return br


def reset_all() -> None:
    """Testlar uchun — registrni tozalaydi."""
    _registry.clear()
