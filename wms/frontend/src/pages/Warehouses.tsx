import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getWarehouses, createWarehouse, updateWarehouse, deleteWarehouse,
  getZones, createZone, updateZone, deleteZone,
  getLocations, createLocation, deleteLocation,
} from '../lib/api'
import { Stage, Layer, Rect, Text, Group } from 'react-konva'
import { Plus, ChevronRight, MapPin, Layers, Map, List, Pencil, Trash2, X, Warehouse } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  PageHeader, Card, CardHeader, Button, Input, Select, Badge, Tabs, type Tone,
} from '../components/ui'

const ZONE_TYPES = ['reserve', 'pick', 'open_pallet', 'staging', 'dock', 'quarantine', 'return']
const LOC_TYPES = ['pallet', 'shelf', 'floor']

const ZONE_COLORS: Record<string, string> = {
  reserve: '#3b82f6',
  pick: '#10b981',
  open_pallet: '#f59e0b',
  staging: '#8b5cf6',
  dock: '#6b7280',
  quarantine: '#ef4444',
  return: '#f97316',
}
const LOC_STATUS_COLORS: Record<string, string> = {
  empty: '#d1fae5',
  occupied: '#bfdbfe',
  partial: '#fef3c7',
  blocked: '#fee2e2',
}

// ── Shared QuickForm ─────────────────────────────────────────────────────────
function QuickForm({ title, fields, onSubmit, onCancel, submitLabel = 'Saqlash' }: any) {
  const [vals, setVals] = useState<Record<string, any>>({})
  return (
    <div className="border border-blue-500/40 bg-blue-500/10 rounded-xl p-3 space-y-2 mb-2">
      <p className="text-xs font-semibold text-blue-600">{title}</p>
      {fields.map((f: any) => (
        <div key={f.name} className="space-y-1">
          <label className="text-xs text-slate-500">{f.label}{f.required && ' *'}</label>
          {f.type === 'select' ? (
            <Select
              className="h-8 text-xs"
              value={vals[f.name] ?? ''}
              onChange={e => setVals(v => ({ ...v, [f.name]: e.target.value }))}
            >
              <option value="">Tanlang</option>
              {f.options.map((o: string) => <option key={o} value={o}>{o}</option>)}
            </Select>
          ) : (
            <Input
              type={f.type ?? 'text'}
              className="h-8 text-xs"
              value={vals[f.name] ?? ''}
              onChange={e => setVals(v => ({
                ...v,
                [f.name]: f.type === 'number' ? (e.target.value ? Number(e.target.value) : '') : e.target.value,
              }))}
            />
          )}
        </div>
      ))}
      <div className="flex gap-2 pt-1">
        <Button size="sm" onClick={() => onSubmit(vals)}>{submitLabel}</Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>Bekor</Button>
      </div>
    </div>
  )
}

const STATUS_TONE: Record<string, Tone> = {
  empty: 'green', occupied: 'blue', partial: 'amber', blocked: 'red',
}
function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONE[status] ?? 'slate'}>{status}</Badge>
}

// ── 2D Map (drag & drop) ─────────────────────────────────────────────────────
const CANVAS_W = 780
const CANVAS_H = 480
const ZONE_DEFAULT_W = 160
const ZONE_DEFAULT_H = 110
const COLS = 4

function defaultPos(index: number) {
  const col = index % COLS
  const row = Math.floor(index / COLS)
  return { x: 16 + col * (ZONE_DEFAULT_W + 12), y: 16 + row * (ZONE_DEFAULT_H + 12) }
}

function WarehouseMap({
  zones,
  locations,
  onZoneMoved,
}: {
  zones: any[]
  locations: any[]
  warehouseId: string
  onZoneMoved: (zoneId: string, x: number, y: number) => void
}) {
  const [hovered, setHovered] = useState<string | null>(null)
  const [dragging, setDragging] = useState<string | null>(null)

  const locsByZone: Record<string, any[]> = {}
  for (const loc of locations) {
    if (!locsByZone[loc.zone_id]) locsByZone[loc.zone_id] = []
    locsByZone[loc.zone_id].push(loc)
  }

  if (zones.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-400 bg-slate-50 rounded-xl border-2 border-dashed border-slate-200">
        <Map size={28} className="mb-2 opacity-40" />
        <p className="text-sm">Avval zona qo'shing — u yerda drag qiling</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-50">
      <div className="px-3 py-2 border-b border-slate-200 bg-white flex items-center gap-2 text-xs text-slate-400">
        <span>☝️ Zonalarni xohlagancha sudrab qo'ying — o'rni avtomatik saqlanadi</span>
      </div>
      <Stage width={CANVAS_W} height={CANVAS_H}>
        <Layer>
          {/* Grid dots background */}
          {Array.from({ length: Math.floor(CANVAS_H / 20) }).map((_, ri) =>
            Array.from({ length: Math.floor(CANVAS_W / 20) }).map((_, ci) => (
              <Rect
                key={`dot-${ri}-${ci}`}
                x={ci * 20 + 9}
                y={ri * 20 + 9}
                width={2}
                height={2}
                fill="#cbd5e1"
                cornerRadius={1}
              />
            ))
          )}

          {zones.map((zone, idx) => {
            const def = defaultPos(idx)
            const x = zone.x ?? def.x
            const y = zone.y ?? def.y
            const w = zone.width ?? ZONE_DEFAULT_W
            const h = zone.height ?? ZONE_DEFAULT_H
            const color = ZONE_COLORS[zone.zone_type] ?? '#94a3b8'
            const zoneLocs = locsByZone[zone.id] ?? []
            const isDragging = dragging === zone.id

            const cellSize = 14
            const padding = 6
            const cols = Math.max(1, Math.floor((w - padding * 2) / (cellSize + 3)))

            return (
              <Group
                key={zone.id}
                x={x}
                y={y}
                draggable
                opacity={isDragging ? 0.7 : 1}
                onDragStart={() => setDragging(zone.id)}
                onDragEnd={e => {
                  setDragging(null)
                  const newX = Math.round(e.target.x())
                  const newY = Math.round(e.target.y())
                  onZoneMoved(zone.id, newX, newY)
                }}
              >
                {/* Zone body */}
                <Rect
                  width={w}
                  height={h}
                  fill={color + '18'}
                  stroke={isDragging ? color : color + 'aa'}
                  strokeWidth={isDragging ? 2.5 : 1.5}
                  cornerRadius={6}
                  shadowColor={isDragging ? color : 'transparent'}
                  shadowBlur={isDragging ? 12 : 0}
                  shadowOpacity={0.4}
                />
                {/* Zone label */}
                <Text
                  x={padding}
                  y={5}
                  text={zone.name}
                  fontSize={11}
                  fill={color}
                  fontStyle="bold"
                  width={w - padding * 2}
                  ellipsis
                />
                <Text
                  x={padding}
                  y={18}
                  text={zone.zone_type}
                  fontSize={9}
                  fill={color + '99'}
                  width={w - padding * 2}
                />
                {/* Location cells */}
                {zoneLocs.slice(0, cols * Math.floor((h - 32) / (cellSize + 3))).map((loc, i) => {
                  const col = i % cols
                  const row = Math.floor(i / cols)
                  const lx = padding + col * (cellSize + 3)
                  const ly = 30 + row * (cellSize + 3)
                  const fillColor = LOC_STATUS_COLORS[loc.status] ?? '#f1f5f9'
                  return (
                    <Rect
                      key={loc.id}
                      x={lx}
                      y={ly}
                      width={cellSize}
                      height={cellSize}
                      fill={hovered === loc.id ? '#fbbf24' : fillColor}
                      stroke="#e2e8f0"
                      strokeWidth={0.5}
                      cornerRadius={2}
                      onMouseEnter={() => setHovered(loc.id)}
                      onMouseLeave={() => setHovered(null)}
                    />
                  )
                })}
                {zoneLocs.length > 0 && (
                  <Text
                    x={padding}
                    y={h - 14}
                    text={`${zoneLocs.length} yacheyka`}
                    fontSize={9}
                    fill={color + '88'}
                  />
                )}
              </Group>
            )
          })}
        </Layer>
      </Stage>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 px-3 py-2 border-t border-slate-200 bg-white">
        {Object.entries(LOC_STATUS_COLORS).map(([status, color]) => (
          <div key={status} className="flex items-center gap-1.5 text-xs text-slate-500">
            <div className="w-3 h-3 rounded-sm border border-slate-200" style={{ background: color }} />
            {status}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main component ───────────────────────────────────────────────────────────
export default function Warehouses() {
  const qc = useQueryClient()
  const [selectedWh, setSelectedWh] = useState<any>(null)
  const [selectedZone, setSelectedZone] = useState<any>(null)
  const [viewMode, setViewMode] = useState<'list' | 'map'>('map')

  const [showWhForm, setShowWhForm] = useState(false)
  const [editWh, setEditWh] = useState<any>(null)
  const [showZoneForm, setShowZoneForm] = useState(false)
  const [editZone, setEditZone] = useState<any>(null)
  const [showLocForm, setShowLocForm] = useState(false)

  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const { data: zones = [] } = useQuery({
    queryKey: ['zones', selectedWh?.id],
    queryFn: () => getZones(selectedWh.id),
    enabled: !!selectedWh,
  })
  const { data: locations = [] } = useQuery({
    queryKey: ['locations', selectedWh?.id, selectedZone?.id],
    queryFn: () => getLocations(selectedWh.id, selectedZone.id),
    enabled: !!selectedWh && !!selectedZone,
  })
  // Map uchun: tanlangan zona yacheykalarini ko'rsatamiz
  const mapLocations = locations as any[]

  // Warehouse mutations
  const addWh = useMutation({
    mutationFn: createWarehouse,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['warehouses'] }); setShowWhForm(false); toast.success('Sklad yaratildi') },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
  })
  const patchWh = useMutation({
    mutationFn: ({ id, d }: any) => updateWarehouse(id, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['warehouses'] }); setEditWh(null); toast.success('Sklad yangilandi') },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
  })
  const removeWh = useMutation({
    mutationFn: (id: string) => deleteWarehouse(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['warehouses'] })
      if (selectedWh) setSelectedWh(null)
      toast.success("Sklad o'chirildi")
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
  })

  // Zone mutations
  const addZone = useMutation({
    mutationFn: (d: any) => createZone(selectedWh.id, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['zones'] }); setShowZoneForm(false); toast.success('Zona yaratildi') },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
  })
  const patchZone = useMutation({
    mutationFn: ({ id, d }: any) => updateZone(selectedWh.id, id, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['zones'] }); setEditZone(null); toast.success('Zona yangilandi') },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
  })
  const removeZone = useMutation({
    mutationFn: (id: string) => deleteZone(selectedWh.id, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['zones'] })
      if (selectedZone) setSelectedZone(null)
      toast.success("Zona o'chirildi")
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
  })

  // Location mutations
  const addLoc = useMutation({
    mutationFn: (d: any) => createLocation(selectedWh.id, selectedZone.id, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['locations'] }); setShowLocForm(false); toast.success('Yacheyka yaratildi') },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
  })
  const removeLoc = useMutation({
    mutationFn: (lid: string) => deleteLocation(selectedWh.id, selectedZone.id, lid),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['locations'] }); toast.success("Yacheyka o'chirildi") },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
  })

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
      <PageHeader
        icon={<Warehouse size={20} />}
        title="Skladlar"
        subtitle="Sklad, zona va yacheykalarni boshqaring"
        actions={<Button onClick={() => setShowWhForm(true)} icon={<Plus size={15} />}>Sklad qo'shish</Button>}
      />

      {showWhForm && (
        <QuickForm
          title="Yangi sklad"
          fields={[
            { name: 'name', label: 'Nomi', required: true },
            { name: 'address', label: 'Manzil' },
            { name: 'smartup_warehouse_code', label: 'Smartup kodi' },
          ]}
          onSubmit={(d: any) => addWh.mutate(d)}
          onCancel={() => setShowWhForm(false)}
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Warehouses column */}
        <Card className="space-y-1">
          <CardHeader icon={<MapPin size={16} />} title="Skladlar" />
          {(warehouses as any[]).map((wh: any) => (
            <div key={wh.id}>
              {editWh?.id === wh.id ? (
                <QuickForm
                  title="Tahrirlash"
                  fields={[
                    { name: 'name', label: 'Nomi', required: true },
                    { name: 'address', label: 'Manzil' },
                    { name: 'smartup_warehouse_code', label: 'Smartup kodi' },
                  ]}
                  onSubmit={(d: any) => patchWh.mutate({ id: wh.id, d })}
                  onCancel={() => setEditWh(null)}
                  submitLabel="Yangilash"
                />
              ) : (
                <div
                  className={`flex items-center gap-1 rounded-lg px-2 py-1.5 transition group cursor-pointer border ${selectedWh?.id === wh.id ? 'border-blue-500/40 bg-blue-500/10' : 'border-transparent hover:bg-slate-500/5'}`}
                  onClick={() => { setSelectedWh(wh); setSelectedZone(null) }}
                >
                  <span className={`flex-1 text-sm ${selectedWh?.id === wh.id ? 'text-blue-600 font-medium' : 'text-slate-700'}`}>
                    {wh.name}
                  </span>
                  <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition" onClick={e => e.stopPropagation()}>
                    <button onClick={() => setEditWh(wh)} className="p-1 text-slate-400 hover:text-blue-500 rounded">
                      <Pencil size={12} />
                    </button>
                    <button
                      onClick={() => { if (confirm(`"${wh.name}" skladini o'chirasizmi?`)) removeWh.mutate(wh.id) }}
                      className="p-1 text-slate-400 hover:text-rose-500 rounded"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                  <ChevronRight size={14} className="text-slate-300 shrink-0" />
                </div>
              )}
            </div>
          ))}
          {(warehouses as any[]).length === 0 && <p className="text-xs text-slate-400 py-2">Hali sklad yo'q</p>}
        </Card>

        {/* Zones column */}
        <Card className="space-y-1">
          <CardHeader
            icon={<Layers size={16} />}
            title="Zonalar"
            action={selectedWh ? (
              <Button size="icon" variant="ghost" onClick={() => setShowZoneForm(true)} className="h-8 w-8">
                <Plus size={16} />
              </Button>
            ) : undefined}
          />

          {showZoneForm && selectedWh && (
            <QuickForm
              title="Yangi zona"
              fields={[
                { name: 'name', label: 'Nomi', required: true },
                { name: 'zone_type', label: 'Tur', type: 'select', options: ZONE_TYPES, required: true },
                { name: 'x', label: 'X (xarita)', type: 'number' },
                { name: 'y', label: 'Y (xarita)', type: 'number' },
                { name: 'width', label: 'Kenglik', type: 'number' },
                { name: 'height', label: 'Balandlik', type: 'number' },
              ]}
              onSubmit={(d: any) => addZone.mutate(d)}
              onCancel={() => setShowZoneForm(false)}
            />
          )}

          {(zones as any[]).map((z: any) => (
            <div key={z.id}>
              {editZone?.id === z.id ? (
                <QuickForm
                  title="Zona tahrirlash"
                  fields={[
                    { name: 'name', label: 'Nomi' },
                    { name: 'zone_type', label: 'Tur', type: 'select', options: ZONE_TYPES },
                    { name: 'x', label: 'X', type: 'number' },
                    { name: 'y', label: 'Y', type: 'number' },
                    { name: 'width', label: 'Kenglik', type: 'number' },
                    { name: 'height', label: 'Balandlik', type: 'number' },
                  ]}
                  onSubmit={(d: any) => patchZone.mutate({ id: z.id, d })}
                  onCancel={() => setEditZone(null)}
                  submitLabel="Yangilash"
                />
              ) : (
                <div
                  className={`flex items-center gap-1 rounded-lg px-2 py-1.5 transition group cursor-pointer border ${selectedZone?.id === z.id ? 'border-blue-500/40 bg-blue-500/10' : 'border-transparent hover:bg-slate-500/5'}`}
                  onClick={() => setSelectedZone(z)}
                >
                  <div
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: ZONE_COLORS[z.zone_type] ?? '#94a3b8' }}
                  />
                  <span className={`flex-1 text-sm ${selectedZone?.id === z.id ? 'text-blue-600 font-medium' : 'text-slate-700'}`}>
                    {z.name}
                    <span className="ml-1.5 text-xs text-slate-400">{z.zone_type}</span>
                  </span>
                  <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition" onClick={e => e.stopPropagation()}>
                    <button onClick={() => setEditZone(z)} className="p-1 text-slate-400 hover:text-blue-500 rounded">
                      <Pencil size={12} />
                    </button>
                    <button
                      onClick={() => { if (confirm(`"${z.name}" zonasini o'chirasizmi?`)) removeZone.mutate(z.id) }}
                      className="p-1 text-slate-400 hover:text-rose-500 rounded"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                  <ChevronRight size={14} className="text-slate-300 shrink-0" />
                </div>
              )}
            </div>
          ))}
          {selectedWh && (zones as any[]).length === 0 && <p className="text-xs text-slate-400 py-2">Zona yo'q</p>}
          {!selectedWh && <p className="text-xs text-slate-400 py-2">Sklad tanlang</p>}
        </Card>

        {/* Locations column */}
        <Card className="space-y-1">
          <CardHeader
            title="Yacheykalar"
            action={selectedZone ? (
              <Button size="icon" variant="ghost" onClick={() => setShowLocForm(true)} className="h-8 w-8">
                <Plus size={16} />
              </Button>
            ) : undefined}
          />

          {showLocForm && selectedZone && (
            <QuickForm
              title="Yangi yacheyka"
              fields={[
                { name: 'code', label: 'Kod (A-01-01)', required: true },
                { name: 'location_type', label: 'Tur', type: 'select', options: LOC_TYPES, required: true },
                { name: 'barcode', label: 'Barkod' },
                { name: 'row', label: 'Qator' },
                { name: 'rack', label: 'Stellaj', type: 'number' },
                { name: 'tier', label: 'Yarus', type: 'number' },
                { name: 'position', label: 'Pozitsiya', type: 'number' },
              ]}
              onSubmit={(d: any) => addLoc.mutate(d)}
              onCancel={() => setShowLocForm(false)}
            />
          )}

          <div className="max-h-72 overflow-y-auto space-y-0.5 pr-1">
            {(locations as any[]).map((l: any) => (
              <div key={l.id} className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-slate-500/5 group">
                <span className="font-mono text-xs text-slate-700">{l.code}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">{l.location_type}</span>
                  <StatusBadge status={l.status} />
                  <button
                    onClick={() => { if (confirm(`"${l.code}" yacheykasini o'chirasizmi?`)) removeLoc.mutate(l.id) }}
                    className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-300 hover:text-rose-500 transition"
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
          {selectedZone && (locations as any[]).length === 0 && <p className="text-xs text-slate-400 py-2">Yacheyka yo'q</p>}
          {!selectedZone && <p className="text-xs text-slate-400 py-2">Zona tanlang</p>}
        </Card>
      </div>

      {/* 2D Map section */}
      {selectedWh && (
        <Card>
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <h2 className="font-semibold text-slate-700 flex items-center gap-2">
              <Map size={16} className="text-blue-500" /> Sklad xaritasi — {selectedWh.name}
            </h2>
            <Tabs
              size="sm"
              active={viewMode}
              onChange={(id) => setViewMode(id as 'list' | 'map')}
              items={[
                { id: 'list', label: "Ro'yxat", icon: List },
                { id: 'map', label: 'Xarita', icon: Map },
              ]}
            />
          </div>

          {viewMode === 'map' ? (
            <WarehouseMap
              zones={zones as any[]}
              locations={mapLocations}
              warehouseId={selectedWh.id}
              onZoneMoved={(zoneId, x, y) =>
                patchZone.mutate({ id: zoneId, d: { x, y } })
              }
            />
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
              {(zones as any[]).map((z: any) => (
                <div
                  key={z.id}
                  className="rounded-lg p-3 border cursor-pointer transition hover:shadow-sm"
                  style={{ borderColor: ZONE_COLORS[z.zone_type] + '44', background: ZONE_COLORS[z.zone_type] + '11' }}
                  onClick={() => setSelectedZone(z)}
                >
                  <div className="flex items-center gap-1.5 mb-1">
                    <div className="w-2 h-2 rounded-full" style={{ background: ZONE_COLORS[z.zone_type] ?? '#94a3b8' }} />
                    <span className="text-xs font-semibold text-slate-700">{z.name}</span>
                  </div>
                  <span className="text-xs text-slate-400">{z.zone_type}</span>
                </div>
              ))}
              {(zones as any[]).length === 0 && (
                <p className="col-span-4 text-xs text-slate-400 py-4">Zona qo'shilmagan</p>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
