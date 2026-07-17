import { useState, useEffect, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getWarehouses,
  getZones,
  getAllLocations,
  updateZone,
  updateZoneRules,
  getSlottingWeights,
  updateSlottingWeights,
  createZone,
  createLocation,
  deleteLocationById,
  updateLocationById,
} from '../lib/api'
import { Stage, Layer, Rect, Text, Group } from 'react-konva'
import { Map, Save, Sliders, Warehouse as WhIcon, Truck, Plus, Grid3x3 } from 'lucide-react'
import toast from 'react-hot-toast'

// ── Konstantalar ─────────────────────────────────────────────────────────────
const CANVAS_W = 820
const CANVAS_H = 540
const ZONE_DEFAULT_W = 160
const ZONE_DEFAULT_H = 110
const COLS = 4

const ABC_CLASSES = ['A', 'B', 'C']

const ZONE_COLORS: Record<string, string> = {
  reserve: '#3b82f6',
  pick: '#10b981',
  open_pallet: '#f59e0b',
  staging: '#8b5cf6',
  dock: '#0f766e',
  quarantine: '#ef4444',
  return: '#f97316',
}

const LOC_STATUS_COLORS: Record<string, string> = {
  empty: '#d1fae5',
  occupied: '#bfdbfe',
  partial: '#fef3c7',
  blocked: '#fee2e2',
}

const WEIGHT_KEYS = [
  'zone_match',
  'consolidation',
  'fefo',
  'capacity',
  'dock_proximity',
  'weight_tier',
] as const

function defaultPos(index: number) {
  const col = index % COLS
  const row = Math.floor(index / COLS)
  return { x: 16 + col * (ZONE_DEFAULT_W + 16), y: 16 + row * (ZONE_DEFAULT_H + 16) }
}

type Coords = { x: number; y: number; width: number; height: number }

// ── Map canvasi ──────────────────────────────────────────────────────────────
function MapCanvas({
  zones,
  coords,
  locations,
  selectedZoneId,
  onSelect,
  onZoneMoved,
}: {
  zones: any[]
  coords: Record<string, Coords>
  locations: any[]
  selectedZoneId: string | null
  onSelect: (zone: any) => void
  onZoneMoved: (zoneId: string, x: number, y: number) => void
}) {
  const [dragging, setDragging] = useState<string | null>(null)

  const locsByZone = useMemo(() => {
    const m: Record<string, any[]> = {}
    for (const loc of locations) {
      if (!m[loc.zone_id]) m[loc.zone_id] = []
      m[loc.zone_id].push(loc)
    }
    return m
  }, [locations])

  if (zones.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-slate-400 bg-slate-50 rounded-xl border-2 border-dashed border-slate-200">
        <Map size={28} className="mb-2 opacity-40" />
        <p className="text-sm">Bu skladda zona yo'q</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-50">
      <div className="px-3 py-2 border-b border-slate-200 bg-white text-xs text-slate-400">
        Zonalarni sudrab joylashtiring — keyin "Saqlash" tugmasini bosing
      </div>
      <Stage width={CANVAS_W} height={CANVAS_H}>
        <Layer>
          {/* Grid */}
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

          {zones.map((zone) => {
            const c = coords[zone.id]
            if (!c) return null
            const { x, y, width: w, height: h } = c
            const color = ZONE_COLORS[zone.zone_type] ?? '#94a3b8'
            const isDock = zone.zone_type === 'dock'
            const isSelected = selectedZoneId === zone.id
            const isDragging = dragging === zone.id
            const zoneLocs = locsByZone[zone.id] ?? []

            const cellSize = 13
            const gap = 3
            const padding = 6
            const cols = Math.max(1, Math.floor((w - padding * 2) / (cellSize + gap)))
            const rows = Math.max(0, Math.floor((h - 34) / (cellSize + gap)))

            return (
              <Group
                key={zone.id}
                x={x}
                y={y}
                draggable
                opacity={isDragging ? 0.75 : 1}
                onClick={() => onSelect(zone)}
                onTap={() => onSelect(zone)}
                onDragStart={() => setDragging(zone.id)}
                onDragEnd={(e) => {
                  setDragging(null)
                  onZoneMoved(zone.id, Math.round(e.target.x()), Math.round(e.target.y()))
                }}
              >
                {/* Tana */}
                <Rect
                  width={w}
                  height={h}
                  fill={color + (isDock ? '30' : '18')}
                  stroke={isSelected ? '#1d4ed8' : isDock ? color : color + 'aa'}
                  strokeWidth={isSelected ? 3 : isDock ? 2.5 : 1.5}
                  dash={isDock ? [8, 4] : undefined}
                  cornerRadius={6}
                  shadowColor={isSelected || isDragging ? color : 'transparent'}
                  shadowBlur={isSelected || isDragging ? 12 : 0}
                  shadowOpacity={0.4}
                />
                {/* Dock belgisi */}
                {isDock && (
                  <Text
                    x={w - 18}
                    y={6}
                    text="⚓"
                    fontSize={13}
                  />
                )}
                {/* Nom */}
                <Text
                  x={padding}
                  y={6}
                  text={zone.name}
                  fontSize={11}
                  fill={color}
                  fontStyle="bold"
                  width={w - padding * 2 - (isDock ? 16 : 0)}
                  ellipsis
                />
                <Text
                  x={padding}
                  y={19}
                  text={zone.zone_type}
                  fontSize={9}
                  fill={color + '99'}
                  width={w - padding * 2}
                />
                {/* Yacheykalar */}
                {zoneLocs.slice(0, cols * rows).map((loc, i) => {
                  const col = i % cols
                  const row = Math.floor(i / cols)
                  return (
                    <Rect
                      key={loc.id}
                      x={padding + col * (cellSize + gap)}
                      y={32 + row * (cellSize + gap)}
                      width={cellSize}
                      height={cellSize}
                      fill={LOC_STATUS_COLORS[loc.status] ?? '#f1f5f9'}
                      stroke="#e2e8f0"
                      strokeWidth={0.5}
                      cornerRadius={2}
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

      {/* Legenda */}
      <div className="flex flex-wrap items-center gap-3 px-3 py-2 border-t border-slate-200 bg-white">
        {Object.entries(LOC_STATUS_COLORS).map(([status, color]) => (
          <div key={status} className="flex items-center gap-1.5 text-xs text-slate-500">
            <div className="w-3 h-3 rounded-sm border border-slate-200" style={{ background: color }} />
            {status}
          </div>
        ))}
        <div className="flex items-center gap-1.5 text-xs text-slate-500 ml-auto">
          <Truck size={12} className="text-teal-700" /> DOCK zona (dock-yaqinlik uchun)
        </div>
      </div>
    </div>
  )
}

// ── Asosiy sahifa ────────────────────────────────────────────────────────────
export default function WarehouseMap() {
  const qc = useQueryClient()
  const [warehouseId, setWarehouseId] = useState<string | null>(null)
  const [selectedZone, setSelectedZone] = useState<any>(null)
  const [zoneSearch, setZoneSearch] = useState('')
  const [coords, setCoords] = useState<Record<string, Coords>>({})
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  // putaway_rules tahrir holati
  const [rules, setRules] = useState<any>({})
  const [savingRules, setSavingRules] = useState(false)

  // slotting weights
  const [weights, setWeights] = useState<Record<string, number>>({})
  const [savingWeights, setSavingWeights] = useState(false)

  // ── So'rovlar ──
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })

  useEffect(() => {
    if (!warehouseId && (warehouses as any[]).length > 0) {
      setWarehouseId((warehouses as any[])[0].id)
    }
  }, [warehouses, warehouseId])

  const { data: zones = [] } = useQuery({
    queryKey: ['zones', warehouseId],
    queryFn: () => getZones(warehouseId as string),
    enabled: !!warehouseId,
  })

  const { data: locations = [] } = useQuery({
    queryKey: ['all-locations', warehouseId],
    queryFn: () => getAllLocations(warehouseId as string),
    enabled: !!warehouseId,
  })

  const { data: weightsData } = useQuery({
    queryKey: ['slotting-weights', warehouseId],
    queryFn: () => getSlottingWeights(warehouseId as string),
    enabled: !!warehouseId,
  })

  // ── Zonalardan koordinatalarni boshlash ──
  useEffect(() => {
    const next: Record<string, Coords> = {}
    ;(zones as any[]).forEach((z, idx) => {
      const def = defaultPos(idx)
      next[z.id] = {
        x: z.x ?? def.x,
        y: z.y ?? def.y,
        width: z.width ?? ZONE_DEFAULT_W,
        height: z.height ?? ZONE_DEFAULT_H,
      }
    })
    setCoords(next)
    setDirty(false)
  }, [zones])

  // ── Weights holatini boshlash ──
  useEffect(() => {
    if (weightsData) {
      const next: Record<string, number> = {}
      for (const k of WEIGHT_KEYS) next[k] = Number((weightsData as Record<string, any>)[k] ?? 0)
      setWeights(next)
    }
  }, [weightsData])

  // ── Zona tanlanganda rules holatini yangilash ──
  useEffect(() => {
    if (selectedZone) {
      const pr = selectedZone.putaway_rules ?? {}
      setRules({
        blocked: !!pr.blocked,
        abc: Array.isArray(pr.abc) ? pr.abc : [],
        categories: Array.isArray(pr.categories) ? pr.categories.join(', ') : (pr.categories ?? ''),
        min_volume: pr.min_volume ?? '',
        max_volume: pr.max_volume ?? '',
      })
    }
  }, [selectedZone])

  // ── Drag handler ──
  const handleZoneMoved = (zoneId: string, x: number, y: number) => {
    setCoords((c) => ({ ...c, [zoneId]: { ...c[zoneId], x, y } }))
    setDirty(true)
  }

  // ── Koordinatalarni saqlash ──
  const handleSaveCoords = async () => {
    if (!warehouseId) return
    setSaving(true)
    try {
      const changed = (zones as any[]).filter((z) => {
        const c = coords[z.id]
        if (!c) return false
        return c.x !== z.x || c.y !== z.y || c.width !== z.width || c.height !== z.height
      })
      for (const z of changed) {
        const c = coords[z.id]
        await updateZone(warehouseId, z.id, {
          x: c.x,
          y: c.y,
          width: c.width,
          height: c.height,
        })
      }
      await qc.invalidateQueries({ queryKey: ['zones', warehouseId] })
      setDirty(false)
      toast.success(`${changed.length} ta zona o'rni saqlandi`)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Saqlashda xatolik')
    } finally {
      setSaving(false)
    }
  }

  // ── putaway_rules saqlash ──
  const handleSaveRules = async () => {
    if (!selectedZone) return
    setSavingRules(true)
    try {
      const putaway_rules: any = {
        blocked: !!rules.blocked,
        abc: rules.abc,
        categories: String(rules.categories || '')
          .split(',')
          .map((s: string) => s.trim())
          .filter(Boolean),
      }
      if (rules.min_volume !== '' && rules.min_volume != null) putaway_rules.min_volume = Number(rules.min_volume)
      if (rules.max_volume !== '' && rules.max_volume != null) putaway_rules.max_volume = Number(rules.max_volume)

      const updated = await updateZoneRules(selectedZone.id, { putaway_rules })
      await qc.invalidateQueries({ queryKey: ['zones', warehouseId] })
      setSelectedZone((z: any) => ({ ...z, putaway_rules: updated?.putaway_rules ?? putaway_rules }))
      toast.success('Qoidalar saqlandi')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Saqlashda xatolik')
    } finally {
      setSavingRules(false)
    }
  }

  // ── Yacheyka (cell) soni: stellajga qo'shish / o'chirish ──
  const zoneLocations = useMemo(
    () => (locations as any[]).filter((l) => l.zone_id === selectedZone?.id),
    [locations, selectedZone],
  )
  const [cellTarget, setCellTarget] = useState<string>('')
  const [busyCells, setBusyCells] = useState(false)

  useEffect(() => {
    setCellTarget(selectedZone ? String(zoneLocations.length) : '')
  }, [selectedZone, zoneLocations.length])

  const applyCellCount = async () => {
    if (!selectedZone || !warehouseId) return
    const target = parseInt(cellTarget, 10)
    if (!Number.isFinite(target) || target < 0) { toast.error("Noto'g'ri son"); return }
    const current = zoneLocations.length
    if (target === current) return
    setBusyCells(true)
    try {
      const base = (selectedZone.name || 'CELL').replace(/\s+/g, '-')
      if (target > current) {
        // mavjud raqamlardan keyin davom etamiz (kod to'qnashuvini oldini olish)
        let n = zoneLocations.reduce((m: number, l: any) => Math.max(m, l.position ?? 0), 0)
        for (let i = current; i < target; i++) {
          n += 1
          const code = `${base}-${String(n).padStart(2, '0')}`
          await createLocation(warehouseId, selectedZone.id, {
            code, barcode: code, location_type: 'pallet', position: n, max_pallets: 1,
          })
        }
      } else {
        // faqat BO'SH yacheykalarni o'chiramiz (mahsulot borlari saqlanadi)
        const empty = zoneLocations.filter((l: any) => String(l.status).toLowerCase() === 'empty')
        const need = current - target
        if (empty.length < need) {
          toast.error(`Faqat ${empty.length} ta bo'sh yacheyka o'chirish mumkin — qolganlarida mahsulot/bron bor`)
        }
        const slice = empty.slice(-Math.min(need, empty.length))
        for (const l of slice) await deleteLocationById(warehouseId, l.id)
      }
      await qc.invalidateQueries({ queryKey: ['all-locations', warehouseId] })
      toast.success('Yacheykalar yangilandi')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Xatolik')
    } finally {
      setBusyCells(false)
    }
  }

  const addRack = async () => {
    if (!warehouseId) return
    const name = window.prompt('Yangi stellaj nomi:', 'Stellaj')
    if (!name) return
    const cnt = parseInt(window.prompt('Nechta yacheyka?', '6') || '0', 10)
    if (!Number.isFinite(cnt) || cnt < 0) { toast.error("Noto'g'ri son"); return }
    setBusyCells(true)
    try {
      const zone = await createZone(warehouseId, { name, zone_type: 'reserve' })
      const base = name.replace(/\s+/g, '-')
      for (let i = 0; i < cnt; i++) {
        const code = `${base}-${String(i + 1).padStart(2, '0')}`
        await createLocation(warehouseId, zone.id, {
          code, barcode: code, location_type: 'pallet', position: i + 1, max_pallets: 1,
        })
      }
      await qc.invalidateQueries({ queryKey: ['zones', warehouseId] })
      await qc.invalidateQueries({ queryKey: ['all-locations', warehouseId] })
      toast.success(`"${name}" stellaji ${cnt} yacheyka bilan qo'shildi`)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Xatolik')
    } finally {
      setBusyCells(false)
    }
  }

  // ── Stellaj (zona) nomini o'zgartirish ──
  const [zoneName, setZoneName] = useState('')
  useEffect(() => { setZoneName(selectedZone?.name ?? '') }, [selectedZone])

  const renameZone = async () => {
    if (!selectedZone || !warehouseId || !zoneName.trim() || zoneName.trim() === selectedZone.name) return
    setBusyCells(true)
    try {
      await updateZone(warehouseId, selectedZone.id, { name: zoneName.trim() })
      await qc.invalidateQueries({ queryKey: ['zones', warehouseId] })
      setSelectedZone((z: any) => ({ ...z, name: zoneName.trim() }))
      toast.success("Stellaj nomi o'zgartirildi")
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Xatolik')
    } finally { setBusyCells(false) }
  }

  // ── Yacheyka kodini o'zgartirish ──
  const renameCell = async (loc: any, newCode: string) => {
    const code = newCode.trim()
    if (!warehouseId || !code || code === loc.code) return
    try {
      await updateLocationById(warehouseId, loc.id, { code, barcode: code })
      await qc.invalidateQueries({ queryKey: ['all-locations', warehouseId] })
      toast.success('Yacheyka kodi o\'zgartirildi')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Xatolik')
    }
  }

  const toggleAbc = (cls: string) => {
    setRules((r: any) => {
      const has = (r.abc ?? []).includes(cls)
      return { ...r, abc: has ? r.abc.filter((a: string) => a !== cls) : [...(r.abc ?? []), cls] }
    })
  }

  // ── Weights saqlash ──
  const handleSaveWeights = async () => {
    setSavingWeights(true)
    try {
      const payload: Record<string, number> = {}
      for (const k of WEIGHT_KEYS) payload[k] = Number(weights[k] ?? 0)
      await updateSlottingWeights(payload)
      await qc.invalidateQueries({ queryKey: ['slotting-weights'] })
      toast.success('Slotting vaznlari saqlandi')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Saqlashda xatolik')
    } finally {
      setSavingWeights(false)
    }
  }

  return (
    <div className="p-4 lg:p-6 space-y-4">
      {/* Sarlavha + sklad selektori */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <Map size={20} className="text-blue-500" /> Sklad xaritasi
        </h1>
        <div className="flex items-center gap-2">
          {/* Zona qidiruv → topilganini tanlaydi/belgilaydi */}
          <input
            value={zoneSearch}
            onChange={(e) => {
              const v = e.target.value
              setZoneSearch(v)
              const s = v.trim().toLowerCase()
              if (s) {
                const hit = (zones as any[]).find((z: any) =>
                  String(z.name ?? '').toLowerCase().includes(s) || String(z.code ?? '').toLowerCase().includes(s))
                if (hit) setSelectedZone(hit)
              }
            }}
            placeholder="Zona qidirish…"
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white w-40"
          />
          <div className="flex items-center gap-1.5 text-sm text-slate-500">
            <WhIcon size={14} /> Sklad:
          </div>
          <select
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white"
            value={warehouseId ?? ''}
            onChange={(e) => {
              setWarehouseId(e.target.value || null)
              setSelectedZone(null)
            }}
          >
            <option value="">Tanlang</option>
            {(warehouses as any[]).map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
          <button
            onClick={addRack}
            disabled={!warehouseId || busyCells}
            className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition"
          >
            <Plus size={14} /> Stellaj qo'shish
          </button>
          <button
            onClick={handleSaveCoords}
            disabled={!dirty || saving}
            className={`flex items-center gap-1.5 text-sm px-3 py-2 rounded-lg transition ${
              dirty && !saving
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-slate-100 text-slate-400 cursor-not-allowed'
            }`}
          >
            <Save size={14} /> {saving ? 'Saqlanmoqda…' : 'Saqlash'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Map */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm p-5">
          {warehouseId ? (
            <MapCanvas
              zones={zones as any[]}
              coords={coords}
              locations={locations as any[]}
              selectedZoneId={selectedZone?.id ?? null}
              onSelect={setSelectedZone}
              onZoneMoved={handleZoneMoved}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-slate-400">
              <WhIcon size={28} className="mb-2 opacity-40" />
              <p className="text-sm">Sklad tanlang</p>
            </div>
          )}
        </div>

        {/* Yon panel */}
        <div className="space-y-4">
          {/* Zona qoidalari */}
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-1.5">
              <Sliders size={14} /> Zona qoidalari
            </h2>
            {selectedZone ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{ background: ZONE_COLORS[selectedZone.zone_type] ?? '#94a3b8' }}
                  />
                  <span className="text-sm font-medium text-slate-700">{selectedZone.name}</span>
                  <span className="text-xs text-slate-400">{selectedZone.zone_type}</span>
                </div>

                {/* Stellaj nomi */}
                <div>
                  <label className="text-xs text-slate-500">Stellaj nomi</label>
                  <div className="flex items-center gap-2 mt-0.5">
                    <input
                      type="text"
                      className="flex-1 border border-slate-200 rounded px-2 py-1 text-sm"
                      value={zoneName}
                      onChange={(e) => setZoneName(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') renameZone() }}
                    />
                    <button
                      onClick={renameZone}
                      disabled={busyCells || !zoneName.trim() || zoneName.trim() === selectedZone.name}
                      className="text-sm px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      Saqlash
                    </button>
                  </div>
                </div>

                {/* Yacheykalar soni */}
                <div className="border border-slate-100 rounded-lg p-2.5 bg-slate-50/60">
                  <label className="text-xs text-slate-500 flex items-center gap-1.5 mb-1">
                    <Grid3x3 size={12} /> Yacheykalar soni
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={0}
                      className="w-20 border border-slate-200 rounded px-2 py-1 text-sm"
                      value={cellTarget}
                      onChange={(e) => setCellTarget(e.target.value)}
                    />
                    <button
                      onClick={applyCellCount}
                      disabled={busyCells || cellTarget === String(zoneLocations.length)}
                      className="text-sm px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition"
                    >
                      {busyCells ? '…' : "Qo'llash"}
                    </button>
                    <span className="text-xs text-slate-400">hozir: {zoneLocations.length}</span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1">
                    Kamaytirilsa faqat bo'sh yacheykalar o'chadi (mahsulotlilari saqlanadi).
                  </p>
                </div>

                {/* Yacheyka kodlari (nom o'zgartirish) */}
                {zoneLocations.length > 0 && (
                  <details className="border border-slate-100 rounded-lg p-2.5">
                    <summary className="text-xs text-slate-500 cursor-pointer select-none">
                      Yacheyka kodlari ({zoneLocations.length}) — nom o'zgartirish
                    </summary>
                    <div className="mt-2 space-y-1 max-h-56 overflow-auto">
                      {[...zoneLocations]
                        .sort((a: any, b: any) => String(a.code).localeCompare(String(b.code)))
                        .map((loc: any) => (
                          <input
                            key={loc.id}
                            type="text"
                            defaultValue={loc.code}
                            className="w-full border border-slate-200 rounded px-2 py-1 text-xs font-mono"
                            onBlur={(e) => renameCell(loc, e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
                          />
                        ))}
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1">Enter yoki boshqa joyni bosish bilan saqlanadi.</p>
                  </details>
                )}

                <label className="flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={!!rules.blocked}
                    onChange={(e) => setRules((r: any) => ({ ...r, blocked: e.target.checked }))}
                  />
                  Bloklangan (putaway taqiqlangan)
                </label>

                <div>
                  <label className="text-xs text-slate-500">ABC sinflari</label>
                  <div className="flex gap-2 mt-1">
                    {ABC_CLASSES.map((cls) => {
                      const active = (rules.abc ?? []).includes(cls)
                      return (
                        <button
                          key={cls}
                          onClick={() => toggleAbc(cls)}
                          className={`text-xs px-3 py-1 rounded border transition ${
                            active
                              ? 'bg-blue-600 text-white border-blue-600'
                              : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300'
                          }`}
                        >
                          {cls}
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div>
                  <label className="text-xs text-slate-500">Kategoriyalar (vergul bilan)</label>
                  <input
                    type="text"
                    className="w-full border border-slate-200 rounded px-2 py-1 text-sm mt-0.5"
                    placeholder="elektronika, oziq-ovqat"
                    value={rules.categories ?? ''}
                    onChange={(e) => setRules((r: any) => ({ ...r, categories: e.target.value }))}
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-slate-500">Min hajm (m³)</label>
                    <input
                      type="number"
                      step="any"
                      className="w-full border border-slate-200 rounded px-2 py-1 text-sm mt-0.5"
                      value={rules.min_volume ?? ''}
                      onChange={(e) => setRules((r: any) => ({ ...r, min_volume: e.target.value }))}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-500">Max hajm (m³)</label>
                    <input
                      type="number"
                      step="any"
                      className="w-full border border-slate-200 rounded px-2 py-1 text-sm mt-0.5"
                      value={rules.max_volume ?? ''}
                      onChange={(e) => setRules((r: any) => ({ ...r, max_volume: e.target.value }))}
                    />
                  </div>
                </div>

                <button
                  onClick={handleSaveRules}
                  disabled={savingRules}
                  className="w-full flex items-center justify-center gap-1.5 bg-blue-600 text-white text-sm px-3 py-2 rounded-lg hover:bg-blue-700 transition disabled:opacity-60"
                >
                  <Save size={14} /> {savingRules ? 'Saqlanmoqda…' : 'Qoidalarni saqlash'}
                </button>
              </div>
            ) : (
              <p className="text-xs text-slate-400 py-2">Xaritadan zona tanlang</p>
            )}
          </div>

          {/* Slotting vaznlari */}
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-1.5">
              <Sliders size={14} /> Slotting vaznlari
            </h2>
            <div className="space-y-2">
              {WEIGHT_KEYS.map((k) => (
                <div key={k} className="flex items-center justify-between gap-2">
                  <label className="text-xs text-slate-500 flex-1">{k}</label>
                  <input
                    type="number"
                    step="any"
                    className="w-24 border border-slate-200 rounded px-2 py-1 text-sm text-right"
                    value={weights[k] ?? ''}
                    onChange={(e) =>
                      setWeights((w) => ({ ...w, [k]: e.target.value === '' ? 0 : Number(e.target.value) }))
                    }
                  />
                </div>
              ))}
            </div>
            <button
              onClick={handleSaveWeights}
              disabled={savingWeights}
              className="w-full mt-3 flex items-center justify-center gap-1.5 bg-slate-700 text-white text-sm px-3 py-2 rounded-lg hover:bg-slate-800 transition disabled:opacity-60"
            >
              <Save size={14} /> {savingWeights ? 'Saqlanmoqda…' : 'Vaznlarni saqlash'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
