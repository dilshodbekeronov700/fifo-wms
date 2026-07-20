import axios from 'axios'

export const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  r => r,
  async err => {
    if (err.response?.status === 401) {
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          err.config.headers.Authorization = `Bearer ${data.access_token}`
          return api(err.config)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      } else {
        localStorage.clear()
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

// ── Auth ────────────────────────────────────────────────────────────────────
export const login = (email: string, password: string) =>
  api.post('/auth/login', { email, password }).then(r => r.data)
export const getMe = () => api.get('/auth/me').then(r => r.data)

// ── Tenants ─────────────────────────────────────────────────────────────────
export const getTenants = () => api.get('/tenants/').then(r => r.data)
export const createTenant = (d: any) => api.post('/tenants/', d).then(r => r.data)

// ── Warehouses ───────────────────────────────────────────────────────────────
export const getWarehouses = () => api.get('/warehouses/').then(r => r.data)
export const createWarehouse = (d: any) => api.post('/warehouses/', d).then(r => r.data)
export const updateWarehouse = (id: string, d: any) => api.patch(`/warehouses/${id}`, d).then(r => r.data)
export const deleteWarehouse = (id: string) => api.delete(`/warehouses/${id}`).then(r => r.data)
export const getWarehouseClimate = (id: string) => api.get(`/warehouses/${id}/climate`).then(r => r.data)

// ── Zones ────────────────────────────────────────────────────────────────────
export const getZones = (wid: string) => api.get(`/warehouses/${wid}/zones`).then(r => r.data)
export const createZone = (wid: string, d: any) => api.post(`/warehouses/${wid}/zones`, d).then(r => r.data)
export const updateZone = (wid: string, zid: string, d: any) => api.patch(`/warehouses/${wid}/zones/${zid}`, d).then(r => r.data)
export const deleteZone = (wid: string, zid: string) => api.delete(`/warehouses/${wid}/zones/${zid}`).then(r => r.data)

// ── Locations ────────────────────────────────────────────────────────────────
export const getLocations = (wid: string, zid: string) =>
  api.get(`/warehouses/${wid}/zones/${zid}/locations`).then(r => r.data)
export const createLocation = (wid: string, zid: string, d: any) =>
  api.post(`/warehouses/${wid}/zones/${zid}/locations`, d).then(r => r.data)
export const updateLocation = (wid: string, zid: string, lid: string, d: any) =>
  api.patch(`/warehouses/${wid}/zones/${zid}/locations/${lid}`, d).then(r => r.data)
export const deleteLocation = (wid: string, zid: string, lid: string) =>
  api.delete(`/warehouses/${wid}/zones/${zid}/locations/${lid}`).then(r => r.data)
export const getAllLocations = (wid: string) =>
  api.get(`/warehouses/${wid}/locations`).then(r => r.data)

// ── Map editor (Faza 1) ───────────────────────────────────────────────────────
export const updateLocationById = (wid: string, lid: string, d: any) =>
  api.patch(`/warehouses/${wid}/locations/${lid}`, d).then(r => r.data)
export const deleteLocationById = (wid: string, lid: string) =>
  api.delete(`/warehouses/${wid}/locations/${lid}`).then(r => r.data)
export const bulkCreateLocations = (wid: string, zone_id: string, locations: any[]) =>
  api.post(`/warehouses/${wid}/locations/bulk`, { zone_id, locations }).then(r => r.data)
export const generateRack = (wid: string, d: any) =>
  api.post(`/warehouses/${wid}/rack-generator`, d).then(r => r.data)
export const setRackCells = (wid: string, d: { zone_id: string; base_code: string; tiers: number; positions: number }) =>
  api.post(`/warehouses/${wid}/set-rack-cells`, d).then(r => r.data)
export const autoArrangeRacks = (wid: string, cols?: number) =>
  api.post(`/warehouses/${wid}/auto-arrange-racks`, {}, { params: cols ? { cols } : {} }).then(r => r.data)

// ── IoT sensorlar (Faza 3) ────────────────────────────────────────────────────
export const getSensors = (warehouse_id?: string) =>
  api.get('/sensors/', { params: warehouse_id ? { warehouse_id } : {} }).then(r => r.data)
export const createSensor = (d: any) => api.post('/sensors/', d).then(r => r.data)
export const updateSensor = (id: string, d: any) => api.patch(`/sensors/${id}`, d).then(r => r.data)
export const deleteSensor = (id: string) => api.delete(`/sensors/${id}`).then(r => r.data)
export const getSensorHistory = (id: string, hours = 24) =>
  api.get(`/sensors/${id}/history`, { params: { hours } }).then(r => r.data)

// ── Products ─────────────────────────────────────────────────────────────────
export const getProducts = () => api.get('/products/').then(r => r.data)
export const getAllProducts = (includeInactive = false) =>
  api.get('/products/', { params: { include_inactive: includeInactive } }).then(r => r.data)
export const createProduct = (d: any) => api.post('/products/', d).then(r => r.data)
export const updateProduct = (id: string, d: any) => api.patch(`/products/${id}`, d).then(r => r.data)
export const deleteProduct = (id: string) => api.delete(`/products/${id}`).then(r => r.data)
export const reconcileSmartup = () => api.post('/products/reconcile-smartup').then(r => r.data)

// ── Stock ────────────────────────────────────────────────────────────────────
export const getStock = (warehouse_id: string) =>
  api.get('/stock/', { params: { warehouse_id } }).then(r => r.data)

// ── Analytics ────────────────────────────────────────────────────────────────
export const getKpi = (warehouse_id: string, days = 30) =>
  api.get('/analytics/kpi', { params: { warehouse_id, days } }).then(r => r.data)
export const getHeatmap = (warehouse_id: string, days = 30) =>
  api.get('/analytics/heatmap', { params: { warehouse_id, days } }).then(r => r.data)
export const getAbcSuggestions = (warehouse_id: string) =>
  api.get('/analytics/abc-suggestions', { params: { warehouse_id } }).then(r => r.data)
export const getExpiryAlerts = (warehouse_id: string, warn_days = 30) =>
  api.get('/analytics/expiry-alerts', { params: { warehouse_id, warn_days } }).then(r => r.data)
export const getThroughput = (warehouse_id: string, days = 14) =>
  api.get('/analytics/throughput', { params: { warehouse_id, days } }).then(r => r.data)
export const getAnalyticsDashboard = (warehouse_id: string) =>
  api.get('/analytics/dashboard', { params: { warehouse_id } }).then(r => r.data)
export const getLocationHistory = (location_id: string, limit = 100) =>
  api.get('/analytics/location-history', { params: { location_id, limit } }).then(r => r.data)
export const getOccupancy = (warehouse_id: string) =>
  api.get('/analytics/occupancy', { params: { warehouse_id } }).then(r => r.data)
export const getReturnsAnalytics = (warehouse_id: string, days = 30) =>
  api.get('/analytics/returns', { params: { warehouse_id, days } }).then(r => r.data)
export const getZoneSummary = (warehouse_id: string, days = 30) =>
  api.get('/analytics/zone-summary', { params: { warehouse_id, days } }).then(r => r.data)

// ── Receipt ──────────────────────────────────────────────────────────────────
export const getProductionInputs = (warehouse_id: string) =>
  api.get('/receipt/production-inputs', { params: { warehouse_id } }).then(r => r.data)
export const getPurchases = (warehouse_id: string) =>
  api.get('/receipt/purchases', { params: { warehouse_id } }).then(r => r.data)
export const createReceipt = (d: any) => api.post('/receipt', d).then(r => r.data)
export const getReceipt = (id: string) => api.get(`/receipt/${id}`).then(r => r.data)
export const getDocuments = (warehouse_id: string, doc_type?: string) =>
  api.get('/documents/', { params: { warehouse_id, doc_type } }).then(r => r.data)

// ── Shipment ─────────────────────────────────────────────────────────────────
export const getShipmentOrders = (params: {
  warehouse_id: string
  statuses?: string[]
  all_statuses?: boolean
  begin_modified_on?: string
  end_modified_on?: string
}) => api.get('/shipment/orders', { params }).then(r => r.data)
export const shipmentScan = (d: { task_id: string; scanned_code: string; location_id?: string }) =>
  api.post('/shipment/scan', d).then(r => r.data)
export const createPickTask = (d: any) => api.post('/shipment/pick-task', d).then(r => r.data)
export const getPickTask = (id: string) => api.get(`/shipment/pick-task/${id}`).then(r => r.data)
export const confirmShipment = (doc_id: string) => api.post(`/shipment/confirm/${doc_id}`).then(r => r.data)

// ── Operations ───────────────────────────────────────────────────────────────
export const createMovement = (d: any) => api.post('/movement', d).then(r => r.data)
export const createInventoryCount = (d: any) => api.post('/inventory/count', d).then(r => r.data)
export const createWriteoff = (d: any) => api.post('/writeoff', d).then(r => r.data)
export const createReturn = (d: any) => api.post('/return', d).then(r => r.data)
export const getReconciliation = (warehouse_id: string) =>
  api.get('/reconciliation', { params: { warehouse_id } }).then(r => r.data)

// ── Export (authenticated blob download — bearer header is carried by `api`) ──
async function downloadCsv(path: string, params: Record<string, string>, filename: string) {
  const res = await api.get(path, { params, responseType: 'blob' })
  const url = URL.createObjectURL(res.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
export const exportStockCsv = (warehouseId: string, format: 'csv' = 'csv') =>
  downloadCsv('/export/stock', { warehouse_id: warehouseId, format }, `stock-${warehouseId}.${format}`)
export const exportReconciliationCsv = (warehouseId: string, format: 'csv' = 'csv') =>
  downloadCsv('/export/reconciliation', { warehouse_id: warehouseId, format }, `reconciliation-${warehouseId}.${format}`)

// Hisobot eksporti (Faza 4) — har biri csv/xlsx/pdf
export const exportReport = (
  kind: 'stock' | 'movement' | 'expiry' | 'temperature' | 'reconciliation',
  warehouseId: string, format: 'csv' | 'xlsx' | 'pdf', params: Record<string, any> = {},
) => downloadCsv(`/export/${kind}`, { warehouse_id: warehouseId, format, ...params }, `${kind}-${warehouseId}.${format}`)

// ── Admin (RBAC seeding) ─────────────────────────────────────────────────────
export const seedRbac = () => api.post('/admin/seed-rbac').then(r => r.data)

// ── Sign-up (self-registration → admin approval) ─────────────────────────────
export const signup = (d: { email: string; password: string; full_name: string; tenant_slug: string; phone?: string }) =>
  api.post('/auth/signup', d).then(r => r.data)

// ── User / role / permission administration + audit ──────────────────────────
export const getAdminUsers = (status = 'all') =>
  api.get('/admin/users', { params: { status } }).then(r => r.data)
export const approveUser = (id: string, role_ids: string[]) =>
  api.post(`/admin/users/${id}/approve`, { role_ids }).then(r => r.data)
export const rejectUser = (id: string) => api.post(`/admin/users/${id}/reject`).then(r => r.data)
export const updateAdminUser = (id: string, d: any) => api.patch(`/admin/users/${id}`, d).then(r => r.data)
export const getRoles = () => api.get('/admin/roles').then(r => r.data)
export const createRole = (name: string) => api.post('/admin/roles', { name }).then(r => r.data)
export const setRolePermissions = (id: string, permission_ids: string[]) =>
  api.put(`/admin/roles/${id}/permissions`, { permission_ids }).then(r => r.data)
export const getPermissions = () => api.get('/admin/permissions').then(r => r.data)
export const getAuditLog = (params?: { action?: string; resource?: string; limit?: number }) =>
  api.get('/admin/audit', { params }).then(r => r.data)

// ── Connectors ───────────────────────────────────────────────────────────────
export const getConnectorSpecs = () => api.get('/connectors/specs').then(r => r.data)
export const getConnectors = () => api.get('/connectors/').then(r => r.data)
export const upsertConnector = (d: any) => api.post('/connectors/', d).then(r => r.data)
export const testConnector = (t: string) => api.post(`/connectors/${t}/test`).then(r => r.data)
export const deleteConnector = (t: string) => api.delete(`/connectors/${t}`).then(r => r.data)
export const syncSmartupProducts = (full = false) =>
  api.post('/connectors/smartup/sync/products', null, { params: { full } }).then(r => r.data)
export const syncAslbelgisiProducts = () =>
  api.post('/connectors/aslbelgisi/sync/products').then(r => r.data)
export const seedOcardProducts = () =>
  api.post('/products/seed-ocard').then(r => r.data)
export const getIntegrationStatus = () => api.get('/connectors/status').then(r => r.data)
export const getSmartupReconciliation = (warehouse_id: string) =>
  api.get('/connectors/smartup/reconciliation', { params: { warehouse_id } }).then(r => r.data)
export const pullSmartup = (flows?: string[]) =>
  api.post('/connectors/smartup/pull', { flows: flows ?? null }).then(r => r.data)
// ERP-yozuv ruxsati (rol asosida) + buyurtma status push
export const getErpPolicy = () => api.get('/connectors/erp-policy').then(r => r.data)
export const setErpPolicy = (allowed_roles: string[]) =>
  api.put('/connectors/erp-policy', { allowed_roles }).then(r => r.data)
export const pushOrderStatus = (deal_id: string, status: string) =>
  api.post('/shipment/order-status', { deal_id, status }).then(r => r.data)
export const getSmartupMovements = (warehouse_id: string) =>
  api.get('/connectors/smartup/movements', { params: { warehouse_id } }).then(r => r.data)
export const getSmartupStocktakings = (warehouse_id: string) =>
  api.get('/connectors/smartup/stocktakings', { params: { warehouse_id } }).then(r => r.data)
export const getSmartupCurrentOrg = () =>
  api.get('/connectors/smartup/current-org').then(r => r.data)
export const getSmartupWriteoffs = (warehouse_id: string) =>
  api.get('/connectors/smartup/writeoffs', { params: { warehouse_id } }).then(r => r.data)
export const getSmartupReturns = (warehouse_id: string) =>
  api.get('/connectors/smartup/returns', { params: { warehouse_id } }).then(r => r.data)
export const approvePush = (id: string) =>
  api.post(`/connectors/smartup/push/${id}/approve`).then(r => r.data)
export const rejectPush = (id: string, reason = '') =>
  api.post(`/connectors/smartup/push/${id}/reject`, { reason }).then(r => r.data)

// ── Putaway (TSD pallet scan → optimal slot) ─────────────────────────────────
export const putawayScanSuggest = (d: { warehouse_id: string; code: string; top_n?: number }) =>
  api.post('/putaway/scan-suggest', d).then(r => r.data)
export const putawayReserve = (d: any) => api.post('/putaway/reserve', d).then(r => r.data)
export const putawayConfirm = (d: { reservation_id: string; location_barcode: string }) =>
  api.post('/putaway/confirm', d).then(r => r.data)
export const putawayCancel = (reservation_id: string) =>
  api.post('/putaway/cancel', { reservation_id }).then(r => r.data)
export const getReservations = (warehouse_id: string, status = 'pending') =>
  api.get('/putaway/reservations', { params: { warehouse_id, status } }).then(r => r.data)

// ── Cell contents (map cell-detail: stock + Asl Belgisi code tree + bron) ─────
export const getLocationContents = (locationId: string) =>
  api.get(`/stock/location/${locationId}/contents`).then(r => r.data)
export const fetchLocationCodeTree = (locationId: string) =>
  api.post(`/stock/location/${locationId}/fetch-code-tree`).then(r => r.data)

// ── Tasks ────────────────────────────────────────────────────────────────────
export const getTasks = (params?: { warehouse_id?: string; status?: string; task_type?: string }) =>
  api.get('/tasks/', { params }).then(r => r.data)
export const getTask = (id: string) => api.get(`/tasks/${id}`).then(r => r.data)
export const updateTask = (id: string, d: any) => api.patch(`/tasks/${id}`, d).then(r => r.data)

// ── Labels (ZPL) ─────────────────────────────────────────────────────────────
export const getLocationLabel = (locationId: string) =>
  api.get(`/labels/location/${locationId}`).then(r => r.data)
export const getPalletLabel = (markingCode: string) =>
  api.get(`/labels/pallet/${encodeURIComponent(markingCode)}`).then(r => r.data)

// ── Realtime (SSE) ────────────────────────────────────────────────────────────
// EventSource cannot set headers, so the access token is passed via ?token=.
export const subscribeRealtime = (): EventSource => {
  const token = localStorage.getItem('access_token') ?? ''
  return new EventSource(`/api/v1/realtime/stream?token=${encodeURIComponent(token)}`)
}

// ── Slotting config ───────────────────────────────────────────────────────────
export const updateZoneRules = (zoneId: string, d: { putaway_rules: Record<string, any> }) =>
  api.put(`/slotting/zones/${zoneId}/rules`, d).then(r => r.data)

export const getSlottingWeights = (warehouseId?: string) =>
  api
    .get('/slotting/weights', { params: warehouseId ? { warehouse_id: warehouseId } : undefined })
    .then(r => r.data?.weights ?? r.data)

export const updateSlottingWeights = (weights: Record<string, number>) =>
  api.put('/slotting/weights', { weights }).then(r => r.data?.weights ?? r.data)

// ── Stock views (detailed / summary) ─────────────────────────────────────────
export const getStockDetailed = (
  warehouseId: string,
  params?: Record<string, any>,
) =>
  api
    .get('/stock/detailed', { params: { warehouse_id: warehouseId, ...(params ?? {}) } })
    .then(r => r.data)

export const getStockSummary = (
  warehouseId: string,
  params?: Record<string, any>,
) =>
  api
    .get('/stock/summary', { params: { warehouse_id: warehouseId, ...(params ?? {}) } })
    .then(r => r.data)
