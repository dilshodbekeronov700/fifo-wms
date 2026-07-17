import uuid
from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str
    slug: str
    settings: dict = {}


class TenantOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class TenantSettings(BaseModel):
    # Tenant-level configuration (TZ §14). All optional; merged into settings JSON.
    locale: str | None = None                 # ru / uz / en
    uom: str | None = None                    # default unit of measure
    quarantine_on_receipt: bool | None = None
    workflows: dict | None = None             # feature toggles
    slotting_weights: dict | None = None
    extra: dict | None = None


class TenantProvision(BaseModel):
    """Super-admin: create a tenant + its first admin user (+ optional warehouse)."""
    name: str
    slug: str
    admin_email: str
    admin_password: str
    admin_full_name: str = "Administrator"
    warehouse_name: str | None = None
    locale: str = "ru"
