"""
Pluggable ERP/TMS connectors (TZ §14 — productisation).

Demonstrates the extensibility seam: new external systems are added here as
ConnectorSpec registrations WITHOUT touching core business logic. These ship as
stubs (config + connectivity ping); concrete API mappings are implemented per
deployment. They appear in the UI automatically via /connectors/specs.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.connectors.base import (
    ConnectorKind,
    ConnectorSpec,
    CredentialField,
    register,
)


class GenericRestClient:
    """Minimal REST stub: holds creds + a connectivity probe. Concrete request
    mappings are added when the integration is implemented for a customer."""

    def __init__(self, kind: str, base_url: str, token: str = "", extra: dict[str, Any] | None = None):
        self.kind = kind
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.extra = extra or {}

    async def ping(self) -> None:
        if not self.base_url:
            raise ValueError("base_url is required")
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.get(self.base_url, headers=headers)
            # Any HTTP response means the host is reachable; 4xx is fine for a probe.
            if resp.status_code >= 500:
                raise RuntimeError(f"{self.kind} host error {resp.status_code}")


def _builder(kind: str):
    def build(creds: dict[str, Any], settings: dict[str, Any]) -> GenericRestClient:
        return GenericRestClient(
            kind=kind,
            base_url=creds.get("base_url", ""),
            token=creds.get("token", "") or creds.get("api_key", ""),
            extra={k: v for k, v in creds.items() if k not in ("base_url", "token", "api_key")},
        )
    return build


async def _test(client: GenericRestClient) -> None:
    await client.ping()


def register_plugin_connectors() -> None:
    # 1C (ERP)
    register(ConnectorSpec(
        type="1c", kind=ConnectorKind.ERP, label="1C (ERP)",
        fields=[
            CredentialField("base_url", "Base URL", placeholder="https://1c.example.uz"),
            CredentialField("token", "Token / API key", secret=True, required=False),
            CredentialField("database", "Baza nomi", required=False),
        ],
        builder=_builder("1c"), test=_test,
    ))
    # SAP (ERP)
    register(ConnectorSpec(
        type="sap", kind=ConnectorKind.ERP, label="SAP (ERP)",
        fields=[
            CredentialField("base_url", "Base URL", placeholder="https://sap.example.com"),
            CredentialField("token", "OAuth token", secret=True, required=False),
            CredentialField("company_code", "Company code", required=False),
        ],
        builder=_builder("sap"), test=_test,
    ))
    # Generic TMS (transport)
    register(ConnectorSpec(
        type="tms", kind=ConnectorKind.TMS, label="TMS (transport)",
        fields=[
            CredentialField("base_url", "Base URL", placeholder="https://tms.example.com"),
            CredentialField("api_key", "API key", secret=True, required=False),
        ],
        builder=_builder("tms"), test=_test,
    ))
