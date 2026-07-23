import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getWarehouses,
  getAllLocations,
  createPickTask,
  confirmShipment,
} from '../lib/api'
import {
  Route,
  Package,
  CheckCircle2,
  AlertTriangle,
  Layers,
  MapPin,
  Cloud,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader, Card, CardHeader, Button, Select, Badge, EmptyState } from '../components/ui'

interface RouteStop {
  sequence: number
  location_code: string
  product_id?: string
  product_code?: string
  product_name?: string
  take_qty: number
  marking_codes?: string[]
  is_partial_pallet?: boolean
  lot_number?: string
  production_date?: string
  expiry_date?: string
}

interface Issue {
  order_line_id: string
  kind: string
  detail: string
  requested?: number
  available?: number
  product_code?: string
  product_name?: string
  gtin?: string
}

interface PickTaskResult {
  document_id: string
  task_id?: string
  route?: RouteStop[]
  shortfall_lines?: string[]
  issues?: Issue[]
}

const ISSUE_META: Record<string, { label: string; tone: string }> = {
  unmapped_product: { label: 'Mapping yo\'q', tone: 'bg-slate-500/10 border-slate-400/40 text-slate-600' },
  unmapped_gtin: { label: 'Mapping yo\'q', tone: 'bg-slate-500/10 border-slate-400/40 text-slate-600' },
  over_pick: { label: 'Qoldiq yetarli emas', tone: 'bg-amber-500/10 border-amber-500/40 text-amber-700' },
  shortfall: { label: 'Yetishmovchilik', tone: 'bg-rose-500/10 border-rose-500/40 text-rose-700' },
}

export default function Shipment() {
  const qc = useQueryClient()
  const nav = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const dealParam = searchParams.get('deal')
  const whParam = searchParams.get('wh')

  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [whId, setWhId] = useState<string>('')
  const wid = whId || whParam || (warehouses as any[])[0]?.id
  const activeWh = (warehouses as any[]).find((w: any) => w.id === wid)

  const [createdTask, setCreatedTask] = useState<PickTaskResult | null>(null)
  const [failInfo, setFailInfo] = useState<{ message?: string; issues: Issue[] } | null>(null)
  const [activeDeal, setActiveDeal] = useState<string | null>(null)
  const builtFor = useRef<string | null>(null)

  // Barcha yacheykalar — xaritani chizish va marshrut koordinatalari uchun.
  const { data: locations = [] } = useQuery({
    queryKey: ['pick-locations', wid],
    queryFn: () => getAllLocations(wid),
    enabled: !!wid,
  })

  const pickMut = useMutation({
    mutationFn: (dealId: string) =>
      createPickTask({ warehouse_id: wid, smartup_deal_id: dealId }),
    onSuccess: (data: PickTaskResult) => {
      setFailInfo(null)
      setCreatedTask(data)
      const short = data.shortfall_lines?.length ?? 0
      if (short > 0) toast(`Marshrut tuzildi — ${short} qatorda yetishmovchilik`, { icon: '⚠️' })
      else toast.success('Pick marshruti tuzildi')
    },
    onError: (e: any) => {
      const d = e.response?.data?.detail
      // 422 "No pickable lines" — sababni (mapping yo'q / qoldiq yo'q) ko'rsatamiz
      if (d && typeof d === 'object' && Array.isArray(d.issues)) {
        setFailInfo({ message: d.message, issues: d.issues })
      } else {
        setFailInfo({ message: typeof d === 'string' ? d : 'Marshrut tuzishda xatolik', issues: [] })
      }
      toast.error(typeof d === 'string' ? d : d?.message ?? 'Marshrut tuzishda xatolik')
    },
  })

  const confirmMut = useMutation({
    mutationFn: (doc_id: string) => confirmShipment(doc_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['stock'] })
      qc.invalidateQueries({ queryKey: ['tasks'] })
      setCreatedTask(null)
      setActiveDeal(null)
      toast.success('Chiqim tasdiqlandi')
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Tasdiqlashda xatolik'),
  })

  // ?wh — Smartup sahifasidagi tanlangan skladni sinxronlaymiz.
  useEffect(() => { if (whParam) setWhId(whParam) }, [whParam])

  // ?deal — buyurtma bo'yicha marshrutni bir marta tuzamiz, so'ng URL'ni tozalaymiz.
  useEffect(() => {
    if (!dealParam || !wid || builtFor.current === dealParam) return
    builtFor.current = dealParam
    setActiveDeal(dealParam)
    setCreatedTask(null)
    setFailInfo(null)
    pickMut.mutate(dealParam)
    const next = new URLSearchParams(searchParams)
    next.delete('deal'); next.delete('wh')
    setSearchParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dealParam, wid])

  const route = createdTask?.route ?? []
  const issues = createdTask?.issues ?? []

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
      <PageHeader
        icon={<Route size={20} />}
        title="Pick marshruti"
        subtitle={activeDeal ? `Buyurtma ${activeDeal} · ${activeWh?.name ?? ''}` : 'Interaktiv terish marshruti — sklad xaritasi bo\'yicha optimal yo\'l'}
        actions={
          <Select value={wid ?? ''} onChange={e => setWhId(e.target.value)} className="w-auto min-w-40">
            {(warehouses as any[]).map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </Select>
        }
      />

      {/* Marshrut tuzilmadi — SABABINI ko'rsatamiz (mapping yo'q / qoldiq yetmayapti) */}
      {!createdTask && !pickMut.isPending && failInfo && (
        <Card className="space-y-3">
          <div className="flex items-center gap-2 text-rose-600">
            <AlertTriangle size={18} />
            <span className="font-semibold text-sm">Marshrut tuzilmadi{activeDeal ? ` — buyurtma ${activeDeal}` : ''}</span>
          </div>
          <p className="text-sm text-slate-500">
            {failInfo.issues.length > 0
              ? 'Buyurtmadagi hech bir qatorni terib bo\'lmadi. Sabab quyida — mahsulotni «Товары»da bog\'lang (Avto-bog\'lash) yoki qoldiqni to\'ldiring.'
              : (failInfo.message || 'Noma\'lum xatolik.')}
          </p>
          {failInfo.issues.map((iss, i) => {
            const m = ISSUE_META[iss.kind] ?? { label: iss.kind, tone: 'bg-slate-500/10 border-slate-400/40 text-slate-600' }
            const missing = (iss.requested != null && iss.available != null) ? iss.requested - iss.available : null
            return (
              <div key={i} className={`rounded-xl border p-2.5 text-xs ${m.tone}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold">{m.label}</span>
                  {missing != null && missing > 0 && <span className="font-bold">−{missing} yetishmaydi</span>}
                </div>
                <div className="mt-1 text-slate-700">
                  {iss.product_name || iss.product_code || iss.order_line_id}
                  {iss.product_code && iss.product_name && <span className="text-slate-400 font-mono"> · {iss.product_code}</span>}
                </div>
                {iss.gtin && <div className="text-[11px] font-mono text-slate-400">GTIN {iss.gtin}</div>}
                {(iss.requested != null || iss.available != null) && (
                  <div className="mt-0.5 text-slate-500">So'ralgan: <b>{iss.requested ?? '?'}</b> · Mavjud: <b>{iss.available ?? '?'}</b></div>
                )}
                <div className="mt-0.5 text-slate-400">{iss.detail}</div>
              </div>
            )
          })}
          <div className="flex gap-2">
            <Button variant="secondary" icon={<Cloud size={15} />} onClick={() => nav('/smartup')}>Buyurtmalar</Button>
            <Button variant="ghost" onClick={() => nav('/products')}>Товарlarga o'tish</Button>
          </div>
        </Card>
      )}

      {/* Marshrut hali yo'q — Smartup buyurtmalaridan boshlash */}
      {!createdTask && !pickMut.isPending && !failInfo && (
        <Card className="min-h-[320px] flex items-center justify-center">
          <div className="text-center max-w-md">
            <EmptyState
              icon={Route}
              title="Marshrut yo'q"
              description="Smartup (ERP) → Buyurtmalar bo'limida buyurtma yonidagi «Pick» tugmasini bosing — marshrut shu yerda interaktiv chiziladi."
            />
            <Button variant="secondary" icon={<Cloud size={15} />} className="mt-3" onClick={() => nav('/smartup')}>
              Buyurtmalarga o'tish
            </Button>
          </div>
        </Card>
      )}

      {pickMut.isPending && (
        <Card className="min-h-[200px] flex items-center justify-center">
          <p className="text-sm text-slate-500 flex items-center gap-2">
            <Route size={16} className="animate-pulse text-blue-500" /> Marshrut tuzilmoqda…
          </p>
        </Card>
      )}

      {createdTask && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-4 items-start">
          {/* CHAP: interaktiv xarita + yo'l */}
          <Card>
            <CardHeader icon={<MapPin size={16} className="text-blue-500" />} title="Sklad xaritasi — optimal yo'l"
              action={route.length > 0 ? <Badge tone="blue">{route.length} to'xtash</Badge> : undefined} />
            {route.length === 0 ? (
              <EmptyState icon={MapPin} title="To'xtash yo'q" description="Bu buyurtma uchun teriladigan qoldiq topilmadi." />
            ) : (
              <PickRouteMap locations={locations as any[]} route={route} />
            )}
          </Card>

          {/* O'NG: marshrut qadamlari + yetishmovchilik + tasdiqlash */}
          <div className="space-y-4">
            {/* Yetishmovchilik / mapping muammolari — batafsil */}
            {issues.length > 0 && (
              <Card padded={false} className="overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-200/60 flex items-center gap-2">
                  <AlertTriangle size={15} className="text-amber-500" />
                  <span className="font-semibold text-slate-700 text-sm">Diqqat ({issues.length})</span>
                </div>
                <div className="p-3 space-y-2">
                  {issues.map((iss, i) => {
                    const m = ISSUE_META[iss.kind] ?? { label: iss.kind, tone: 'bg-slate-500/10 border-slate-400/40 text-slate-600' }
                    const missing = (iss.requested != null && iss.available != null) ? iss.requested - iss.available : null
                    return (
                      <div key={i} className={`rounded-xl border p-2.5 text-xs ${m.tone}`}>
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold">{m.label}</span>
                          {missing != null && missing > 0 && <span className="font-bold">−{missing} yetishmaydi</span>}
                        </div>
                        <div className="mt-1 text-slate-700">
                          {iss.product_name || iss.product_code || iss.order_line_id}
                          {iss.product_code && iss.product_name && <span className="text-slate-400 font-mono"> · {iss.product_code}</span>}
                        </div>
                        {iss.gtin && <div className="text-[11px] font-mono text-slate-400">GTIN {iss.gtin}</div>}
                        {(iss.requested != null || iss.available != null) && (
                          <div className="mt-0.5 text-slate-500">
                            So'ralgan: <b>{iss.requested ?? '?'}</b> · Mavjud: <b>{iss.available ?? '?'}</b>
                          </div>
                        )}
                        {iss.detail && <div className="mt-0.5 text-slate-400">{iss.detail}</div>}
                      </div>
                    )
                  })}
                </div>
              </Card>
            )}

            {/* Marshrut qadamlari (mahsulot nomi bilan) */}
            <Card padded={false} className="overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-200/60 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Package size={15} className="text-green-500" />
                  <span className="font-semibold text-slate-700 text-sm">Terish qadamlari</span>
                </div>
                {createdTask.document_id && (
                  <Button variant="success" size="sm" icon={<CheckCircle2 size={14} />}
                    loading={confirmMut.isPending} disabled={confirmMut.isPending || route.length === 0}
                    onClick={() => confirmMut.mutate(createdTask.document_id)}>
                    Tasdiqlash
                  </Button>
                )}
              </div>
              <div className="max-h-[60vh] overflow-y-auto divide-y divide-slate-100">
                {route.length === 0 && <p className="text-xs text-slate-400 py-6 text-center">Qadam yo'q</p>}
                {route.map((stop, i) => (
                  <div key={i} className="flex items-start gap-3 px-4 py-2.5">
                    <span className="w-7 h-7 bg-blue-500/10 text-blue-600 rounded-full flex items-center justify-center font-bold text-sm shrink-0">
                      {stop.sequence}
                    </span>
                    <div className="min-w-0 flex-1 text-xs">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono font-semibold text-slate-700">{stop.location_code}</span>
                        <span className="text-green-600 font-semibold">{stop.take_qty} dona</span>
                        {stop.is_partial_pallet && <Badge tone="orange"><Layers size={10} /> Qisman</Badge>}
                      </div>
                      {(stop.product_name || stop.product_code) && (
                        <div className="text-slate-600 mt-0.5 truncate">
                          {stop.product_name ?? '—'}
                          {stop.product_code && <span className="text-slate-400 font-mono"> · {stop.product_code}</span>}
                        </div>
                      )}
                      {(stop.lot_number || stop.expiry_date) && (
                        <div className="text-slate-400 mt-0.5 flex flex-wrap gap-x-3">
                          {stop.lot_number && <span>Partiya: {stop.lot_number}</span>}
                          {stop.expiry_date && <span>Muddat: {String(stop.expiry_date).slice(0, 10)}</span>}
                        </div>
                      )}
                      {stop.marking_codes && stop.marking_codes.length > 0 && (
                        <div className="text-slate-300 mt-0.5">{stop.marking_codes.length} markirovka kodi</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Interaktiv sklad xaritasi + optimal terish yo'li ────────────────────────
function PickRouteMap({ locations, route }: { locations: any[]; route: RouteStop[] }) {
  const model = useMemo(() => {
    // Yacheyka kodi → koordinata (x,y). Stellaj bo'yicha guruhlaymiz (fon uchun).
    const byCode = new Map<string, { x: number; y: number }>()
    const cells = new Map<string, { x: number; y: number; code: string }>()
    for (const l of locations) {
      const x = l.x ?? 0, y = l.y ?? 0
      byCode.set(l.code, { x, y })
      const rack = l.rack_group || String(l.code).replace(/-\d+$/, '') || l.code
      if (!cells.has(rack)) cells.set(rack, { x, y, code: rack })
    }
    // Marshrut to'xtashlari uchun koordinata (kod topilmasa — chetga qo'yamiz).
    const stops = route.map((s, idx) => {
      const c = byCode.get(s.location_code)
      return { ...s, x: c?.x ?? null, y: c?.y ?? null, idx }
    })
    const known = stops.filter(s => s.x != null) as (RouteStop & { x: number; y: number; idx: number })[]
    const allX = [...cells.values()].map(c => c.x).concat(known.map(s => s.x))
    const allY = [...cells.values()].map(c => c.y).concat(known.map(s => s.y))
    const maxX = allX.length ? Math.max(...allX) : 10
    const maxY = allY.length ? Math.max(...allY) : 10
    return { cells: [...cells.values()], known, maxX, maxY }
  }, [locations, route])

  const SC = 44, PAD = 26, CW = 1.4, CH = 1.0
  const W = model.maxX * SC + PAD * 2 + CW * SC
  const H = model.maxY * SC + PAD * 2 + CH * SC
  const px = (v: number) => v * SC + PAD
  const cx = (x: number) => px(x) + (CW * SC) / 2
  const cy = (y: number) => px(y) + (CH * SC) / 2

  const routeCodes = new Set(route.map(r => r.location_code))
  const missingCoords = model.known.length < route.length

  return (
    <div className="space-y-2">
      <div className="overflow-auto rounded-xl border border-slate-200 bg-slate-50">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxHeight: '62vh', display: 'block' }}>
          {/* Fon: barcha yacheykalar */}
          {model.cells.map((c, i) => {
            const active = routeCodes.has(c.code) || [...routeCodes].some(rc => rc.startsWith(c.code))
            return (
              <rect key={i} x={px(c.x)} y={px(c.y)} width={CW * SC} height={CH * SC} rx={3}
                fill={active ? '#dbeafe' : '#eef2f7'} stroke={active ? '#3b82f6' : '#e2e8f0'} strokeWidth={active ? 1.5 : 0.75} />
            )
          })}
          {/* Yo'l chizig'i (ketma-ketlik bo'yicha) */}
          {model.known.length > 1 && (
            <polyline
              points={model.known.map(s => `${cx(s.x)},${cy(s.y)}`).join(' ')}
              fill="none" stroke="#2563eb" strokeWidth={2.5} strokeDasharray="6 4"
              strokeLinejoin="round" strokeLinecap="round" opacity={0.8} />
          )}
          {/* To'xtash markerlari */}
          {model.known.map((s, i) => (
            <g key={i}>
              <circle cx={cx(s.x)} cy={cy(s.y)} r={11} fill="#2563eb" stroke="#fff" strokeWidth={2} />
              <text x={cx(s.x)} y={cy(s.y) + 3.5} textAnchor="middle" fontSize={11} fontWeight={700} fill="#fff">{s.sequence}</text>
              <text x={cx(s.x)} y={cy(s.y) - 14} textAnchor="middle" fontSize={8.5} fontWeight={600} fill="#334155">{s.location_code}</text>
            </g>
          ))}
        </svg>
      </div>
      <p className="text-[11px] text-slate-400 flex items-center gap-1.5">
        <span className="inline-block w-3 h-2 rounded bg-blue-200 border border-blue-500" /> teriladigan yacheyka ·
        <span className="inline-block w-4 border-t-2 border-dashed border-blue-600" /> optimal yo'l (S-shakl, ketma-ket)
      </p>
      {missingCoords && (
        <p className="text-[11px] text-amber-600">
          Diqqat: ba'zi yacheykalar xaritada koordinatasiz — ular yo'lda ko'rsatilmadi (Sklad muharririda joyini belgilang).
        </p>
      )}
    </div>
  )
}
