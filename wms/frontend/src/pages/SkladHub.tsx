/**
 * Sklad markazi — birlashtirilgan interaktiv xarita (P2).
 *  Tablar: Xarita (2D, tahrirlanadigan) · 3D Twin · Ro'yxat
 *  Imkoniyatlar:
 *   - 2 skladni bitta ko'rinishda ("Hammasi")
 *   - Tahrir rejimida slotni sudrab ko'chirish (drag) + katak/stellajni copy-paste
 *   - Yacheyka bosilganda: ichidagi transport+box+child kodlar daraxti, qoldiq, bron
 *   - Bron qilingan yacheykalar belgilanadi (real-time)
 *   - 2D va 3D — to'liq ekran (full-screen)
 */
import { useMemo, useRef, useState, lazy, Suspense } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getWarehouses, getZones, getAllLocations,
  updateLocationById, deleteLocationById, generateRack, setRackCells,
  bulkCreateLocations, getReservations, getLocationContents, fetchLocationCodeTree,
  getProductByGtin, getAslBelgisiProductCard,
} from '../lib/api'
import {
  Box, LayoutGrid, List, Layers, Pencil, Plus, Trash2, Save, X, Wand2,
  Maximize2, Minimize2, Copy, ClipboardPaste, Move, Boxes, Clock, Download,
} from 'lucide-react'
import toast from 'react-hot-toast'

const Warehouse3D = lazy(() => import('./Warehouse3D'))

const COMBINED = '__all__'
const STATUS_FILL: Record<string, string> = {
  occupied: '#16a34a', partial: '#d97706', blocked: '#dc2626', empty: '#e2e8f0',
}
const STATUS_BORDER: Record<string, string> = {
  occupied: '#15803d', partial: '#b45309', blocked: '#b91c1c', empty: '#cbd5e1',
}
const STATUS_LABEL: Record<string, string> = {
  occupied: 'Band', partial: 'Qisman', blocked: 'Bloklangan', empty: "Bo'sh",
}
const NEXT_STATUS: Record<string, string> = {
  empty: 'occupied', occupied: 'blocked', blocked: 'empty', partial: 'empty',
}

type Loc = {
  id: string; code: string; zone_id: string; status: string
  row: string | null; rack: number | null; tier: number | null; position: number | null
  x: number | null; y: number | null
  length_mm: number | null; width_mm: number | null; height_mm: number | null
  max_weight_kg: number | null; rack_group: string | null
  _wid: string; _wname: string; _ox: number
}
type Cell = {
  code: string; x: number; y: number; ox: number; row: string | null; rack_group: string | null
  zone_id: string; wid: string; wname: string; slots: Loc[]
}

function groupCells(locs: Loc[]): Cell[] {
  // GURUHLASH: stellaj (rack_group) bo'yicha — bitta quti = bitta stellaj, ichida yacheykalar.
  // rack_group bo'lmasa, kodning oxirgi "-N" segmentisiz qismi (yoki kod) ishlatiladi.
  const m = new Map<string, Cell>()
  for (const l of locs) {
    const rack = l.rack_group || l.code.replace(/-\d+$/, '') || l.code
    const key = `${l._wid}:${rack}`
    if (!m.has(key)) {
      m.set(key, {
        code: rack, x: l.x ?? 0, y: l.y ?? 0, ox: l._ox, row: l.row,
        rack_group: rack, zone_id: l.zone_id, wid: l._wid, wname: l._wname, slots: [],
      })
    }
    m.get(key)!.slots.push(l)
  }
  // har stellaj ichidagi yacheykalarni position/kod bo'yicha tartiblaymiz
  for (const c of m.values()) c.slots.sort((a, b) => (a.position ?? 0) - (b.position ?? 0) || a.code.localeCompare(b.code))
  return [...m.values()]
}

export default function SkladHub() {
  const qc = useQueryClient()
  const [tab, setTab] = useState<'2d' | '3d' | 'list'>('2d')
  const [editMode, setEditMode] = useState(false)
  const [whId, setWhId] = useState('')
  const [selCode, setSelCode] = useState<string | null>(null)   // "wid:code"
  const [genOpen, setGenOpen] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const [clipboard, setClipboard] = useState<{ kind: 'cell' | 'rack'; cells: Cell[] } | null>(null)
  const [pasteMode, setPasteMode] = useState(false)

  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const whList = warehouses as any[]
  const wid = whId || whList[0]?.id
  const combined = whId === COMBINED

  // Locations across one or all warehouses, annotated with offset for side-by-side layout.
  const { data: locations = [], isLoading } = useQuery({
    queryKey: ['hub-locations', whId, whList.length],
    enabled: whList.length > 0,
    retry: false,
    queryFn: async () => {
      const list = combined ? whList : whList.filter(w => w.id === wid)
      const all: Loc[] = []
      let offset = 0
      for (const w of list) {
        const locs = (await getAllLocations(w.id)) as any[]
        const maxX = locs.reduce((mx, l) => Math.max(mx, l.x ?? 0), 0)
        for (const l of locs) all.push({ ...l, _wid: w.id, _wname: w.name, _ox: offset })
        offset += maxX + 8 // gap (m) between two warehouses
      }
      return all
    },
  })

  const { data: zones = [] } = useQuery({
    queryKey: ['zones', wid], queryFn: () => getZones(wid), enabled: !!wid && !combined,
  })

  // Reserved location ids (bron overlay).
  const { data: reservations = [] } = useQuery({
    queryKey: ['hub-reservations', whId, whList.length],
    enabled: whList.length > 0,
    refetchInterval: 15000,
    queryFn: async () => {
      const list = combined ? whList : whList.filter(w => w.id === wid)
      const out: any[] = []
      for (const w of list) {
        try { out.push(...(await getReservations(w.id))) } catch { /* ignore */ }
      }
      return out
    },
  })
  const reservedLocIds = useMemo(
    () => new Set((reservations as any[]).map(r => r.location_id)), [reservations])

  const cells = useMemo(() => groupCells(locations as Loc[]), [locations])
  const selCell = cells.find(c => `${c.wid}:${c.code}` === selCode) || null

  const bounds = useMemo(() => {
    if (cells.length === 0) return { maxX: 40, maxY: 16 }
    return {
      maxX: Math.max(...cells.map(c => c.x + c.ox)) + 3,
      maxY: Math.max(...cells.map(c => c.y)) + 2.5,
    }
  }, [cells])

  const PAD = 24
  const SCALE = Math.min(1180 / bounds.maxX, 70)
  const m = (v: number) => v * SCALE
  const SVG_W = bounds.maxX * SCALE + PAD * 2
  const SVG_H = bounds.maxY * SCALE + PAD * 2

  const stats = useMemo(() => {
    let occ = 0, part = 0, blk = 0
    for (const l of locations as Loc[]) {
      if (l.status === 'occupied') occ++
      else if (l.status === 'partial') part++
      else if (l.status === 'blocked') blk++
    }
    const total = (locations as Loc[]).length
    return { total, occ, part, blk, free: total - occ - part - blk, cells: cells.length }
  }, [locations, cells])

  const reload = () => qc.invalidateQueries({ queryKey: ['hub-locations'] })

  const cycleSlot = async (loc: Loc) => {
    const next = NEXT_STATUS[loc.status] ?? 'empty'
    try { await updateLocationById(loc._wid, loc.id, { status: next }); reload() }
    catch { toast.error('Saqlashda xatolik') }
  }

  // ── Drag-to-move (edit mode) ───────────────────────────────────────────────
  const svgRef = useRef<SVGSVGElement>(null)
  const [drag, setDrag] = useState<{ key: string; dx: number; dy: number; x: number; y: number } | null>(null)

  const svgPoint = (e: React.PointerEvent) => {
    const svg = svgRef.current!
    const r = svg.getBoundingClientRect()
    return { px: e.clientX - r.left, py: e.clientY - r.top }
  }
  const onCellPointerDown = (e: React.PointerEvent, cell: Cell) => {
    if (!editMode || pasteMode) return
    e.stopPropagation()
    const { px, py } = svgPoint(e)
    const cx = PAD + m(cell.x + cell.ox), cy = PAD + m(cell.y)
    setDrag({ key: `${cell.wid}:${cell.code}`, dx: px - cx, dy: py - cy, x: cell.x, y: cell.y })
    setSelCode(`${cell.wid}:${cell.code}`)
  }
  const onSvgPointerMove = (e: React.PointerEvent) => {
    if (!drag) return
    const { px, py } = svgPoint(e)
    const cell = cells.find(c => `${c.wid}:${c.code}` === drag.key)
    if (!cell) return
    const nx = (px - drag.dx - PAD) / SCALE - cell.ox
    const ny = (py - drag.dy - PAD) / SCALE
    setDrag({ ...drag, x: Math.max(0, +nx.toFixed(2)), y: Math.max(0, +ny.toFixed(2)) })
  }
  const onSvgPointerUp = async () => {
    if (!drag) return
    const cell = cells.find(c => `${c.wid}:${c.code}` === drag.key)
    const d = drag
    setDrag(null)
    // Grid'ga yopishtirish (snap) — tekis tizilishi uchun: x→1m, y→1m
    const sx = Math.max(0, Math.round(d.x))
    const sy = Math.max(0, Math.round(d.y))
    if (!cell || (Math.abs(cell.x - sx) < 0.05 && Math.abs(cell.y - sy) < 0.05)) return
    try {
      for (const s of cell.slots) await updateLocationById(cell.wid, s.id, { x: sx, y: sy })
      reload()
    } catch { toast.error('Ko\'chirishda xatolik') }
  }

  // ── Copy / paste cell or rack ──────────────────────────────────────────────
  const copyCell = (cell: Cell) => {
    setClipboard({ kind: 'cell', cells: [cell] }); setPasteMode(true)
    toast.success('Katak nusxalandi — joylash uchun xaritani bosing')
  }
  const copyRack = (cell: Cell) => {
    const rg = cell.rack_group
    const group = cells.filter(c => c.wid === cell.wid && c.rack_group === rg)
    if (!rg || group.length === 0) { toast.error('rack_group yo\'q'); return }
    setClipboard({ kind: 'rack', cells: group }); setPasteMode(true)
    toast.success(`Stellaj nusxalandi (${group.length} katak) — joylash joyini bosing`)
  }
  const pasteAt = async (modelX: number, modelY: number, targetWid: string) => {
    if (!clipboard) return
    const base = clipboard.cells
    const ax = Math.min(...base.map(c => c.x)), ay = Math.min(...base.map(c => c.y))
    const suffix = '-K' + Math.floor(Math.random() * 900 + 100)
    // group by zone for bulk create
    const byZone = new Map<string, any[]>()
    for (const c of base) {
      const arr = byZone.get(c.zone_id) ?? []
      const f = c.slots[0]
      for (const s of c.slots) {
        arr.push({
          code: c.code + suffix, barcode: null,
          location_type: 'pallet', status: 'empty',
          row: c.row, rack: s.rack, tier: s.tier, position: s.position,
          x: +(modelX + (c.x - ax)).toFixed(2), y: +(modelY + (c.y - ay)).toFixed(2),
          length_mm: f.length_mm, width_mm: f.width_mm, height_mm: f.height_mm,
          max_weight_kg: f.max_weight_kg, rack_group: (c.rack_group ?? 'X') + suffix,
        })
      }
      byZone.set(c.zone_id, arr)
    }
    try {
      for (const [zoneId, locs] of byZone) await bulkCreateLocations(targetWid, zoneId, locs)
      toast.success('Joylashtirildi'); setPasteMode(false); setClipboard(null); reload()
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? 'Xatolik') }
  }
  const onCanvasClick = (e: React.PointerEvent) => {
    if (!pasteMode || !clipboard) return
    const { px, py } = svgPoint(e)
    const mx = (px - PAD) / SCALE, my = (py - PAD) / SCALE
    // paste into the warehouse whose offset band the click lands in
    const target = combined
      ? [...cells].sort((a, b) => (a.ox - b.ox))
          .reduce((best, c) => (mx >= c.ox ? c : best), cells[0])
      : cells[0]
    const tWid = target?.wid ?? wid
    const tOx = target?.ox ?? 0
    pasteAt(+(mx - tOx).toFixed(2), +my.toFixed(2), tWid)
  }

  const wrapCls = fullscreen ? 'fixed inset-0 z-50 bg-white p-4 overflow-auto' : ''

  return (
    <div className="p-4 lg:p-6 space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Box size={20} className="text-blue-500" /> Sklad xaritasi
          </h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {tab === '2d' ? '2D interaktiv xarita' : tab === '3d' ? '3D hajmiy ko\'rinish' : 'Yacheykalar ro\'yxati'}
            {editMode && tab === '2d' && ' — ✏️ Tahrir rejimi (slotni sudrab ko\'chiring)'}
            {pasteMode && ' — 📋 Joylash rejimi'}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex rounded-lg border border-slate-200 overflow-hidden text-sm">
            {([['2d', '2D', LayoutGrid], ['3d', '3D', Box], ['list', 'Ro\'yxat', List]] as const).map(([k, lbl, Icon]) => (
              <button key={k} onClick={() => setTab(k)}
                className={`px-3 py-1.5 flex items-center gap-1.5 transition ${tab === k ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`}>
                <Icon size={14} /> {lbl}
              </button>
            ))}
          </div>
          {(tab === '2d' || tab === '3d') && (
            <button onClick={() => setFullscreen(f => !f)} title="To'liq ekran"
              className="text-sm px-3 py-1.5 rounded-lg border bg-white text-slate-600 border-slate-200 hover:bg-slate-50 flex items-center gap-1.5">
              {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
          )}
          {tab === '2d' && (
            <button onClick={() => { setEditMode(e => !e); setSelCode(null); setPasteMode(false) }}
              className={`text-sm px-3 py-1.5 rounded-lg border flex items-center gap-1.5 transition ${editMode ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'}`}>
              <Pencil size={14} /> {editMode ? 'Tahrir: ON' : 'Tahrirlash'}
            </button>
          )}
          {editMode && tab === '2d' && !combined && (
            <button onClick={() => setGenOpen(true)}
              className="text-sm px-3 py-1.5 rounded-lg bg-blue-600 text-white flex items-center gap-1.5 hover:bg-blue-700">
              <Wand2 size={14} /> Rack qo'shish
            </button>
          )}
          {pasteMode && (
            <button onClick={() => { setPasteMode(false); setClipboard(null) }}
              className="text-sm px-3 py-1.5 rounded-lg border border-red-200 text-red-600 bg-red-50 hover:bg-red-100">
              Joylashni bekor
            </button>
          )}
          <select className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm bg-white"
            value={whId || (whList[0]?.id ?? '')} onChange={e => { setWhId(e.target.value); setSelCode(null) }}>
            {whList.map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
            {whList.length > 1 && <option value={COMBINED}>🏭 Hammasi ({whList.length} sklad)</option>}
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="flex flex-wrap gap-3 items-center text-sm">
        {[['Jami', stats.total, '#64748b'], ['Band', stats.occ, '#16a34a'], ['Qisman', stats.part, '#d97706'],
          ['Blok', stats.blk, '#dc2626'], ["Bo'sh", stats.free, '#94a3b8'], ['Stellaj', stats.cells, '#3b82f6'],
          ['Bron', (reservations as any[]).length, '#7c3aed']].map(([l, v, c]) => (
          <div key={l as string} className="px-3 py-1.5 rounded-lg border bg-white shadow-sm flex items-baseline gap-1.5">
            <span className="font-bold" style={{ color: c as string }}>{v as any}</span>
            <span className="text-xs text-slate-400">{l}</span>
          </div>
        ))}
      </div>

      {isLoading && <div className="py-20 text-center text-slate-400 text-sm"><Layers size={32} className="mx-auto mb-3 opacity-30" /> Yuklanmoqda…</div>}

      {/* ── 2D Tab ── */}
      {!isLoading && tab === '2d' && (
        <div className={`flex gap-4 ${wrapCls}`}>
          {fullscreen && (
            <button onClick={() => setFullscreen(false)} className="absolute top-3 right-3 z-10 bg-white border rounded-lg p-2 shadow">
              <Minimize2 size={16} />
            </button>
          )}
          <div className="flex-1 overflow-auto rounded-xl border border-slate-200 bg-slate-50"
               style={{ cursor: pasteMode ? 'copy' : 'default' }}>
            <svg ref={svgRef} width={SVG_W} height={SVG_H} style={{ display: 'block', minWidth: SVG_W }}
                 onPointerMove={onSvgPointerMove} onPointerUp={onSvgPointerUp}
                 onClick={onCanvasClick as any}>
              {Array.from({ length: Math.floor(bounds.maxX / 6) + 1 }, (_, i) => (
                <line key={i} x1={PAD + m(i * 6)} y1={PAD - 6} x2={PAD + m(i * 6)} y2={SVG_H - PAD}
                  stroke="#fca5a5" strokeWidth={0.7} strokeDasharray="4 4" opacity={0.4} />
              ))}
              {/* warehouse band labels (combined) */}
              {combined && [...new Map(cells.map(c => [c.wid, c])).values()].map(c => (
                <text key={c.wid} x={PAD + m(c.ox)} y={14} fontSize={12} fontWeight={700} fill="#475569">{c.wname}</text>
              ))}
              {cells.map(cell => {
                const key = `${cell.wid}:${cell.code}`
                const dragging = drag?.key === key
                const useX = dragging ? drag!.x : cell.x
                const useY = dragging ? drag!.y : cell.y
                const cx = PAD + m(useX + cell.ox), cy = PAD + m(useY)
                let occ = 0
                cell.slots.forEach(s => { if (s.status === 'occupied') occ++ })
                const isSel = key === selCode
                const isReserved = cell.slots.some(s => reservedLocIds.has(s.id))
                // ── Grid: etaj (tier) × joy (position). Tier 1 = tepada. ──
                const maxPos = cell.slots.reduce((mx, s) => Math.max(mx, s.position ?? 1), 1)
                const maxTier = cell.slots.reduce((mx, s) => Math.max(mx, s.tier ?? 1), 1)
                const cols = maxPos, rows = maxTier
                const SW = 15, SH = 13, GAP = 2, PADIN = 4, LABEL = 11
                const boxW = cols * SW + (cols - 1) * GAP + PADIN * 2
                const boxH = rows * SH + (rows - 1) * GAP + PADIN * 2 + LABEL
                return (
                  <g key={key} style={{ cursor: editMode ? 'move' : 'pointer' }}
                    onPointerDown={(e) => onCellPointerDown(e, cell)}
                    onClick={(e) => { e.stopPropagation(); if (!pasteMode) setSelCode(key) }}>
                    <rect x={cx} y={cy} width={boxW} height={boxH} rx={3}
                      fill="#f8fafc" stroke={isSel ? '#2563eb' : isReserved ? '#7c3aed' : '#cbd5e1'}
                      strokeWidth={isSel ? 2.5 : isReserved ? 2 : 1}
                      strokeDasharray={isReserved && !isSel ? '4 2' : undefined} />
                    {cell.slots.map((s) => {
                      const r = maxTier - (s.tier ?? 1), cc = (s.position ?? 1) - 1   // tier 1 PASTDA (5 6 yuqorida)
                      const sx = cx + PADIN + cc * (SW + GAP)
                      const sy = cy + PADIN + r * (SH + GAP)
                      return (
                        <g key={s.id}>
                          <rect x={sx} y={sy} width={SW} height={SH} rx={2}
                            fill={STATUS_FILL[s.status]} stroke={STATUS_BORDER[s.status]} strokeWidth={0.5}
                            onClick={(e) => { if (editMode && !pasteMode) { e.stopPropagation(); setSelCode(key); cycleSlot(s) } }}>
                            <title>{s.code}</title>
                          </rect>
                          <text x={sx + SW / 2} y={sy + SH / 2 + 2.5} textAnchor="middle" fontSize={6} fill="#475569" pointerEvents="none">
                            {(s.code.split('-').pop() || '')}
                          </text>
                        </g>
                      )
                    })}
                    {isReserved && <circle cx={cx + boxW - 5} cy={cy + 5} r={3} fill="#7c3aed" />}
                    <text x={cx + boxW / 2} y={cy + boxH - 2} textAnchor="middle" fontSize={7.5} fontWeight={600} fill="#334155">{cell.code}</text>
                  </g>
                )
              })}
            </svg>
          </div>

          {/* Side panel: edit (edit mode) OR inspect (view mode) */}
          {editMode && selCell && (
            <EditPanel key={selCell.wid + selCell.code} cell={selCell}
              onCopyCell={() => copyCell(selCell)} onCopyRack={() => copyRack(selCell)}
              onClose={() => setSelCode(null)} onSaved={reload} />
          )}
          {editMode && !selCell && (
            <div className="w-72 shrink-0 bg-white rounded-xl border border-slate-200 p-4 text-sm text-slate-400 self-start">
              <Move size={20} className="mb-2 opacity-40" />
              Katakni <b>sudrab</b> ko'chiring. Slot ustiga bossangiz — holati o'zgaradi. Tanlangan katakni <b>nusxalab</b> boshqa joyga joylashingiz mumkin.
            </div>
          )}
          {!editMode && selCell && (
            <CellInspector key={selCell.wid + selCell.code} cell={selCell} onClose={() => setSelCode(null)} />
          )}
        </div>
      )}

      {/* ── 3D Tab ── */}
      {!isLoading && tab === '3d' && (
        <div className={`bg-white rounded-xl shadow-sm p-3 ${wrapCls}`}>
          {fullscreen && (
            <button onClick={() => setFullscreen(false)} className="absolute top-5 right-5 z-10 bg-white border rounded-lg p-2 shadow">
              <Minimize2 size={16} />
            </button>
          )}
          {combined ? (
            <div className="grid lg:grid-cols-2 gap-3">
              {whList.map((w: any) => (
                <Suspense key={w.id} fallback={<div className="py-16 text-center text-slate-400 text-sm">3D yuklanmoqda…</div>}>
                  <div><div className="text-sm font-semibold text-slate-600 mb-1">{w.name}</div>
                    <Warehouse3D warehouseId={w.id} /></div>
                </Suspense>
              ))}
            </div>
          ) : wid && (
            <Suspense fallback={<div className="py-16 text-center text-slate-400 text-sm">3D yuklanmoqda…</div>}>
              <Warehouse3D warehouseId={wid} />
            </Suspense>
          )}
        </div>
      )}

      {/* ── Ro'yxat Tab ── */}
      {!isLoading && tab === 'list' && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-auto max-h-[70vh]">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 sticky top-0">
              <tr className="text-left text-slate-500">
                {['Sklad', 'Kod', 'Qator', 'Stellaj', 'Yacheyka', 'Holat'].map(h =>
                  <th key={h} className="px-3 py-2 font-medium">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {(locations as Loc[]).map(l => (
                <tr key={l._wid + l.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-1.5 text-slate-400 text-xs">{l._wname}</td>
                  <td className="px-3 py-1.5 font-medium font-mono">{l.code}</td>
                  <td className="px-3 py-1.5">{l.row ?? l.rack_group ?? '—'}</td>
                  <td className="px-3 py-1.5">{l.rack ?? '—'}</td>
                  <td className="px-3 py-1.5">{l.position ?? '—'}</td>
                  <td className="px-3 py-1.5">
                    <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: STATUS_FILL[l.status] + '33', color: STATUS_BORDER[l.status] }}>
                      {STATUS_LABEL[l.status]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {genOpen && (
        <RackGenModal wid={wid} zones={zones as any[]}
          onClose={() => setGenOpen(false)} onDone={() => { setGenOpen(false); reload() }} />
      )}
    </div>
  )
}

// ─── Cell inspector (view mode) — Asl Belgisi kod daraxti + qoldiq + bron ────
function CellInspector({ cell, onClose }: { cell: Cell; onClose: () => void }) {
  // Rack ichidagi yacheykalar (etaj/joy bo'yicha tartiblab). Default — band bo'lgani,
  // aks holda birinchisi. Foydalanuvchi har yacheykani tanlab ko'ra oladi.
  const orderedSlots = [...cell.slots].sort((a, b) =>
    (a.tier ?? 0) - (b.tier ?? 0) || (a.position ?? 0) - (b.position ?? 0) || a.code.localeCompare(b.code))
  const firstOcc = orderedSlots.find(s => s.status === 'occupied') ?? orderedSlots[0]
  const [selId, setSelId] = useState<string | undefined>(firstOcc?.id)
  const locId = selId ?? orderedSlots[0]?.id
  const [fetchingTree, setFetchingTree] = useState(false)
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['loc-contents', cell.wid, cell.code, locId],
    queryFn: () => getLocationContents(locId),
    enabled: !!locId, retry: false,
  })
  // GTIN bo'yicha mahsulot kartochkasi (kod daraxti yoki qoldiqdan GTIN)
  const gtin: string | null = data?.code_tree?.[0]?.gtin || data?.stock?.[0]?.gtin || null
  const { data: prodCard } = useQuery({
    queryKey: ['prod-card', gtin],
    queryFn: () => getProductByGtin(gtin as string),
    enabled: !!gtin, retry: false,
  })
  // Asl Belgisi mahsulot-reyestri kartochkasi (rasm/status/qadoq)
  const { data: abCard } = useQuery({
    queryKey: ['ab-card', gtin],
    queryFn: () => getAslBelgisiProductCard(gtin as string),
    enabled: !!gtin, retry: false,
  })

  const loadTree = async () => {
    setFetchingTree(true)
    try {
      const r = await fetchLocationCodeTree(locId)
      toast.success(`Daraxt yuklandi: +${r.created} kod (${r.api_calls} so'rov)`)
      await refetch()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Asl Belgisi\'dan yuklab bo\'lmadi')
    } finally { setFetchingTree(false) }
  }
  const selCode = orderedSlots.find(s => s.id === locId)?.code ?? '—'
  const codeCount = (function count(nodes: any[]): number {
    return (nodes || []).reduce((n, x) => n + 1 + count(x.children || []), 0)
  })(data?.code_tree || [])
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
          <div>
            <h3 className="font-semibold text-slate-800 text-base flex items-center gap-2">
              <Boxes size={18} className="text-blue-500" /> {cell.code}
            </h3>
            <div className="text-xs text-slate-400">{cell.wname} · {cell.slots.length} yacheyka · Tanlangan: <b className="font-mono text-slate-600">{selCode}</b></div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={20} /></button>
        </div>

        {/* Yacheyka chiplari */}
        <div className="px-5 py-2 border-b border-slate-100 flex flex-wrap gap-1">
          {orderedSlots.map(s => {
            const occ = s.status === 'occupied'; const sel = s.id === locId
            return (
              <button key={s.id} onClick={() => setSelId(s.id)} title={`${s.code}${occ ? ' · band' : " · bo'sh"}`}
                className={`text-xs font-mono rounded-md px-2.5 py-1 border transition ${
                  sel ? 'border-blue-500 bg-blue-500/10 text-blue-700 font-semibold'
                  : occ ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                  : 'border-slate-200 text-slate-500 hover:bg-slate-50'}`}>
                {s.code.split('-').pop()}{occ ? ' ●' : ''}
              </button>
            )
          })}
        </div>

        <div className="flex-1 overflow-auto grid md:grid-cols-2 gap-0">
          {/* CHAP: mahsulot kartochkasi + qoldiq + bron */}
          <div className="p-5 space-y-4 border-r border-slate-100">
            {isLoading && <div className="text-sm text-slate-400 py-4">Yuklanmoqda…</div>}
            {isError && <div className="text-xs text-amber-600 bg-amber-50 rounded-lg p-2">Ma'lumot yuklanmadi.</div>}

            {/* Mahsulot kartochkasi (GTIN bo'yicha) */}
            {(prodCard || gtin) && (
              <div className="rounded-xl border border-slate-200 overflow-hidden">
                <div className="px-3 py-1.5 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wide">Mahsulot kartochkasi</div>
                <div className="p-3 space-y-1.5">
                  <div className="font-semibold text-slate-800 text-sm">{nameOf(prodCard?.name) !== '—' ? nameOf(prodCard?.name) : nameOf(data?.stock?.[0]?.product_name)}</div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                    <Info k="GTIN" v={gtin} mono />
                    <Info k="Smartup kod" v={prodCard?.smartup_product_code} mono />
                    <Info k="O'lchov" v={prodCard?.uom} />
                    <Info k="Box ichida" v={prodCard?.units_per_box} />
                    <Info k="Kategoriya" v={prodCard?.category} />
                    <Info k="ABC" v={prodCard?.abc_class} />
                  </div>
                </div>
              </div>
            )}

            {/* Asl Belgisi mahsulot-reyestr kartochkasi */}
            {abCard?.found && (
              <div className="rounded-xl border border-emerald-200 overflow-hidden">
                <div className="px-3 py-1.5 bg-emerald-50 text-[11px] font-bold text-emerald-700 uppercase tracking-wide flex items-center justify-between">
                  <span>Asl Belgisi reyestri</span>
                  {abCard.status && <span className="normal-case font-semibold text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-600 text-white">{nameOf(abCard.status)}</span>}
                </div>
                <div className="p-3 space-y-2">
                  {abCard.image && (
                    <img src={abCard.image} alt="mahsulot" className="w-full max-h-40 object-contain rounded-lg bg-slate-50 border border-slate-100" />
                  )}
                  <div className="font-semibold text-slate-800 text-sm">{nameOf(abCard.product_name)}</div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                    <Info k="Qadoq turi" v={nameOf(abCard.package_type)} />
                    <Info k="Kategoriya" v={abCard.product_category} />
                    <Info k="TNVED" v={abCard.tnved} mono />
                    <Info k="Ishlab chiqaruvchi" v={abCard.producer} />
                    <Info k="INN" v={abCard.inn} mono />
                    <Info k="Mahsulot guruhi" v={abCard.product_group} />
                  </div>
                </div>
              </div>
            )}

            {/* Qoldiq */}
            <div>
              <div className="text-xs font-semibold text-slate-500 mb-1">Qoldiq</div>
              {data?.stock?.length ? data.stock.map((s: any, i: number) => (
                <div key={i} className="text-xs bg-slate-50 rounded-lg px-2.5 py-2 mb-1">
                  <div className="font-medium text-slate-700">{nameOf(s.product_name)}</div>
                  <div className="text-slate-500">{s.qty} dona · {STATUS_LABEL[s.status] ?? s.status}
                    {s.batch ? ` · partiya ${s.batch}` : ''}{s.expiry_date ? ` · muddat ${s.expiry_date}` : ''}{s.pallet_open ? ' · ochiq pallet' : ''}</div>
                </div>
              )) : <div className="text-xs text-slate-400">Bo'sh</div>}
            </div>

            {/* Bron */}
            {data?.reservations?.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-violet-600 mb-1 flex items-center gap-1"><Clock size={12} /> Bron</div>
                {data.reservations.map((r: any) => (
                  <div key={r.id} className="text-xs bg-violet-50 rounded-lg px-2 py-1.5 mb-1 font-mono break-all">{r.code} · {r.qty} box{r.manual ? ' · qo\'lda' : ''}</div>
                ))}
              </div>
            )}
          </div>

          {/* O'NG: to'liq kod daraxti */}
          <div className="p-5 space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-xs font-semibold text-slate-500">Kodlar daraxti (Asl Belgisi) {codeCount > 0 && <span className="text-slate-400">· {codeCount} kod</span>}</div>
              {(data?.stock?.length > 0 || data?.code_tree?.length > 0 || data?.reservations?.length > 0) && (
                <button onClick={loadTree} disabled={fetchingTree}
                  className="text-xs flex items-center gap-1 text-blue-600 hover:text-blue-700 disabled:opacity-50"
                  title="Kod daraxtini Asl Belgisi'dan yuklash (tepa+past) + to'liq maydonlar">
                  <Download size={12} className={fetchingTree ? 'animate-pulse' : ''} />
                  {fetchingTree ? 'Yuklanmoqda…' : 'Yuklash'}
                </button>
              )}
            </div>
            {data?.code_tree?.length ? data.code_tree.map((n: any) => <CodeNode key={n.code} node={n} depth={0} />)
              : <div className="text-xs text-slate-400">Kod biriktirilmagan — kod qo'yilgach "Yuklash" bilan daraxtni torting.</div>}
          </div>
        </div>
      </div>
    </div>
  )
}

function CodeNode({ node, depth }: { node: any; depth: number }) {
  const [open, setOpen] = useState(depth < 1)
  const has = node.children?.length > 0
  return (
    <div style={{ marginLeft: depth * 10 }}>
      <div className="text-[11px] font-mono py-0.5 flex items-center gap-1 cursor-pointer hover:bg-slate-50 rounded"
        onClick={() => has && setOpen(o => !o)}>
        {has ? <span className="text-slate-400">{open ? '▾' : '▸'}</span> : <span className="w-2.5 inline-block" />}
        <span className="px-1 rounded bg-slate-100 text-slate-500">{node.package_type}</span>
        <span className="text-slate-700 break-all">{node.code.length > 24 ? node.code.slice(0, 24) + '…' : node.code}</span>
      </div>
      {/* 9.2 to'liq ma'lumot — GTIN / status / i.ch. / muddat / partiya */}
      {(node.gtin || node.status || node.production_date || node.expiry_date || node.batch_number) && (
        <div className="text-[10px] text-slate-400 pl-4 flex flex-wrap gap-x-2">
          {node.gtin && <span>GTIN {node.gtin}</span>}
          {node.status && <span className="text-slate-500">{node.status}</span>}
          {node.production_date && <span>i.ch. {String(node.production_date).slice(0, 10)}</span>}
          {node.expiry_date && <span className="text-amber-600">muddat {String(node.expiry_date).slice(0, 10)}</span>}
          {node.batch_number && <span>partiya {node.batch_number}</span>}
        </div>
      )}
      {open && has && node.children.map((c: any) => <CodeNode key={c.code} node={c} depth={depth + 1} />)}
    </div>
  )
}

function nameOf(n: any): string {
  if (!n) return '—'
  if (typeof n === 'string') return n
  return n.uz || n.ru || n.en || '—'
}

function Info({ k, v, mono }: { k: string; v: any; mono?: boolean }) {
  return (
    <div className="min-w-0">
      <div className="text-[10px] text-slate-400 leading-3">{k}</div>
      <div className={`text-slate-700 truncate ${mono ? 'font-mono text-[11px]' : ''}`}>{v != null && v !== '' ? String(v) : '—'}</div>
    </div>
  )
}

// ─── Edit panel ──────────────────────────────────────────────────────────────
function EditPanel({ cell, onClose, onSaved, onCopyCell, onCopyRack }: {
  cell: Cell; onClose: () => void; onSaved: () => void; onCopyCell: () => void; onCopyRack: () => void
}) {
  const [code, setCode] = useState(cell.code)
  const initT = cell.slots.reduce((mx, s) => Math.max(mx, s.tier ?? 1), 1)
  const initP = cell.slots.reduce((mx, s) => Math.max(mx, s.position ?? 1), 1)
  const [tiers, setTiers] = useState(String(initT))
  const [positions, setPositions] = useState(String(initP))
  const [busy, setBusy] = useState(false)

  const oldBase = cell.rack_group || cell.code
  const save = async () => {
    const T = Math.max(1, Number(tiers) || 1)
    const P = Math.max(1, Number(positions) || 1)
    const base = code.trim()
    if (!base) { toast.error('Stellaj nomini kiriting'); return }
    setBusy(true)
    try {
      // Stellaj yacheykalarini idempotent o'rnatamiz: {base}-1 … {base}-{T×P} (etaj×joy grid)
      await setRackCells(cell.wid, { zone_id: cell.zone_id, base_code: base, tiers: T, positions: P })
      // Stellaj qayta nomlangan bo'lsa — eski (boshqa nomli) bo'sh yacheykalarni o'chiramiz
      if (base !== oldBase) {
        for (const s of cell.slots) {
          if (String(s.status).toLowerCase() === 'empty') await deleteLocationById(cell.wid, s.id)
        }
      }
      toast.success('Saqlandi'); onSaved()
    } catch (e: any) {
      const d = e?.response?.data?.detail
      toast.error(typeof d === 'string' ? d : 'Bu nom band yoki xato')
    } finally { setBusy(false) }
  }

  // Bitta yacheyka nomini o'zgartirish
  const renameSlot = async (s: Loc, newCode: string) => {
    const c = newCode.trim()
    if (!c || c === s.code) return
    try {
      await updateLocationById(cell.wid, s.id, { code: c, barcode: c })
      toast.success('Yacheyka nomi o\'zgartirildi'); onSaved()
    } catch (e: any) {
      const d = e?.response?.data?.detail
      toast.error(typeof d === 'string' ? d : 'Bu kod band')
    }
  }
  const removeCell = async () => {
    if (!confirm(`"${cell.code}" katagini (${cell.slots.length} slot) o'chirasizmi?`)) return
    setBusy(true)
    try {
      for (const s of cell.slots) await deleteLocationById(cell.wid, s.id)
      toast.success('O\'chirildi'); onClose(); onSaved()
    } catch { toast.error('O\'chirishda xatolik') } finally { setBusy(false) }
  }

  return (
    <div className="w-72 shrink-0 bg-white rounded-xl border border-slate-200 p-4 space-y-3 self-start">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-700 text-sm">Stellaj: {cell.code}</h3>
        <button onClick={onClose}><X size={16} className="text-slate-400" /></button>
      </div>
      <div className="text-xs text-slate-400">{cell.wname} · {cell.slots.length} yacheyka</div>

      <div className="flex gap-2">
        <button onClick={onCopyCell} className="flex-1 text-xs border border-slate-200 rounded-lg py-1.5 hover:bg-slate-50 flex items-center justify-center gap-1">
          <Copy size={13} /> Katak
        </button>
        <button onClick={onCopyRack} className="flex-1 text-xs border border-slate-200 rounded-lg py-1.5 hover:bg-slate-50 flex items-center justify-center gap-1">
          <ClipboardPaste size={13} /> Stellaj
        </button>
      </div>

      <Field label="Stellaj nomi"><input className="inp font-mono" value={code} onChange={e => setCode(e.target.value)} /></Field>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Etaj (qator)"><input className="inp" type="number" min={1} value={tiers} onChange={e => setTiers(e.target.value)} /></Field>
        <Field label="Joy (har etajda)"><input className="inp" type="number" min={1} value={positions} onChange={e => setPositions(e.target.value)} /></Field>
      </div>
      <p className="text-[11px] text-slate-400">
        {tiers}×{positions} = <b>{(Number(tiers) || 1) * (Number(positions) || 1)}</b> yacheyka:
        <span className="font-mono"> {code}-1 … {code}-{(Number(tiers) || 1) * (Number(positions) || 1)}</span> (1-etaj tepada).
      </p>

      <div className="flex gap-2 pt-1">
        <button onClick={save} disabled={busy} className="flex-1 bg-blue-600 text-white text-sm py-2 rounded-lg hover:bg-blue-700 flex items-center justify-center gap-1.5 disabled:opacity-50">
          <Save size={14} /> Saqlash
        </button>
        <button onClick={removeCell} disabled={busy} className="bg-red-50 text-red-600 border border-red-200 px-3 rounded-lg hover:bg-red-100">
          <Trash2 size={14} />
        </button>
      </div>

      {/* Har bir yacheyka nomi (alohida o'zgartirish) */}
      {cell.slots.length > 0 && (
        <details className="border border-slate-100 rounded-lg p-2">
          <summary className="text-xs text-slate-500 cursor-pointer select-none">Yacheyka nomlari ({cell.slots.length})</summary>
          <div className="mt-2 space-y-1 max-h-52 overflow-auto">
            {[...cell.slots].sort((a, b) => (a.position ?? 0) - (b.position ?? 0)).map(s => (
              <input key={s.id} className="inp font-mono text-xs" defaultValue={s.code}
                onBlur={e => renameSlot(s, e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }} />
            ))}
          </div>
        </details>
      )}
      <style>{`.inp{width:100%;border:1px solid #e2e8f0;border-radius:8px;padding:5px 8px;font-size:13px}.inp:focus{outline:none;border-color:#3b82f6}`}</style>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="text-xs text-slate-500">{label}</span>{children}</label>
}

// ─── Rack generator modal ────────────────────────────────────────────────────
function RackGenModal({ wid, zones, onClose, onDone }: { wid: string; zones: any[]; onClose: () => void; onDone: () => void }) {
  const ROWS = ['A', 'B', 'C', 'D', 'E', 'F']
  const [f, setF] = useState({
    zone_id: zones[0]?.id ?? '', row: 'A', racks: 1, tiers: 3, positions: 2,
  })
  const [busy, setBusy] = useState(false)
  const set = (k: string, v: any) => setF(s => ({ ...s, [k]: v }))
  const run = async () => {
    if (!f.zone_id) { toast.error('Zona tanlang'); return }
    setBusy(true)
    try {
      // Qator A-F → stellaj A-01..A-{racks}; har stellaj: etaj×joy grid → A-01-1..N
      const r = await generateRack(wid, {
        zone_id: f.zone_id,
        rack_group: f.row,
        code_prefix: f.row,
        row: f.row,
        cols: +f.racks,        // stellajlar soni
        tiers: +f.tiers,       // etaj
        positions: +f.positions, // har etajda joy
        x: 0, y: 0, cell_w: 1.95,
      })
      toast.success(`${r.length} yacheyka yaratildi`); onDone()
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? 'Xatolik') } finally { setBusy(false) }
  }
  const perRack = (+f.tiers || 1) * (+f.positions || 1)
  const total = (+f.racks || 0) * perRack
  const sample = `${f.row}-01-1 … ${f.row}-${String(+f.racks || 1).padStart(2, '0')}-${perRack}`
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-xl p-5 w-[420px] space-y-3" onClick={e => e.stopPropagation()}>
        <h3 className="font-semibold text-slate-800 flex items-center gap-2"><Wand2 size={18} className="text-blue-500" /> Stellaj generatori</h3>
        <label className="block"><span className="text-xs text-slate-500">Zona</span>
          <select className="inp2" value={f.zone_id} onChange={e => set('zone_id', e.target.value)}>
            {zones.map(z => <option key={z.id} value={z.id}>{z.name}</option>)}
          </select></label>
        <div className="grid grid-cols-2 gap-2">
          <L label="Qator"><select className="inp2" value={f.row} onChange={e => set('row', e.target.value)}>
            {ROWS.map(r => <option key={r} value={r}>{r}</option>)}
          </select></L>
          <L label="Stellajlar soni"><input className="inp2" type="number" min={1} value={f.racks} onChange={e => set('racks', e.target.value)} /></L>
          <L label="Etaj (qator)"><input className="inp2" type="number" min={1} value={f.tiers} onChange={e => set('tiers', e.target.value)} /></L>
          <L label="Joy (har etajda)"><input className="inp2" type="number" min={1} value={f.positions} onChange={e => set('positions', e.target.value)} /></L>
        </div>
        <div className="text-xs text-slate-500 bg-slate-50 rounded-lg p-2">
          Har stellaj <b>{f.tiers}×{f.positions} = {perRack}</b> yacheyka · Kodlar: <b className="font-mono">{sample}</b> · jami <b>{total}</b>
        </div>
        <div className="flex gap-2">
          <button onClick={run} disabled={busy} className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-1.5">
            <Plus size={16} /> {busy ? 'Yaratilmoqda…' : 'Yaratish'}
          </button>
          <button onClick={onClose} className="px-4 border border-slate-200 rounded-lg text-slate-600">Bekor</button>
        </div>
        <style>{`.inp2{width:100%;border:1px solid #e2e8f0;border-radius:8px;padding:6px 8px;font-size:13px;margin-top:2px}.inp2:focus{outline:none;border-color:#3b82f6}`}</style>
      </div>
    </div>
  )
}
function L({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="text-[11px] text-slate-500">{label}</span>{children}</label>
}
