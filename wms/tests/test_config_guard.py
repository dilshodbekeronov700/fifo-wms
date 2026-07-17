"""Production sir-guard testlari (config.model_validator)."""
import pytest
from pydantic import ValidationError

from app.core.config import Settings

_STRONG = "x" * 48  # 32+ belgi, andoza emas


def test_weak_jwt_rejected_in_production():
    with pytest.raises(ValidationError):
        Settings(DEBUG=False, JWT_SECRET_KEY="change-me-to-a-long-random-secret",
                 CORS_ORIGINS="https://app.example.com", _env_file=None)


def test_short_jwt_rejected_in_production():
    with pytest.raises(ValidationError):
        Settings(DEBUG=False, JWT_SECRET_KEY="short", CORS_ORIGINS="https://a.com",
                 _env_file=None)


def test_wildcard_cors_rejected_in_production():
    with pytest.raises(ValidationError):
        Settings(DEBUG=False, JWT_SECRET_KEY=_STRONG, CORS_ORIGINS="*", _env_file=None)


def test_strong_secrets_accepted_in_production():
    s = Settings(DEBUG=False, JWT_SECRET_KEY=_STRONG,
                 CORS_ORIGINS="https://app.example.com", _env_file=None)
    assert s.cors_origins_list == ["https://app.example.com"]


def test_debug_mode_allows_defaults():
    # DEBUG=true (dev) — andoza qiymatlar qabul qilinadi.
    s = Settings(DEBUG=True, JWT_SECRET_KEY="change-me-to-a-long-random-secret",
                 CORS_ORIGINS="*", _env_file=None)
    assert s.DEBUG is True
