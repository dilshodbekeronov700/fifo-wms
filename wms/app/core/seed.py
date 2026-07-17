"""RBAC permission catalog + idempotent seeding.

Defines every (resource, action) capability used across the API and the
built-in system roles. ``seed_rbac`` upserts Permission rows and (re)attaches
the canonical permission sets to the system roles. Safe to run repeatedly.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import Permission, Role

# --------------------------------------------------------------------------- #
# Permission catalog
# --------------------------------------------------------------------------- #
# Every resource that appears across the app, each with a sensible action set.
# Actions: view / create / update / delete / approve.
PERMISSIONS: list[tuple[str, str]] = [
    # Platform / tenant administration
    ("tenant", "view"),
    ("tenant", "create"),
    ("tenant", "update"),
    ("tenant", "delete"),
    # Warehouse topology
    ("warehouse", "view"),
    ("warehouse", "create"),
    ("warehouse", "update"),
    ("warehouse", "delete"),
    ("zone", "view"),
    ("zone", "create"),
    ("zone", "update"),
    ("zone", "delete"),
    ("location", "view"),
    ("location", "create"),
    ("location", "update"),
    ("location", "delete"),
    # Catalog
    ("product", "view"),
    ("product", "create"),
    ("product", "update"),
    ("product", "delete"),
    # Inbound operations
    ("receipt", "view"),
    ("receipt", "create"),
    ("receipt", "update"),
    ("receipt", "approve"),
    ("putaway", "view"),
    ("putaway", "create"),
    ("putaway", "update"),
    ("putaway", "approve"),
    # Stock / inventory
    ("stock", "view"),
    ("stock", "update"),
    ("inventory", "view"),
    ("inventory", "create"),
    ("inventory", "update"),
    ("inventory", "approve"),
    # Outbound operations
    ("shipment", "view"),
    ("shipment", "create"),
    ("shipment", "update"),
    ("shipment", "approve"),
    # Internal moves
    ("movement", "view"),
    ("movement", "create"),
    ("movement", "update"),
    ("movement", "approve"),
    # Adjustments
    ("writeoff", "view"),
    ("writeoff", "create"),
    ("writeoff", "approve"),
    ("return", "view"),
    ("return", "create"),
    ("return", "update"),
    ("return", "approve"),
    ("reconciliation", "view"),
    ("reconciliation", "create"),
    ("reconciliation", "approve"),
    # Integrations
    ("connector", "view"),
    ("connector", "create"),
    ("connector", "update"),
    ("connector", "delete"),
    # Labels / printing
    ("label", "view"),
    ("label", "create"),
    # Slotting configuration
    ("slotting", "view"),
    ("slotting", "create"),
    ("slotting", "update"),
    # Exception handling
    ("exception", "view"),
    ("exception", "create"),
    ("exception", "update"),
    ("exception", "approve"),
    # Quarantine
    ("quarantine", "view"),
    ("quarantine", "update"),
    ("quarantine", "approve"),
    # Tasks
    ("task", "view"),
    ("task", "create"),
    ("task", "update"),
    # Data export
    ("export", "view"),
    ("export", "create"),
    # Billing / tariff
    ("billing", "view"),
    ("billing", "update"),
    # User / role administration (sign-up approval, role assignment)
    ("user", "view"),
    ("user", "create"),
    ("user", "update"),
    ("user", "approve"),
    ("role", "view"),
    ("role", "update"),
    ("audit", "view"),
]

# All resources, for "view-only across resources" / "all tenant-level" sets.
_ALL_RESOURCES: list[str] = []
for _res, _act in PERMISSIONS:
    if _res not in _ALL_RESOURCES:
        _ALL_RESOURCES.append(_res)

# Operational resources an operator/manager actually drives day to day.
_OPS_RESOURCES = [
    "receipt", "putaway", "stock", "inventory",
    "shipment", "movement", "writeoff", "return",
    "reconciliation", "label", "exception", "quarantine", "task", "export",
]


def _perms_for_resources(resources: list[str], actions: set[str]) -> set[tuple[str, str]]:
    """Filter the catalog to (resource, action) pairs that exist and match."""
    wanted = set(resources)
    return {
        (r, a) for (r, a) in PERMISSIONS
        if r in wanted and a in actions
    }


# --------------------------------------------------------------------------- #
# System role definitions -> set of (resource, action)
# --------------------------------------------------------------------------- #
def _tenant_admin_perms() -> set[tuple[str, str]]:
    # Every permission in the catalog (full tenant-level control).
    return set(PERMISSIONS)


def _warehouse_manager_perms() -> set[tuple[str, str]]:
    # Ops (create/update/delete) + view everywhere + approve everywhere.
    perms = _perms_for_resources(_OPS_RESOURCES, {"create", "update", "delete"})
    perms |= _perms_for_resources(_ALL_RESOURCES, {"view"})
    perms |= _perms_for_resources(_ALL_RESOURCES, {"approve"})
    # Managers also manage topology & catalog within their warehouses.
    perms |= _perms_for_resources(
        ["warehouse", "zone", "location", "product", "slotting", "connector"],
        {"create", "update"},
    )
    return perms


def _operator_perms() -> set[tuple[str, str]]:
    # Floor operator: execute core flows + read.
    perms = _perms_for_resources(
        ["receipt", "putaway", "shipment", "movement", "inventory"],
        {"create", "view"},
    )
    perms |= _perms_for_resources(["task"], {"view", "update"})
    # Needs to see stock/products/locations to do the work.
    perms |= _perms_for_resources(
        ["stock", "product", "location", "zone", "warehouse", "label"],
        {"view"},
    )
    perms |= _perms_for_resources(["label"], {"create"})
    return perms


def _office_perms() -> set[tuple[str, str]]:
    # Read-only across every resource.
    return _perms_for_resources(_ALL_RESOURCES, {"view"})


SYSTEM_ROLES: dict[str, "callable"] = {
    "tenant_admin": _tenant_admin_perms,
    "warehouse_manager": _warehouse_manager_perms,
    "operator": _operator_perms,
    "office": _office_perms,
}


# --------------------------------------------------------------------------- #
# Seeder
# --------------------------------------------------------------------------- #
async def seed_rbac(db: AsyncSession) -> dict:
    """Upsert all permissions and (re)attach them to system roles.

    Idempotent: existing permissions are reused (unique resource+action),
    existing system roles are reused, and their permission sets are
    reconciled to the canonical definition above.

    Returns counts of what exists / was created.
    """
    # --- 1. Upsert permissions -------------------------------------------- #
    existing_res = await db.execute(select(Permission))
    by_key: dict[tuple[str, str], Permission] = {
        (p.resource, p.action): p for p in existing_res.scalars().all()
    }

    perms_created = 0
    for resource, action in PERMISSIONS:
        key = (resource, action)
        if key not in by_key:
            perm = Permission(resource=resource, action=action)
            db.add(perm)
            by_key[key] = perm
            perms_created += 1

    # Flush so newly-added permissions get IDs before role attachment.
    await db.flush()

    # --- 2. Upsert system roles + reconcile permissions ------------------- #
    roles_created = 0
    roles_updated = 0

    for role_name, perm_fn in SYSTEM_ROLES.items():
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.name == role_name, Role.tenant_id.is_(None))
        )
        role = result.scalar_one_or_none()

        target_keys = perm_fn()
        target_perms = [by_key[k] for k in target_keys if k in by_key]

        if role is None:
            # Set permissions at construction (transient object → no lazy load).
            role = Role(name=role_name, tenant_id=None, is_system=True, permissions=target_perms)
            db.add(role)
            roles_created += 1
        else:
            if not role.is_system:
                role.is_system = True
            # `permissions` is eager-loaded via selectinload above (async-safe).
            current_keys = {(p.resource, p.action) for p in role.permissions}
            if current_keys != target_keys:
                role.permissions = target_perms
                roles_updated += 1

    await db.flush()

    return {
        "permissions_total": len(PERMISSIONS),
        "permissions_created": perms_created,
        "roles_total": len(SYSTEM_ROLES),
        "roles_created": roles_created,
        "roles_updated": roles_updated,
    }
