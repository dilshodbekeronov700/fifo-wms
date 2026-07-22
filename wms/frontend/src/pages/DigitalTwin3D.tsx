/**
 * Digital Twin — 2D Layout Map + 3D toggle
 *
 * 2D: PDF rejaga mos rack segmentlari (warehouseLayout.ts) SVG'da chiziladi.
 *     Har katak = 2 pallet × 3 etaj = 6 joy.
 * 3D: Warehouse3D (three.js) — xuddi shu layoutdan.
 */

import { useMemo, useState, lazy, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Box, Layers, LayoutGrid } from 'lucide-react'
import { getWarehouses, getAllLocations } from '../lib/api'
import {
  BUILDING, CELL_W, ROW_D, TIERS, POSITIONS,
  RACK_SEGMENTS, CONTEXT_ZONES, enumerateCells, totals, demoStatus,
  STATUS_FILL, STATUS_BORDER, STATUS_LABEL,
} from '../lib/warehouseLayout'

const Warehouse3D = lazy(() => import('./Warehouse3D'))

// SVG masshtab
const PAD = 26
const SVG_INNER_W = 1180
const SCALE = SVG_INNER_W / BUILDING.w           // px / m
const SVG_W = BUILDING.w * SCALE + PAD * 2
const SVG_H = BUILDING.h * SCALE + PAD * 2.4

const m = (v: number) => v * SCALE

function StatPill({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div className="flex flex-col items-center px-4 py-2 rounded-xl border bg-white shadow-sm min-w-[80px]">
      <span className="text-lg font-bold" style={{ color }}>{value}</span>
      <span className="text-xs text-slate-400 mt-0.5">{label}</span>
    </div>
  )
}

// ─── 2D Layout (SVG) ─────────────────────────────────────────────────────────
function LayoutMap({ locations }: { locations: any[] }) {
  // real location indeksi: cellId -> {tier,pos -> status}
  const locMap = useMemo(() => {
    const map: Record<string, string> = {}
    for (const l of locations) {
      if (l.code && l.tier != null && l.position != null) {
        map[`${l.code}:${l.tier}:${l.position}`] = l.status
      }
    }
    return map
  }, [locations])

  const isDemo = locations.length === 0 || Object.keys(locMap).length === 0
  const cells = useMemo(() => enumerateCells(), [])
  const { cells: cellCount, spots } = totals()

  // statistika
  const stats = useMemo(() => {
    let occ = 0, part = 0, blk = 0
    for (const cell of cells) {
      for (let t = 1; t <= TIERS; t++)
        for (let p = 1; p <= POSITIONS; p++) {
          const s = isDemo
            ? demoStatus(cell.segId, cell.rIdx, cell.col, t, p)
            : (locMap[`${cell.cellId}:${t}:${p}`] ?? 'empty')
          if (s === 'occupied') occ++
          else if (s === 'partial') part++
          else if (s === 'blocked') blk++
        }
    }
    return { total: spots, occ, part, blk, free: spots - occ - part - blk }
  }, [cells, isDemo, locMap, spots])

  // mini-slot o'lchami
  const cw = m(CELL_W) - 3
  const ch = m(ROW_D) - 3
  const slotW = (cw - 6) / POSITIONS
  const slotH = (ch - 8) / TIERS

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="flex flex-wrap gap-3 items-center">
        <StatPill label="Jami joy" value={stats.total} color="#64748b" />
        <StatPill label="Band"     value={stats.occ}   color="#16a34a" />
        <StatPill label="Qisman"   value={stats.part}  color="#d97706" />
        <StatPill label="Bloklangan" value={stats.blk} color="#dc2626" />
        <StatPill label="Bo'sh"    value={stats.free}  color="#94a3b8" />
        <div className="ml-auto flex items-center gap-2 text-xs text-slate-400">
          {isDemo && (
            <span className="px-2 py-1 bg-amber-50 text-amber-600 border border-amber-200 rounded-full font-medium">
              Demo — real location yo'q
            </span>
          )}
          <span>{cellCount} katak · har katak 2 pallet × 3 etaj = 6 joy</span>
        </div>
      </div>

      {/* SVG layout */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-50">
        <svg width={SVG_W} height={SVG_H} style={{ display: 'block', minWidth: SVG_W }}>
          <defs>
            <marker id="arrowUp" markerWidth={8} markerHeight={8} refX={4} refY={2}
              orient="auto" markerUnits="strokeWidth">
              <path d="M0,6 L4,0 L8,6 Z" fill="#f59e0b" />
            </marker>
          </defs>
          {/* Bino konturi */}
          <rect x={PAD} y={PAD} width={m(BUILDING.w)} height={m(BUILDING.h)}
            rx={4} fill="#ffffff" stroke="#cbd5e1" strokeWidth={2} />

          {/* 6m span chiziqlari (bino ustunlari) */}
          {Array.from({ length: Math.floor(BUILDING.w / 6) + 1 }, (_, i) => {
            const x = PAD + m(i * 6)
            return (
              <g key={`span-${i}`}>
                <line x1={x} y1={PAD} x2={x} y2={PAD + m(BUILDING.h)}
                  stroke="#fca5a5" strokeWidth={0.8} strokeDasharray="4 4" opacity={0.5} />
                <circle cx={x} cy={PAD} r={3} fill="#ef4444" opacity={0.6} />
                <text x={x} y={PAD - 6} textAnchor="middle" fontSize={8} fill="#ef4444" opacity={0.7}>
                  {i * 6}m
                </text>
              </g>
            )
          })}

          {/* Kontekst zonalar (dok / ofis / ishlab chiqarish kirishi) */}
          {CONTEXT_ZONES.map(z => {
            if (z.kind === 'entry') {
              // Ishlab chiqarishdan kirish — pastdan yuqoriga sariq strelka
              const ax = PAD + m(z.x) + m(z.w) / 2
              const ay0 = PAD + m(z.y) + m(z.h)   // past (bino chekkasi)
              const ay1 = PAD + m(z.y) - m(1.2)    // yuqori (skladga)
              return (
                <g key={z.id}>
                  <line x1={ax} y1={ay0} x2={ax} y2={ay1}
                    stroke="#f59e0b" strokeWidth={3} markerEnd="url(#arrowUp)" />
                  <text x={ax + m(2.4)} y={ay0 - 4} textAnchor="start"
                    fontSize={9} fontWeight="600" fill="#d97706">{z.label}</text>
                </g>
              )
            }
            return (
              <g key={z.id}>
                <rect x={PAD + m(z.x)} y={PAD + m(z.y)} width={m(z.w)} height={m(z.h)}
                  rx={4}
                  fill={z.kind === 'dock' ? '#fff7ed' : '#f1f5f9'}
                  stroke={z.kind === 'dock' ? '#fed7aa' : '#e2e8f0'}
                  strokeWidth={1.5}
                  strokeDasharray={z.kind === 'dock' ? '6 4' : undefined} />
                <text x={PAD + m(z.x) + m(z.w) / 2} y={PAD + m(z.y) + (z.kind === 'office' ? m(z.h) / 2 : 16)}
                  textAnchor="middle" fontSize={11} fontWeight="600"
                  fill={z.kind === 'dock' ? '#ea580c' : '#64748b'}>
                  {z.label}
                </text>
              </g>
            )
          })}

          {/* Sklad GP yozuvi */}
          <text x={PAD + m(6)} y={PAD + m(2.2)} fontSize={20} fontStyle="italic"
            fontWeight="600" fill="#94a3b8" opacity={0.8}>Склад ГП</text>

          {/* Rack segmentlari */}
          {RACK_SEGMENTS.map(seg => {
            const segW = m(seg.cols * CELL_W)
            const segH = m(seg.deep * ROW_D)
            return (
              <g key={seg.id}>
                {/* segment foni */}
                <rect x={PAD + m(seg.x) - 2} y={PAD + m(seg.y) - 2}
                  width={segW + 2} height={segH + 2} rx={3}
                  fill="none" stroke="#bfdbfe" strokeWidth={1} />
                {/* qator yorlig'i (faqat chap chekka segmentida) */}
                {seg.label && (
                  <text x={PAD + m(seg.x) - 6} y={PAD + m(seg.y) + segH / 2 + 3}
                    textAnchor="end" fontSize={11} fontWeight="700" fill="#1d4ed8">
                    {seg.row}
                  </text>
                )}
              </g>
            )
          })}

          {/* Kataklar */}
          {cells.map(cell => {
            const cx = PAD + m(cell.x) + 1.5
            const cy = PAD + m(cell.y) + 1.5

            // katak slotlari
            let occCount = 0
            const slots: { t: number; p: number; s: string }[] = []
            for (let t = 1; t <= TIERS; t++)
              for (let p = 1; p <= POSITIONS; p++) {
                const s = isDemo
                  ? demoStatus(cell.segId, cell.rIdx, cell.col, t, p)
                  : (locMap[`${cell.cellId}:${t}:${p}`] ?? 'empty')
                if (s === 'occupied') occCount++
                slots.push({ t, p, s })
              }
            const ratio = occCount / (TIERS * POSITIONS)
            const cellBg = ratio === 0 ? '#f8fafc' : ratio <= 0.34 ? '#f0fdf4' : ratio <= 0.67 ? '#fefce8' : '#fef2f2'
            const cellBd = ratio === 0 ? '#e2e8f0' : ratio <= 0.34 ? '#bbf7d0' : ratio <= 0.67 ? '#fde68a' : '#fecaca'

            return (
              <g key={cell.segId + cell.rIdx + cell.col}>
                <rect x={cx} y={cy} width={cw} height={ch} rx={2.5}
                  fill={cellBg} stroke={cellBd} strokeWidth={1} />
                {/* mini slotlar: pastki etaj = pastda */}
                {slots.map(({ t, p, s }) => {
                  const sx = cx + 3 + (p - 1) * (slotW + 1.5)
                  const sy = cy + 4 + (TIERS - t) * (slotH + 1)
                  return (
                    <rect key={`${t}-${p}`} x={sx} y={sy} width={slotW} height={slotH - 0.5} rx={1.5}
                      fill={STATUS_FILL[s]} stroke={STATUS_BORDER[s]} strokeWidth={0.4} />
                  )
                })}
              </g>
            )
          })}

          {/* Markaziy vertikal yo'lak (chap va o'ng bloklar orasi) */}
          <line x1={PAD + m(22.9)} y1={PAD + m(3.7)} x2={PAD + m(22.9)} y2={PAD + m(11.2)}
            stroke="#22c55e" strokeWidth={1} strokeDasharray="5 4" opacity={0.5} />
          <text x={PAD + m(22.9)} y={PAD + m(2.9)} textAnchor="middle"
            fontSize={8} fill="#22c55e" fontStyle="italic">markaziy yo'lak</text>
        </svg>
      </div>

      {/* Legenda */}
      <div className="flex flex-wrap gap-4 text-xs text-slate-500">
        {Object.entries(STATUS_FILL).map(([s, c]) => (
          <span key={s} className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded-sm inline-block border" style={{ background: c, borderColor: STATUS_BORDER[s] }} />
            {STATUS_LABEL[s]}
          </span>
        ))}
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 border-t-2 border-dashed border-red-400" /> Bino ustuni (6m)
        </span>
      </div>
    </div>
  )
}

// ─── Asosiy sahifa ───────────────────────────────────────────────────────────
export default function DigitalTwin3D() {
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [whId, setWhId] = useState<string>('')
  const [mode, setMode] = useState<'2d' | '3d'>('2d')
  const wid = whId || (warehouses as any[])[0]?.id

  const { data: locations = [], isLoading } = useQuery({
    queryKey: ['all-locations', wid],
    queryFn: () => getAllLocations(wid),
    enabled: !!wid,
    retry: false,
  })

  return (
    <div className="p-4 lg:p-6 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Box size={20} className="text-blue-500" />
            Digital Twin
          </h1>
          <p className="text-slate-400 text-sm mt-0.5">
            Sklad GP xaritasi — {mode === '2d' ? '2D Layout' : '3D Ko\'rinish'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-slate-200 overflow-hidden text-sm">
            <button onClick={() => setMode('2d')}
              className={`px-3 py-1.5 flex items-center gap-1.5 transition ${mode === '2d' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`}>
              <LayoutGrid size={14} /> 2D Layout
            </button>
            <button onClick={() => setMode('3d')}
              className={`px-3 py-1.5 flex items-center gap-1.5 transition ${mode === '3d' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`}>
              <Box size={14} /> 3D
            </button>
          </div>
          <select className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-600 bg-white"
            value={wid ?? ''} onChange={e => setWhId(e.target.value)}>
            {(warehouses as any[]).map((wh: any) => (
              <option key={wh.id} value={wh.id}>{wh.name}</option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && (
        <div className="py-20 text-center text-slate-400 text-sm">
          <Layers size={32} className="mx-auto mb-3 opacity-30" /> Yuklanmoqda…
        </div>
      )}

      {!isLoading && mode === '2d' && wid && <LayoutMap locations={locations as any[]} />}

      {!isLoading && mode === '3d' && wid && (
        <div className="bg-white rounded-xl shadow-sm p-3">
          <Suspense fallback={<div className="py-16 text-center text-slate-400 text-sm">3D dvigatel yuklanmoqda…</div>}>
            <Warehouse3D warehouseId={wid} />
          </Suspense>
        </div>
      )}
    </div>
  )
}
