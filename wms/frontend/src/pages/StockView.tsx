import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { useState } from 'react'
import { Boxes, Layers, Package, AlertTriangle, Box } from 'lucide-react'
import {
  getWarehouses,
  getProducts,
  getStockDetailed,
  getStockSummary,
} from '../lib/api'

const PAGE_SIZE = 25

export default function StockView({ embedded = false }: { embedded?: boolean }) {
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [whId, setWhId] = useState<string>('')
  const wid = whId || warehouses[0]?.id

  const { data: products = [] } = useQuery({ queryKey: ['products'], queryFn: getProducts })
  const prodMap: Record<string, any> = Object.fromEntries(products.map((p: any) => [p.id, p]))

  const [productId, setProductId] = useState<string>('')
  const [status, setStatus] = useState<string>('')
  const [palletOpen, setPalletOpen] = useState<string>('') // '', 'true', 'false'
  const [offset, setOffset] = useState<number>(0)

  // Reset paging when filters change
  const resetAnd = (fn: (v: string) => void) => (v: string) => {
    setOffset(0)
    fn(v)
  }

  const filters = {
    product_id: productId || undefined,
    status: status || undefined,
    pallet_open: palletOpen === '' ? undefined : palletOpen === 'true',
    limit: PAGE_SIZE,
    offset,
  }

  const { data: detailed, isLoading } = useQuery({
    queryKey: ['stock-detailed', wid, productId, status, palletOpen, offset],
    queryFn: () => getStockDetailed(wid, filters),
    enabled: !!wid,
    placeholderData: keepPreviousData,
  })

  const { data: summary } = useQuery({
    queryKey: ['stock-summary', wid, productId, status, palletOpen],
    queryFn: () =>
      getStockSummary(wid, {
        product_id: productId || undefined,
        status: status || undefined,
        pallet_open: palletOpen === '' ? undefined : palletOpen === 'true',
      }),
    enabled: !!wid,
    placeholderData: keepPreviousData,
  })

  // Backend may return either an array or { items, total } — normalize.
  const rows: any[] = Array.isArray(detailed) ? detailed : detailed?.items ?? []
  const total: number =
    (Array.isArray(detailed) ? undefined : detailed?.total) ??
    summary?.total_records ??
    (offset + rows.length + (rows.length === PAGE_SIZE ? 1 : 0))

  const statusColor: Record<string, string> = {
    available: 'bg-green-100 text-green-700',
    booked: 'bg-blue-100 text-blue-700',
    blocked: 'bg-red-100 text-red-600',
  }

  const summaryCards = [
    {
      label: 'Jami SKU',
      value: summary?.total_skus ?? '—',
      icon: Package,
      tint: 'bg-blue-50 text-blue-600',
    },
    {
      label: 'Jami miqdor',
      value: summary?.total_qty ?? '—',
      icon: Boxes,
      tint: 'bg-indigo-50 text-indigo-600',
    },
    {
      label: 'Ochiq palletlar',
      value: summary?.open_pallets ?? '—',
      icon: Box,
      tint: 'bg-orange-50 text-orange-600',
    },
    {
      label: 'Bloklangan',
      value: summary?.blocked ?? '—',
      icon: AlertTriangle,
      tint: 'bg-red-50 text-red-600',
    },
  ]

  const prodName = (id: string) => {
    const p = prodMap[id]
    return p?.name?.ru ?? p?.name?.uz ?? null
  }

  return (
    <div className={embedded ? 'space-y-5' : 'p-6 space-y-5'}>
      <div className="flex items-center justify-between">
        {!embedded && (
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Boxes size={20} className="text-blue-500" />
            Qoldiq (batafsil)
          </h1>
        )}
        <select
          className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-600 bg-white"
          value={wid ?? ''}
          onChange={e => {
            setOffset(0)
            setWhId(e.target.value)
          }}
        >
          {warehouses.map((wh: any) => (
            <option key={wh.id} value={wh.id}>{wh.name}</option>
          ))}
        </select>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map(c => {
          const Icon = c.icon
          return (
            <div key={c.label} className="bg-white rounded-xl shadow-sm p-5 flex items-center gap-4">
              <div className={`w-11 h-11 rounded-lg flex items-center justify-center ${c.tint}`}>
                <Icon size={20} />
              </div>
              <div>
                <div className="text-2xl font-bold text-slate-800">{c.value}</div>
                <div className="text-xs text-slate-400">{c.label}</div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm p-5 flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">Mahsulot</label>
          <select
            className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-600 bg-white min-w-[200px]"
            value={productId}
            onChange={e => resetAnd(setProductId)(e.target.value)}
          >
            <option value="">Barchasi</option>
            {products.map((p: any) => (
              <option key={p.id} value={p.id}>
                {p.name?.ru ?? p.name?.uz ?? p.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">Holat</label>
          <select
            className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-600 bg-white"
            value={status}
            onChange={e => resetAnd(setStatus)(e.target.value)}
          >
            <option value="">Barchasi</option>
            <option value="available">available</option>
            <option value="booked">booked</option>
            <option value="blocked">blocked</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">Pallet</label>
          <select
            className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-600 bg-white"
            value={palletOpen}
            onChange={e => resetAnd(setPalletOpen)(e.target.value)}
          >
            <option value="">Barchasi</option>
            <option value="true">Ochiq</option>
            <option value="false">Yopiq</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-slate-400 text-xs uppercase">
              <th className="text-left px-4 py-3">Mahsulot</th>
              <th className="text-left px-4 py-3">Yacheyka</th>
              <th className="text-left px-4 py-3">Partiya</th>
              <th className="text-right px-4 py-3">Jami</th>
              <th className="text-right px-4 py-3">Bron</th>
              <th className="text-right px-4 py-3">Erkin</th>
              <th className="text-left px-4 py-3">Holat</th>
              <th className="text-left px-4 py-3">Pallet</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={8} className="text-center py-8 text-slate-400">Yuklanmoqda...</td></tr>
            )}
            {!isLoading && rows.map((s: any) => (
              <tr key={s.id} className="border-b border-slate-50 hover:bg-slate-50">
                <td className="px-4 py-3 text-slate-700 font-medium">
                  {prodName(s.product_id) ?? (
                    <span className="text-slate-400 font-mono text-xs">{String(s.product_id).slice(0, 8)}…</span>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-500 font-mono text-xs">
                  {s.location_code ?? s.location?.code ?? (s.location_id ? String(s.location_id).slice(0, 8) + '…' : '—')}
                </td>
                <td className="px-4 py-3 text-slate-500 font-mono text-xs">
                  {s.batch_code ?? s.batch?.code ?? (s.batch_id ? String(s.batch_id).slice(0, 8) + '…' : '—')}
                </td>
                <td className="px-4 py-3 text-right font-semibold text-slate-800">{s.qty}</td>
                <td className="px-4 py-3 text-right text-blue-600">{s.qty_booked}</td>
                <td className="px-4 py-3 text-right text-green-600">{(s.qty ?? 0) - (s.qty_booked ?? 0)}</td>
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
            ))}
            {!isLoading && rows.length === 0 && (
              <tr><td colSpan={8} className="text-center py-10 text-slate-400">
                <Layers size={24} className="mx-auto mb-2 opacity-30" />
                Qoldiq yo'q
              </td></tr>
            )}
          </tbody>
        </table>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
          <span>
            {rows.length > 0
              ? `${offset + 1}–${offset + rows.length}${total ? ` / ${total}` : ''}`
              : '0'}
          </span>
          <div className="flex gap-2">
            <button
              className="px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Oldingi
            </button>
            <button
              className="px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50"
              disabled={rows.length < PAGE_SIZE}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Keyingi
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
