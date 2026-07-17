# Import all models so Alembic autogenerate discovers them
from app.models.tenant import Tenant  # noqa: F401
from app.models.auth import User, Role, Permission, RefreshToken  # noqa: F401
from app.models.warehouse import Warehouse, Zone, Location  # noqa: F401
from app.models.inventory import (  # noqa: F401
    Product, Batch, MarkingCode, StockItem, Document, OutboxMessage
)
from app.models.ledger import LedgerEntry  # noqa: F401
from app.models.reservation import PutawayReservation  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.connector import ConnectorConfig  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.exception import ExceptionEvent  # noqa: F401
from app.models.sensor import Sensor, SensorReading  # noqa: F401
