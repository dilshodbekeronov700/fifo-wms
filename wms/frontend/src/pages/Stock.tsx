/**
 * Qoldiqlar — savdo-birligi bo'yicha JAMLANGAN ko'rinish (GROUP/UNIT birlashadi).
 * Muddat/FEFO, joylashuv, aylanma (days-of-supply), band qoldiqni bo'shatish.
 */
import { useMemo, useState, Fragment } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getWarehouses, getStockConsolidated, releaseBookings } from '../lib/api'
import { Layers, Boxes, MapPin, Clock, Unlock, ChevronRight, ChevronDown, PackageX } from 'lucide-react'
import toast from 'react-hot-toast'
import { SearchInput, FilterSelect, FilterBar } from '../components/Filters'
import { Badge } from '../components/ui'
import type { Tone } from '../components/ui'

type Row = {
  key: string; product_ids: string[]; name: string; gtin: string | null
  category: string | null; units_per_box: number | null; abc_class: string | null
  qty: number; booked: number; available: number; blocked_qty: number
  locations: string[]; location_count: number; open_pallet: boolean; batch_count: number
  nearest_expiry: string | null; expiry_days: number | null; expired_qty: number
  sold_30d: number; days_of_supply: number | null
}

const nf = (v: number) => new Intl.NumberFormat('uz-UZ').format(v)

function expiryTone(days: number | null): { tone: Tone; label: string } | null {
  if (days == null) return null
  if (days < 0) return { tone: 'red', label: `Muddati o'tgan (${-days} kun)` }
  if (days <= 7) return { tone: 'red', label: `${days} kun qoldi` }
  if (days <= 30) return { tone: 'amber', label: `${days} kun qoldi` }
  return { tone: 'slate', label: `${days} kun` }
}

export default function Stock({ embedded = false }: { embedded?: boolean }) {
  const qc = useQueryClient()
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [whId, setWhId] = useState<string>('')
  const wid = whId || (warehouses as any[])[0]?.id

  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [sort, setSort] = useState('name')
  const [hideZero, setHideZero] = useState(false)
  const [onlyExpiring, setOnlyExpiring] = useState(false)
  const [onlyBooked, setOnlyBooked] = useState(false)
  const [unit, setUnit] = useState<'quti' | 'dona'>('quti')
  const [expanded, setExpanded] = useState<string | null>(null)

  const { data: rows = [], isLoading } = useQuery<Row[]>({
    queryKey: ['stock-consolidated', wid],
    queryFn: () => getStockConsolidated(wid),
    enabled: !!wid,
  })

  const releaseMut = useMutation({
    mutationFn: () => releaseBookings(wid),
    onSuccess: (d: any) => {
      qc.invalidateQueries({ queryKey: ['stock-consolidated'] })
      toast.success(`Bo'shatildi: ${d.freed_qty ?? 0} birlik · ${d.cancelled_documents ?? 0} hujjat bekor qilindi`)
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
  })

  const categories = useMemo(
    () => Array.from(new Set((rows as Row[]).map(r => r.category).filter(Boolean))) as string[],
    [rows])

  const totals = useMemo(() => {
    const r = rows as Row[]
    return {
      skus: r.length,
      qty: r.reduce((s, x) => s + x.qty, 0),
      available: r.reduce((s, x) => s + x.available, 0),
      booked: r.reduce((s, x) => s + x.booked, 0),
      openPallets: r.filter(x => x.open_pallet).length,
      expiringSoon: r.filter(x => x.expiry_days != null && x.expiry_days >= 0 && x.expiry_days <= 30).length,
      expired: r.filter(x => x.expired_qty > 0).length,
    }
  }, [rows])

  const q = search.trim().toLowerCase()
  const filtered = useMemo(() => {
    let r = (rows as Row[]).filter(x => {
      if (hideZero && x.qty <= 0) return false
      if (category && x.category !== category) return false
      if (onlyBooked && x.booked <= 0) return false
      if (onlyExpiring && !(x.expiry_days != null && x.expiry_days <= 30)) return false
      if (!q) return true
      return [x.name, x.gtin, x.category].some(v => String(v ?? '').toLowerCase().includes(q))
    })
    const cmp: Record<string, (a: Row, b: Row) => number> = {
      name: (a, b) => a.name.localeCompare(b.name),
      available: (a, b) => b.available - a.available,
      expiry: (a, b) => (a.expiry_days ?? 1e9) - (b.expiry_days ?? 1e9),
      velocity: (a, b) => b.sold_30d - a.sold_30d,
      dos: (a, b) => (a.days_of_supply ?? 1e9) - (b.days_of_supply ?? 1e9),
    }
    return [...r].sort(cmp[sort] ?? cmp.name)
  }, [rows, q, category, hideZero, onlyBooked, onlyExpiring, sort])

  const hasActive = !!search || !!category || hideZero || onlyExpiring || onlyBooked

  // dona/quti ko'rinishi (units_per_box bo'yicha) — faqat ko'rsatish yordami
  const disp = (v: number, upb: number | null) => (unit === 'dona' && upb ? v * upb : v)
  const unitLbl = unit === 'dona' ? 'dona' : 'quti'

  const Kpi = ({ label, value, tone, sub }: { label: string; value: any; tone?: string; sub?: string }) => (
    <div className="px-3 py-2 rounded-xl border border-slate-200/70 bg-white min-w-[110px]">
      <div className="text-[11px] text-slate-400">{label}</div>
      <div className={`text-lg font-bold ${tone ?? 'text-slate-800'}`}>{value}</div>
      {sub && <div className="text-[10px] text-slate-400">{sub}</div>}
    </div>
  )

  return (
    <div className={embedded ? 'space-y-4' : 'p-6 space-y-4'}>
      <div className="flex items-center justify-between gap-2 flex-wrap">
        {!embedded && <h1 className="text-xl font-bold text-slate-800">Qoldiqlar</h1>}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex rounded-lg border border-slate-200 overflow-hidden text-xs">
            {(['quti', 'dona'] as const).map(u => (
              <button key={u} onClick={() => setUnit(u)}
                className={`px-2.5 py-1.5 transition ${unit === u ? 'bg-blue-600 text-white' : 'bg-white text-slate-500 hover:bg-slate-50'}`}>
                {u === 'quti' ? 'Quti' : 'Dona'}
              </button>
            ))}
          </div>
          <select className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-600 bg-white"
            value={wid} onChange={e => setWhId(e.target.value)}>
            {(warehouses as any[]).map((wh: any) => <option key={wh.id} value={wh.id}>{wh.name}</option>)}
          </select>
        </div>
      </div>

      {/* KPI strip */}
      <div className="flex flex-wrap gap-2">
        <Kpi label="SKU" value={nf(totals.skus)} />
        <Kpi label="Jami" value={nf(totals.qty)} sub={unitLbl} />
        <Kpi label="Erkin" value={nf(totals.available)} tone="text-green-600" sub={unitLbl} />
        <Kpi label="Band" value={nf(totals.booked)} tone="text-blue-600" sub={unitLbl} />
        <Kpi label="Ochiq pallet" value={nf(totals.openPallets)} tone="text-orange-500" />
        <Kpi label="Muddati yaqin" value={nf(totals.expiringSoon)} tone="text-amber-600" sub="≤30 kun" />
        <Kpi label="Muddati o'tgan" value={nf(totals.expired)} tone="text-rose-600" />
        {totals.booked > 0 && (
          <button
            onClick={() => { if (confirm('Tasdiqlanmagan chiqim bandlarini bo\'shataymi? Ochiq pick hujjatlari bekor qilinadi.')) releaseMut.mutate() }}
            disabled={releaseMut.isPending}
            className="self-center inline-flex items-center gap-1.5 text-xs px-3 py-2 rounded-xl border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-50">
            <Unlock size={13} /> {releaseMut.isPending ? 'Bo\'shatilmoqda…' : 'Bandlarni bo\'shatish'}
          </button>
        )}
      </div>

      <FilterBar hasActive={hasActive} onClear={() => { setSearch(''); setCategory(''); setHideZero(false); setOnlyExpiring(false); setOnlyBooked(false) }}>
        <SearchInput value={search} onChange={setSearch} placeholder="Mahsulot / GTIN…" className="w-56" />
        {categories.length > 0 && (
          <FilterSelect label="Barcha kategoriya" value={category} onChange={setCategory}
            options={categories.map(c => ({ value: c, label: c }))} />
        )}
        <FilterSelect label="Saralash" value={sort} onChange={setSort} options={[
          { value: 'name', label: 'Nom (A–Z)' },
          { value: 'available', label: 'Erkin (ko\'p)' },
          { value: 'expiry', label: 'Muddat (yaqin)' },
          { value: 'velocity', label: 'Aylanma (tez)' },
          { value: 'dos', label: 'Yetish kuni (kam)' },
        ]} />
        <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer select-none">
          <input type="checkbox" checked={hideZero} onChange={e => setHideZero(e.target.checked)} className="accent-blue-600" /> Qoldiq=0 yashir
        </label>
        <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer select-none">
          <input type="checkbox" checked={onlyExpiring} onChange={e => setOnlyExpiring(e.target.checked)} className="accent-amber-600" /> Muddati yaqin
        </label>
        <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer select-none">
          <input type="checkbox" checked={onlyBooked} onChange={e => setOnlyBooked(e.target.checked)} className="accent-blue-600" /> Bandlar
        </label>
        <span className="text-xs text-slate-400">{filtered.length} / {(rows as Row[]).length}</span>
      </FilterBar>

      <div className="bg-white rounded-xl shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-slate-400 text-xs uppercase">
              <th className="w-6"></th>
              <th className="text-left px-3 py-3">Mahsulot</th>
              <th className="text-right px-3 py-3">Jami</th>
              <th className="text-right px-3 py-3">Band</th>
              <th className="text-right px-3 py-3">Erkin</th>
              <th className="text-left px-3 py-3">Muddat</th>
              <th className="text-left px-3 py-3">Joylashuv</th>
              <th className="text-right px-3 py-3">Aylanma/kun</th>
              <th className="text-left px-3 py-3">Holat</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={9} className="text-center py-8 text-slate-400">Yuklanmoqda...</td></tr>}
            {!isLoading && !filtered.length && (
              <tr><td colSpan={9} className="text-center py-10 text-slate-400">
                <Layers size={24} className="mx-auto mb-2 opacity-30" /> Qoldiq topilmadi
              </td></tr>
            )}
            {filtered.map(r => {
              const et = expiryTone(r.expiry_days)
              const open = expanded === r.key
              return (
                <Fragment key={r.key}>
                  <tr className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer"
                    onClick={() => setExpanded(open ? null : r.key)}>
                    <td className="pl-3 text-slate-400">{open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</td>
                    <td className="px-3 py-3">
                      <div className="font-medium text-slate-700 flex items-center gap-1.5">
                        {r.name}
                        {r.abc_class && <Badge tone="teal">{r.abc_class}</Badge>}
                      </div>
                      {r.gtin && <div className="text-[11px] font-mono text-slate-400">{r.gtin}</div>}
                    </td>
                    <td className="px-3 py-3 text-right font-semibold text-slate-800">{nf(disp(r.qty, r.units_per_box))}</td>
                    <td className="px-3 py-3 text-right text-blue-600">{r.booked ? nf(disp(r.booked, r.units_per_box)) : '—'}</td>
                    <td className="px-3 py-3 text-right text-green-600 font-medium">{nf(disp(r.available, r.units_per_box))}</td>
                    <td className="px-3 py-3">{et ? <Badge tone={et.tone}>{et.label}</Badge> : <span className="text-slate-300">—</span>}</td>
                    <td className="px-3 py-3 text-xs text-slate-500">
                      <span className="inline-flex items-center gap-1"><MapPin size={11} className="text-slate-400" />{r.location_count}</span>
                      {r.locations.length > 0 && <span className="text-slate-400"> · {r.locations.slice(0, 2).join(', ')}{r.locations.length > 2 ? '…' : ''}</span>}
                    </td>
                    <td className="px-3 py-3 text-right text-xs text-slate-500">
                      {r.days_of_supply != null ? <span title={`${r.sold_30d} / 30 kun`}>{r.days_of_supply} kun</span> : '—'}
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-1">
                        {r.open_pallet && <Badge tone="orange">Ochiq</Badge>}
                        {r.blocked_qty > 0 && <Badge tone="red">Blok {nf(r.blocked_qty)}</Badge>}
                        {r.expired_qty > 0 && <Badge tone="red"><PackageX size={10} /> {nf(r.expired_qty)}</Badge>}
                        {!r.open_pallet && !r.blocked_qty && !r.expired_qty && <span className="text-slate-300 text-xs">✓</span>}
                      </div>
                    </td>
                  </tr>
                  {open && (
                    <tr className="bg-slate-500/[0.03]">
                      <td></td>
                      <td colSpan={8} className="px-3 py-3">
                        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-2 text-xs">
                          <Info k="Bir qutida (dona)" v={r.units_per_box ?? '—'} />
                          <Info k="Partiyalar" v={r.batch_count} />
                          <Info k="Eng yaqin muddat" v={r.nearest_expiry ? r.nearest_expiry.slice(0, 10) : '—'} />
                          <Info k="Chiqim (30 kun)" v={`${nf(r.sold_30d)} ${unitLbl}`} />
                          <div className="sm:col-span-2 lg:col-span-4">
                            <div className="text-[10px] text-slate-400 mb-1 flex items-center gap-1"><Boxes size={11} /> Yacheykalar ({r.location_count})</div>
                            <div className="flex flex-wrap gap-1">
                              {r.locations.length ? r.locations.map(l => (
                                <span key={l} className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">{l}</span>
                              )) : <span className="text-slate-400">—</span>}
                            </div>
                          </div>
                          {r.expiry_days != null && r.expiry_days <= 30 && (
                            <div className="sm:col-span-2 lg:col-span-4 text-amber-600 flex items-center gap-1">
                              <Clock size={12} /> FEFO: bu partiyani birinchi tering (muddati yaqin).
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Info({ k, v }: { k: string; v: any }) {
  return (
    <div>
      <div className="text-[10px] text-slate-400">{k}</div>
      <div className="text-slate-700">{v}</div>
    </div>
  )
}
