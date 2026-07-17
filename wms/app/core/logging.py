"""Strukturali (JSON) logging + so'rov correlation-id + ixtiyoriy Sentry.

- `request_id_ctx`: har bir HTTP so'rov uchun contextvar; middleware o'rnatadi.
  Log yozuvlariga avtomatik qo'shiladi — bir so'rovning barcha loglarini ulash uchun.
- `configure_logging()`: LOG_JSON=true bo'lsa JSON formatter, aks holda matn.
- Sentry: SENTRY_DSN o'rnatilgan va `sentry_sdk` o'rnatilgan bo'lsa yoqiladi
  (ixtiyoriy bog'liqlik — o'rnatilmagan bo'lsa jimgina o'tkazib yuboriladi).
"""
from __future__ import annotations

import json
import logging
from contextvars import ContextVar

from app.core.config import settings

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

# JSON'ga qo'shmaslik kerak bo'lgan standart LogRecord maydonlari.
_STD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName",
}


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # `logger.info("...", extra={...})` orqali kelgan qo'shimcha maydonlar.
        for k, v in record.__dict__.items():
            if k not in _STD_ATTRS and k not in payload and not k.startswith("_"):
                payload[k] = v
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())
    if settings.LOG_JSON:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s [req=%(request_id)s] %(message)s"
        ))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)


def init_sentry() -> bool:
    """Sentry'ni yoqadi (DSN + kutubxona bo'lsa). Yoqilgan bo'lsa True."""
    if not settings.SENTRY_DSN:
        return False
    try:
        import sentry_sdk
    except ImportError:
        logging.getLogger(__name__).warning(
            "SENTRY_DSN o'rnatilgan, lekin sentry_sdk o'rnatilmagan — Sentry o'chiq."
        )
        return False
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        environment="debug" if settings.DEBUG else "production",
    )
    return True
