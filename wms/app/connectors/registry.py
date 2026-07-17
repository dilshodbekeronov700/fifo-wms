"""
Built-in connector registrations.

Importing this module populates the registry. New ERP/TMS connectors are added
here (or by any plugin that calls `base.register(...)`) without touching core
business logic.
"""
from __future__ import annotations

from typing import Any

from app.connectors.aslbelgisi import AslBelgisiClient
from app.connectors.base import (
    ConnectorKind,
    ConnectorSpec,
    CredentialField,
    register,
)
from app.connectors.smartup import SmartupClient


# ── Smartup (ERP) ────────────────────────────────────────────────────────────
def _build_smartup(creds: dict[str, Any], settings: dict[str, Any]) -> SmartupClient:
    return SmartupClient(
        base_url=creds["base_url"],
        login=creds["login"],
        password=creds["password"],
        project_code=creds.get("project_code", ""),
        filial_id=creds["filial_id"],
        filial_code=creds.get("filial_code", ""),
    )


async def _test_smartup(client: SmartupClient) -> None:
    # Lightweight authenticated call; raises on auth/connectivity failure.
    await client.get_product_references()


register(
    ConnectorSpec(
        type="smartup",
        kind=ConnectorKind.ERP,
        label="Smartup ERP",
        fields=[
            CredentialField("base_url", "Base URL", placeholder="https://smartup.online"),
            CredentialField("login", "Login"),
            CredentialField("password", "Parol", secret=True),
            CredentialField("project_code", "Project code (ixtiyoriy — bo'sh qoldiring)", placeholder="bo'sh", required=False),
            CredentialField("filial_id", "Filial ID", placeholder="1833"),
            CredentialField("filial_code", "Filial code (tashkilot kodi — balans uchun)",
                            placeholder="01-OCARD", required=False),
        ],
        builder=_build_smartup,
        test=_test_smartup,
    )
)


# ── Asl Belgisi (MARKING) ────────────────────────────────────────────────────
def _build_aslbelgisi(creds: dict[str, Any], settings: dict[str, Any]) -> AslBelgisiClient:
    return AslBelgisiClient(
        api_key=creds["api_key"],
        base_url=creds.get("base_url", ""),
        tin=creds.get("tin", ""),
        business_place_id=creds.get("business_place_id"),
    )


async def _test_aslbelgisi(client: AslBelgisiClient) -> None:
    # Verifies the apiKey belongs to the configured TIN.
    await client.check_api_key()


register(
    ConnectorSpec(
        type="aslbelgisi",
        kind=ConnectorKind.MARKING,
        label="Asl Belgisi (xtrace)",
        fields=[
            CredentialField("api_key", "API Key", secret=True),
            CredentialField("tin", "TIN / PINFL", placeholder="307797292"),
            CredentialField(
                "base_url", "Base URL", required=False,
                placeholder="https://xtrace.aslbelgisi.uz",
            ),
            CredentialField(
                "business_place_id", "Business Place ID", required=False,
                help="Agregatsiya/dezagregatsiya hisobotlari uchun (MOD identifikatori)",
            ),
        ],
        builder=_build_aslbelgisi,
        test=_test_aslbelgisi,
    )
)


# ── Pluggable ERP/TMS connectors (1C, SAP, TMS) ──────────────────────────────
from app.connectors.plugins import register_plugin_connectors  # noqa: E402

register_plugin_connectors()
