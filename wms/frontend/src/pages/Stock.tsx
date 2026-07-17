import { useQuery } from '@tanstack/react-query'
import { getWarehouses, getStock, getProducts } from '../lib/api'
import { useState } from 'react'
import { Layers } from 'lucide-react'
import { SearchInput, FilterSelect, FilterBar } from '../components/Filters'

export default function Stock({ embedded = false }: { embedded?: boolean }) {
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [whId, setWhId] = useState<string>('')
  const wid = whId || warehouses[0]?.id
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [hideZero, setHideZero] = useState(false)

  const { data: stock = [], isLoading } = useQuery({
    queryKey: ['stock', wid],
    queryFn: () => getStock(wid),
    enabled: !!wid,
  })
  const { data: products = [] } = useQuery({ queryKey: ['products'], queryFn: getProducts })
  const prodMap: Record<string, any> = Object.fromEntries(products.map((p: any) => [p.id, p]))

  const statusColor: Record<string, string> = {
    available: 'bg-green-100 text-green-700',
    booked: 'bg-blue-100 text-blue-700',
    blocked: 'bg-red-100 text-red-600',
  }

  const q = search.trim().toLowerCase()
  const filtered = (stock as any[]).filter((s: any) => {
    if (status && s.status !== status) return false
    if (hideZero && !(Number(s.qty_total ?? s.qty ?? 0) > 0)) return false
    if (!q) return true
    const prod = prodMap[s.product_id]
    return [prod?.name?.ru, prod?.name?.uz, prod?.gtin, s.product_id]
      .some(v => String(v ?? '').toLowerCase().includes(q))
  })
  const hasActive = !!search || !!status || hideZero

  return (
    <div className={embedded ? 'space-y-4' : 'p-6 space-y-4'}>
      <div className="flex items-center justify-between">
        {!embedded && <h1 className="text-xl font-bold text-slate-800">Qoldiqlar</h1>}
        <select
          className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-600 bg-white"
          value={wid}
          onChange={e => setWhId(e.target.value)}
        >
          {warehouses.map((wh: any) => (
            <option key={wh.id} value={wh.id}>{wh.name}</option>
          ))}
        </select>
      </div>

      <FilterBar hasActive={hasActive} onClear={() => { setSearch(''); setStatus(''); setHideZero(false) }}>
        <SearchInput value={search} onChange={setSearch} placeholder="Mahsulot / GTIN…" className="w-56" />
        <FilterSelect label="Barcha holatlar" value={status} onChange={setStatus} options={[
          { value: 'available', label: 'Erkin' },
          { value: 'booked', label: 'Bron' },
          { value: 'blocked', label: 'Bloklangan' },
        ]} />
        <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer select-none">
          <input type="checkbox" checked={hideZero} onChange={e => setHideZero(e.target.checked)} className="accent-blue-600" />
          Qoldiq=0 yashir
        </label>
        <span className="text-xs text-slate-400">{filtered.length} / {(stock as any[]).length}</span>
      </FilterBar>

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-slate-400 text-xs uppercase">
              <th className="text-left px-4 py-3">Mahsulot</th>
              <th className="text-right px-4 py-3">Jami</th>
              <th className="text-right px-4 py-3">Bron</th>
              <th className="text-right px-4 py-3">Erkin</th>
              <th className="text-left px-4 py-3">Holat</th>
              <th className="text-left px-4 py-3">Pallet</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={6} className="text-center py-8 text-slate-400">Yuklanmoqda...</td></tr>}
            {!isLoading && !filtered.length && <tr><td colSpan={6} className="text-center py-8 text-slate-400">Qoldiq topilmadi</td></tr>}
            {filtered.map((s: any) => {
              const prod = prodMap[s.product_id]
              return (
                <tr key={s.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-700 font-medium">
                    {prod?.name?.ru ?? prod?.name?.uz ?? <span className="text-slate-400 font-mono text-xs">{s.product_id.slice(0,8)}…</span>}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-slate-800">{s.qty}</td>
                  <td className="px-4 py-3 text-right text-blue-600">{s.qty_booked}</td>
                  <td className="px-4 py-3 text-right text-green-600">{s.qty - s.qty_booked}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor[s.status] ?? 'bg-slate-100 text-slate-500'}`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {s.pallet_open
                      ? <span className="text-xs text-orange-500 font-medium">Ochiq</span>
                      : <span className="text-xs text-slate-300">—</span>}
                  </td>
                </tr>
              )
            })}
            {!isLoading && stock.length === 0 && (
              <tr><td colSpan={6} className="text-center py-10 text-slate-400">
                <Layers size={24} className="mx-auto mb-2 opacity-30"/>
                Qoldiq yo'q
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
