"""Circuit breaker holat mashinasi testlari (soatni monkeypatch bilan boshqarib)."""
import pytest

from app.core.circuit import CircuitBreaker, CircuitOpenError


class _Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def _make(threshold=3, reset=60):
    clk = _Clock()
    br = CircuitBreaker(name="test", fail_threshold=threshold, reset_seconds=reset)
    br._now = clk  # instansda staticmethod'ni almashtiramiz
    # type(self)._now ishlatilgani uchun klassni ham vaqtincha almashtiramiz
    CircuitBreaker._now = staticmethod(clk)
    return br, clk


def teardown_function():
    import time
    CircuitBreaker._now = staticmethod(time.monotonic)


def test_opens_after_threshold_failures():
    br, clk = _make(threshold=3)
    assert br.state == "closed"
    br.before_call(); br.on_failure()
    br.before_call(); br.on_failure()
    assert br.state == "closed"
    br.before_call(); br.on_failure()
    assert br.state == "open"
    # Ochiq holatda chaqiruv darhol rad etiladi.
    with pytest.raises(CircuitOpenError):
        br.before_call()


def test_success_resets_failure_count():
    br, clk = _make(threshold=3)
    br.before_call(); br.on_failure()
    br.before_call(); br.on_failure()
    br.before_call(); br.on_success()   # muvaffaqiyat hisoblagichni nolga tushiradi
    assert br.failures == 0
    br.before_call(); br.on_failure()
    assert br.state == "closed"


def test_half_open_recovers_on_success():
    br, clk = _make(threshold=1, reset=60)
    br.before_call(); br.on_failure()
    assert br.state == "open"
    clk.advance(61)                      # reset vaqti o'tdi
    br.before_call()                     # half-open sinov chaqiruviga ruxsat
    assert br.half_open is True
    br.on_success()
    assert br.state == "closed"


def test_half_open_reopens_on_failure():
    br, clk = _make(threshold=1, reset=60)
    br.before_call(); br.on_failure()
    clk.advance(61)
    br.before_call()                     # half-open
    br.on_failure()                      # sinov ham muvaffaqiyatsiz → yana ochiladi
    assert br.state == "open"
    with pytest.raises(CircuitOpenError):
        br.before_call()
