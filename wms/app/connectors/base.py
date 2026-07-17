"""
Connector registry — the extensibility seam of the platform.

Every external system (ERP, marking system, TMS, …) is described by a
`ConnectorSpec`. The core never hard-codes "smartup" or "aslbelgisi"; it works
against this registry. Adding a new ERP/TMS = register a spec, no core changes.

A spec declares:
  - kind:           ERP / MARKING / TMS / OTHER (drives where it plugs in)
  - required_fields / secret_fields: for UI form generation + masking
  - builder:        (credentials, settings) -> client instance
  - test:           optional async connectivity probe (client) -> None/raises
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable


class ConnectorKind(str, Enum):
    ERP = "erp"            # orders, balances, master data, postings (Smartup, 1C, SAP…)
    MARKING = "marking"    # national track & trace (Asl Belgisi, CRPT…)
    TMS = "tms"            # transport / logistics
    OTHER = "other"


@dataclass(frozen=True)
class CredentialField:
    name: str
    label: str
    secret: bool = False
    required: bool = True
    placeholder: str = ""
    help: str = ""


@dataclass(frozen=True)
class ConnectorSpec:
    type: str
    kind: ConnectorKind
    label: str
    fields: list[CredentialField]
    builder: Callable[[dict[str, Any], dict[str, Any]], Any]
    test: Callable[[Any], Awaitable[None]] | None = None
    settings_fields: list[CredentialField] = field(default_factory=list)

    @property
    def required_fields(self) -> list[str]:
        return [f.name for f in self.fields if f.required]

    @property
    def secret_fields(self) -> list[str]:
        return [f.name for f in self.fields if f.secret]


_REGISTRY: dict[str, ConnectorSpec] = {}


def register(spec: ConnectorSpec) -> None:
    _REGISTRY[spec.type] = spec


def get_spec(connector_type: str) -> ConnectorSpec:
    try:
        return _REGISTRY[connector_type]
    except KeyError:
        raise KeyError(f"Unknown connector type: {connector_type}")


def all_specs() -> list[ConnectorSpec]:
    return list(_REGISTRY.values())


def validate_credentials(connector_type: str, credentials: dict[str, Any]) -> list[str]:
    """Return the list of missing required fields (empty = valid)."""
    spec = get_spec(connector_type)
    return [f for f in spec.required_fields if not credentials.get(f)]


def describe(spec: ConnectorSpec) -> dict[str, Any]:
    """JSON-serialisable description for the UI (no secret values)."""
    return {
        "type": spec.type,
        "kind": spec.kind.value,
        "label": spec.label,
        "fields": [
            {
                "name": f.name, "label": f.label, "secret": f.secret,
                "required": f.required, "placeholder": f.placeholder, "help": f.help,
            }
            for f in spec.fields
        ],
        "settings_fields": [
            {
                "name": f.name, "label": f.label, "secret": f.secret,
                "required": f.required, "placeholder": f.placeholder, "help": f.help,
            }
            for f in spec.settings_fields
        ],
    }
