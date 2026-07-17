from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, tenants, warehouses, products,
    receipt, putaway, stock, shipment, operations,
    analytics, connectors, exceptions, quarantine,
    labels, realtime, slotting_config, admin, admin_users, export, billing, sensors,
    replenishment, cycle_count, wave, rma,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(warehouses.router)
api_router.include_router(products.router)
api_router.include_router(receipt.router)
api_router.include_router(putaway.router)
api_router.include_router(stock.router)
api_router.include_router(shipment.router)
api_router.include_router(operations.router)
api_router.include_router(analytics.router)
api_router.include_router(connectors.router)
api_router.include_router(exceptions.router)
api_router.include_router(quarantine.router)
api_router.include_router(labels.router)
api_router.include_router(realtime.router)
api_router.include_router(slotting_config.router)
api_router.include_router(admin.router)
api_router.include_router(admin_users.router)
api_router.include_router(export.router)
api_router.include_router(billing.router)
api_router.include_router(sensors.router)
api_router.include_router(replenishment.router)
api_router.include_router(cycle_count.router)
api_router.include_router(wave.router)
api_router.include_router(rma.router)
