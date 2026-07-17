"""
Application-level secret encryption for connector credentials.

Credentials (Smartup login/password, Asl Belgisi apiKey, etc.) are entered via
the UI and stored encrypted at rest with Fernet (AES-128-CBC + HMAC).

The Fernet key is derived from `settings.ENCRYPTION_KEY` (preferred) or, as a
dev fallback, from `settings.JWT_SECRET_KEY`. Deriving via SHA-256 lets the
operator supply any passphrase instead of a strict 32-byte urlsafe-base64 key.

Storage format: the whole credentials dict is JSON-serialised, encrypted, and
stored as `{"_enc": "<fernet-token>"}`. `is_credentials_encrypted` detects this
shape so we can transparently migrate any legacy plaintext rows.
"""
from __future__ import annotations

import base64
import hashlib
import json
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet

from app.core.config import settings

_ENC_KEY = "_enc"


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    raw = ""
    if settings.ENCRYPTION_KEY is not None:
        raw = settings.ENCRYPTION_KEY.get_secret_value()
    if not raw:
        # Dev fallback — never rely on this in production.
        raw = settings.JWT_SECRET_KEY.get_secret_value()
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def is_credentials_encrypted(credentials: dict[str, Any]) -> bool:
    return isinstance(credentials, dict) and set(credentials.keys()) == {_ENC_KEY}


def encrypt_credentials(credentials: dict[str, Any]) -> dict[str, str]:
    """Serialise + encrypt a credentials dict into `{"_enc": token}`."""
    payload = json.dumps(credentials, separators=(",", ":")).encode("utf-8")
    token = _fernet().encrypt(payload).decode("ascii")
    return {_ENC_KEY: token}


def decrypt_credentials(credentials: dict[str, Any]) -> dict[str, Any]:
    """Reverse of `encrypt_credentials`. Plaintext (legacy) rows pass through."""
    if not is_credentials_encrypted(credentials):
        return dict(credentials)  # legacy plaintext — return as-is
    raw = _fernet().decrypt(credentials[_ENC_KEY].encode("ascii"))
    return json.loads(raw)
