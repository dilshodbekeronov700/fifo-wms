/**
 * TSD Qabul — skanerdan mahsulotni qabul qilib, yacheykaga joylash.
 * Oqim (backend tayyor): scan-suggest → yacheyka tanlash → reserve (bron) →
 * yacheyka barkodini skanlab confirm. Har bosqich bitta ekran.
 */
import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  getWarehouses, putawayScanSuggest, putawayReserve, putawayConfirm, putawayCancel,
} from '../lib/api'
import { useAuthStore } from '../store/auth'
import {
  ScanLine, Package, MapPin, CheckCircle2, AlertTriangle, RotateCcw, Boxes, Barcode,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader, Card, Button, Select, Badge, Input } from '../components/ui'

function nameOf(n: any): string {
  if (!n) return '—'
  if (typeof n === 'string') return n
  return n.uz || n.ru || n.en || '—'
}

interface Slot {
  location_id: string
  location_code: string
  zone_type: string
  score: number
  reason: string
  remaining_boxes: number
}
interface Resolved {
  code: string
  ownership_ok: boolean
  reason?: string
  package_type?: string
  gtin?: string
  expiry_date?: string
  production_date?: string
  box_count: number
  unit_count: number
  counting_method: string
  product_id?: string
  product_name?: any
  batch_id?: string
  children: string[]
}

export default function TsdReceive() {
  const { selectedWarehouseId } = useAuthStore()
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [whId, setWhId] = useState('')
  const wid = whId || selectedWarehouseId || (warehouses as any[])[0]?.id

  const [code, setCode] = useState('')
  const [resolved, setResolved] = useState<Resolved | null>(null)
  const [candidates, setCandidates] = useState<Slot[]>([])
  const [reservation, setReservation] = useState<any | null>(null)
  const [locScan, setLocScan] = useState('')
  const [done, setDone] = useState<any | null>(null)

  const reset = () => {
    setCode(''); setResolved(null); setCandidates([]); setReservation(null); setLocScan(''); setDone(null)
  }

  const scanMut = useMutation({
    mutationFn: () => putawayScanSuggest({ warehouse_id: wid, code: code.trim(), top_n: 6 }),
    onSuccess: (d: any) => {
      setResolved(d.resolved); setCandidates(d.candidates ?? [])
      if (!d.candidates?.length) toast('Mos yacheyka topilmadi', { icon: '⚠️' })
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Skanlashda xatolik'),
  })

  const reserveMut = useMutation({
    mutationFn: (slot: Slot) => putawayReserve({
      warehouse_id: wid,
      code: resolved!.code,
      location_id: slot.location_id,
      product_id: resolved!.product_id ?? null,
      batch_id: resolved!.batch_id ?? null,
      qty: resolved!.box_count || 1,
      unit_count: resolved!.unit_count || 0,
      package_type: resolved!.package_type ?? null,
      score: slot.score,
      reason: slot.reason,
      manual: false,
      force: !resolved!.product_id,   // mahsulot noma'lum bo'lsa force kerak
      payload: { children: resolved!.children, gtin: resolved!.gtin, expiry_date: resolved!.expiry_date },
    }),
    onSuccess: (r: any) => { setReservation(r); toast.success('Yacheyka bron qilindi — endi yacheyka barkodini skanlang') },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Bron qilishda xatolik'),
  })

  const confirmMut = useMutation({
    mutationFn: () => putawayConfirm({ reservation_id: reservation.id, location_barcode: locScan.trim() }),
    onSuccess: (d: any) => { setDone(d); toast.success('Joylashtirildi ✓') },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Tasdiqlashda xatolik'),
  })

  const cancelMut = useMutation({
    mutationFn: () => putawayCancel(reservation.id),
    onSuccess: () => { setReservation(null); toast('Bron bekor qilindi', { icon: '↩️' }) },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
  })

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-3xl mx-auto">
      <PageHeader
        icon={<ScanLine size={20} />}
        title="TSD Qabul"
        subtitle="Skanla → yacheyka tavsiyasi → bron → yacheykani skanlab tasdiqlash"
        actions={
          <Select value={wid ?? ''} onChange={e => { setWhId(e.target.value); reset() }} className="w-auto min-w-40">
            {(warehouses as any[]).map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </Select>
        }
      />

      {/* Tugallandi ekrani */}
      {done ? (
        <Card className="text-center py-8 space-y-3">
          <CheckCircle2 size={48} className="mx-auto text-emerald-500" />
          <div className="text-lg font-semibold text-slate-800">Joylashtirildi</div>
          <div className="text-sm text-slate-500">
            {nameOf(resolved?.product_name)} · <span className="font-mono">{resolved?.code?.slice(0, 20)}…</span>
          </div>
          {done.code_tree?.total != null && (
            <div className="text-xs text-slate-400">{done.code_tree.total} kod daraxtga biriktirildi</div>
          )}
          <Button icon={<RotateCcw size={15} />} onClick={reset} className="mt-2">Yangi skan</Button>
        </Card>
      ) : !resolved ? (
        /* 1-qadam: kodni skanlash */
        <Card className="space-y-3">
          <label className="text-sm font-medium text-slate-600 flex items-center gap-2">
            <Barcode size={16} className="text-blue-500" /> Pallet / quti kodini skanlang yoki kiriting
          </label>
          <Input
            autoFocus value={code} onChange={e => setCode(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && code.trim()) scanMut.mutate() }}
            placeholder="0104780094510087…" className="font-mono text-sm h-12" />
          <Button onClick={() => scanMut.mutate()} loading={scanMut.isPending}
            disabled={!code.trim() || !wid} icon={<ScanLine size={16} />} className="w-full h-12">
            Skanlash
          </Button>
        </Card>
      ) : (
        <>
          {/* Aniqlangan mahsulot */}
          <Card className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-semibold text-slate-800">
                <Package size={17} className="text-blue-500" /> {nameOf(resolved.product_name)}
              </div>
              <Button variant="ghost" size="sm" icon={<RotateCcw size={13} />} onClick={reset}>Bekor</Button>
            </div>
            {!resolved.ownership_ok && (
              <div className="text-xs text-rose-600 bg-rose-500/10 rounded-lg px-2 py-1.5 flex items-center gap-1.5">
                <AlertTriangle size={13} /> Egalik tekshiruvi: {resolved.reason}
              </div>
            )}
            {!resolved.product_id && (
              <div className="text-xs text-amber-600 bg-amber-500/10 rounded-lg px-2 py-1.5 flex items-center gap-1.5">
                <AlertTriangle size={13} /> Mahsulot WMS'da topilmadi (mapping yo'q) — force bilan bron qilinadi.
              </div>
            )}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <Info k="GTIN" v={resolved.gtin} mono />
              <Info k="Qadoq" v={resolved.package_type} />
              <Info k="Quti" v={resolved.box_count} />
              <Info k="Dona" v={resolved.unit_count} />
              <Info k="Muddat" v={resolved.expiry_date?.slice(0, 10)} />
              <Info k="Hisob usuli" v={resolved.counting_method} />
              <Info k="Ichki kodlar" v={resolved.children?.length} />
            </div>
          </Card>

          {/* 2 yoki 3-qadam */}
          {!reservation ? (
            <Card padded={false} className="overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-200/60 flex items-center gap-2">
                <MapPin size={15} className="text-green-500" />
                <span className="font-semibold text-slate-700 text-sm">Yacheyka tavsiyasi</span>
                <span className="text-xs text-slate-400">— eng optimal birinchi</span>
              </div>
              <div className="divide-y divide-slate-100">
                {candidates.length === 0 && <p className="text-xs text-slate-400 py-6 text-center">Mos yacheyka topilmadi</p>}
                {candidates.map((s, i) => (
                  <button key={s.location_id} onClick={() => reserveMut.mutate(s)} disabled={reserveMut.isPending}
                    className="w-full text-left px-4 py-3 hover:bg-slate-500/5 transition flex items-center gap-3 disabled:opacity-50">
                    <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${i === 0 ? 'bg-green-500/15 text-green-600' : 'bg-slate-500/10 text-slate-500'}`}>
                      {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-slate-700">{s.location_code}</span>
                        <Badge tone="slate">{s.zone_type}</Badge>
                        {i === 0 && <Badge tone="green">tavsiya</Badge>}
                      </div>
                      <div className="text-xs text-slate-400 truncate">{s.reason} · bo'sh: {s.remaining_boxes}</div>
                    </div>
                    <span className="text-xs text-slate-400 shrink-0">ball {Math.round(s.score)}</span>
                  </button>
                ))}
              </div>
            </Card>
          ) : (
            /* 3-qadam: yacheyka barkodini skanlab tasdiqlash */
            <Card className="space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <Boxes size={16} className="text-blue-500" />
                <span className="text-slate-600">Bron qilindi:</span>
                <span className="font-mono font-semibold text-slate-800">
                  {candidates.find(c => c.location_id === reservation.location_id)?.location_code ?? reservation.location_id?.slice(0, 8)}
                </span>
              </div>
              <label className="text-sm font-medium text-slate-600 flex items-center gap-2">
                <Barcode size={16} className="text-green-500" /> Yacheyka barkodini skanlang
              </label>
              <Input
                autoFocus value={locScan} onChange={e => setLocScan(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && locScan.trim()) confirmMut.mutate() }}
                placeholder="A-01-3 yoki QR…" className="font-mono text-sm h-12" />
              <div className="flex gap-2">
                <Button onClick={() => confirmMut.mutate()} loading={confirmMut.isPending}
                  disabled={!locScan.trim()} variant="success" icon={<CheckCircle2 size={16} />} className="flex-1 h-12">
                  Tasdiqlash
                </Button>
                <Button variant="ghost" onClick={() => cancelMut.mutate()} loading={cancelMut.isPending}
                  className="text-rose-600 hover:bg-rose-500/10">Bronni bekor</Button>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  )
}

function Info({ k, v, mono }: { k: string; v: any; mono?: boolean }) {
  return (
    <div className="rounded-lg bg-slate-500/5 px-2 py-1.5">
      <div className="text-[10px] text-slate-400">{k}</div>
      <div className={`text-slate-700 truncate ${mono ? 'font-mono text-[11px]' : ''}`}>{v != null && v !== '' ? String(v) : '—'}</div>
    </div>
  )
}
