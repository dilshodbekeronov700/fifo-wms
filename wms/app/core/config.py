import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, model_validator

logger = logging.getLogger(__name__)

# Ishlab chiqarishda (DEBUG=false) qabul qilinmaydigan andoza/zaif sirlar.
_WEAK_JWT_SECRETS = {"change-me-to-a-long-random-secret", "change-me", "secret", ""}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "WMS"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://wms:wms@localhost:5432/wms"
    # Connection pool (asyncpg) — production'da concurrency uchun sozlanadi.
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # Observability
    LOG_JSON: bool = False          # production'da true — strukturali (JSON) log
    SENTRY_DSN: str = ""            # bo'sh bo'lsa Sentry o'chiq
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0
    # /health/ready worker heartbeat "yangi" deb sanaladigan maksimal yosh (soniya)
    WORKER_HEARTBEAT_MAX_AGE: int = 300

    # Connector resilience (circuit breaker)
    CIRCUIT_FAIL_THRESHOLD: int = 5     # ketma-ket shuncha xatodan keyin ochiladi
    CIRCUIT_RESET_SECONDS: int = 60     # shuncha vaqt fail-fast, keyin yarim-ochiq

    # JWT
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Secret encryption (connector credentials at rest).
    # Any passphrase; a Fernet key is derived from it (SHA-256). Falls back to
    # JWT_SECRET_KEY in dev if unset — set a dedicated value in production.
    ENCRYPTION_KEY: SecretStr | None = None

    # Argon2 / passlib handles hashing — no extra config needed here

    # Login brute-force protection
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # CORS — comma-separated origins (e.g. "https://app.example.com,https://x.com")
    CORS_ORIGINS: str = "*"

    # External connectors (per-tenant, stored encrypted in DB; these are defaults for dev)
    SMARTUP_BASE_URL: str = ""
    ASLBELGISI_BASE_URL: str = "https://xtrace.aslbelgisi.uz"

    def _split_db_url(self) -> tuple[str, bool]:
        """asyncpg tushunmaydigan query paramlarni (sslmode, channel_binding)
        ajratadi. Neon/Supabase URL'ini o'zgartirmasdan paste qilса ishlaydi:
        toza URL + SSL kerak-kermasligini qaytaradi."""
        raw = self.DATABASE_URL
        if raw.startswith("sqlite"):
            return raw, False
        parts = urlsplit(raw)
        q = dict(parse_qsl(parts.query))
        sslmode = q.pop("sslmode", None)
        q.pop("channel_binding", None)   # Neon qo'shadi; asyncpg rad etadi
        need_ssl = sslmode not in (None, "disable")
        clean = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))
        return clean, need_ssl

    @property
    def db_url_clean(self) -> str:
        return self._split_db_url()[0]

    @property
    def db_connect_args(self) -> dict:
        return {"ssl": True} if self._split_db_url()[1] else {}

    @property
    def cors_origins_list(self) -> list[str]:
        raw = (self.CORS_ORIGINS or "").strip()
        if raw in ("", "*"):
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """DEBUG=false (production) bo'lganda xavfli standart qiymatlarni bloklaydi.

        Andoza JWT siri yoki ochiq CORS bilan ishlab chiqarishga chiqish — jiddiy
        xavf. Bu tekshiruv ilova ishga tushishidayoq (fail-fast) buni to'xtatadi.
        """
        if self.DEBUG:
            return self
        jwt = self.JWT_SECRET_KEY.get_secret_value()
        if jwt in _WEAK_JWT_SECRETS or len(jwt) < 32:
            raise ValueError(
                "JWT_SECRET_KEY production'da kamida 32 belgi va andoza bo'lmasligi kerak. "
                "Yangi sir: `python -c \"import secrets; print(secrets.token_urlsafe(48))\"`"
            )
        if self.cors_origins_list == ["*"]:
            raise ValueError(
                "CORS_ORIGINS production'da '*' bo'lishi mumkin emas — aniq domen(lar)ni ko'rsating."
            )
        if self.ENCRYPTION_KEY is None:
            logger.warning(
                "ENCRYPTION_KEY o'rnatilmagan — connector sirlari JWT_SECRET_KEY'dan "
                "hosil qilingan kalit bilan shifrlanadi. Production'da alohida kalit qo'ying."
            )
        return self


settings = Settings()  # type: ignore[call-arg]
