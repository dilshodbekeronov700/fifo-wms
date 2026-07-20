/**
 * Smartup (ERP) ma'lumotlari — bitta joyda BARCHA Smartup'dan tortilgan ma'lumot.
 *  Buyurtmalar (order$export) · Kirimlar (input$export) · Qoldiq svereka (balance$export).
 *  "Yangilash" tugmasi Smartup'dan darhol qayta tortadi.
 */
import { useState, Fragment } from 'react'
import { SearchInput, FilterSelect, FilterBar } from '../components/Filters'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  RefreshCw, ArrowUpFromLine, ArrowDownToLine, GitCompareArrows, Package,
  ArrowLeftRight, ClipboardCheck, Building2, Boxes, Layers, CheckCircle2, AlertCircle,
  ChevronRight, ChevronDown, Barcode,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getWarehouses, getShipmentOrders, getProductionInputs, getPurchases,
  getSmartupReconciliation, pullSmartup, getErpPolicy, pushOrderStatus,
  getSmartupMovements, getSmartupStocktakings, getSmartupWriteoffs, getSmartupReturns,
  getSmartupCurrentOrg,
} from '../lib/api'
import { PageHeader, Card, Tabs, Button, Select, Badge, StatCard } from '../components/ui'
import { motion } from 'framer-motion'
import { staggerContainer } from '../lib/motion'

type Tab = 'orders' | 'inputs' | 'movements' | 'stocktaking' | 'writeoffs' | 'svereka'

// Smartup buyurtma status kodlari → tushunarli o'zbekcha yorliq + rang.
const ORDER_STATUS: Record<string, { label: string; cls: string }> = {
  'A':   { label: 'Arxiv',              cls: 'bg-slate-100 text-slate-500' },
  'B#N': { label: 'Yangi',              cls: 'bg-emerald-100 text-emerald-700' },   // Новый
  'B#E': { label: 'Jarayonda',         cls: 'bg-amber-100 text-amber-700' },        // В обработке
  'B#W': { label: 'Kutilmoqda',        cls: 'bg-blue-100 text-blue-700' },          // В ожидании
  'B#V': { label: 'Tasdiqlangan',      cls: 'bg-violet-100 text-violet-700' },      // Smartup UI'da alohida karta yo'q
  'B#S': { label: 'Jo\'natilgan',       cls: 'bg-indigo-100 text-indigo-700' },      // Отгружен
  'C':   { label: 'Yetkazilgan',        cls: 'bg-rose-100 text-rose-700' },          // Доставлен
  'D':   { label: 'Qoralama',           cls: 'bg-slate-100 text-slate-600' },        // Черновик
}
const statusBadge = (s: string) => ORDER_STATUS[s] ?? { label: s || '—', cls: 'bg-slate-100 text-slate-600' }

const fmtSum = (v: number | null | undefined) =>
  v == null ? '—' : new Intl.NumberFormat('uz-UZ').format(v) + ' so\'m'
// "25.06.2026 16:24:54" → "25.06.2026" (vaqtni olib tashlaymiz)
const fmtDate = (v: string | null | undefined) => (v ? v.split(' ')[0] : '—')

// Backend xato xabarini XAVFSIZ stringga aylantiradi. FastAPI `detail` string,
// obyekt yoki massiv (422 validatsiya) bo'lishi mumkin — to'g'ridan-to'g'ri
// `.replace()` yoki JSX' da render qilish sahifani yiqitadi (oq ekran).
const errText = (e: any): string => {
  const d = e?.response?.data?.detail
  if (typeof d === 'string') return d.replace(/^Smartup:\s*/, '')
  if (Array.isArray(d)) return d.map((x: any) => x?.msg || JSON.stringify(x)).join('; ')
  if (d && typeof d === 'object') return d.message || d.detail || JSON.stringify(d)
  return e?.message || ''
}

export default function Smartup() {
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('orders')
  const [whId, setWhId] = useState('')
  const [pulling, setPulling] = useState(false)
  const [showAll, setShowAll] = useState(false)  // false = ochiq buyurtmalar, true = barchasi
  const [orderSearch, setOrderSearch] = useState('')
  const [orderStatus, setOrderStatus] = useState('')

  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const wid = whId || (warehouses as any[])[0]?.id

  const currentOrg = useQuery({ queryKey: ['su-current-org'], queryFn: getSmartupCurrentOrg, staleTime: 300_000, retry: false })

  const orders = useQuery({
    queryKey: ['su-orders', wid, showAll],
    queryFn: () => getShipmentOrders({ warehouse_id: wid, all_statuses: showAll }),
    enabled: !!wid,
  })
  const inputs = useQuery({
    queryKey: ['su-inputs', wid], queryFn: () => getProductionInputs(wid),
    enabled: !!wid,
  })
  const purchases = useQuery({
    queryKey: ['su-purchases', wid], queryFn: () => getPurchases(wid),
    enabled: !!wid,
  })
  const movements = useQuery({
    queryKey: ['su-movements', wid], queryFn: () => getSmartupMovements(wid),
    enabled: !!wid && tab === 'movements',
  })
  const stocktakings = useQuery({
    queryKey: ['su-stocktakings', wid], queryFn: () => getSmartupStocktakings(wid),
    enabled: !!wid && tab === 'stocktaking',
  })
  const writeoffs = useQuery({
    queryKey: ['su-writeoffs', wid], queryFn: () => getSmartupWriteoffs(wid),
    enabled: !!wid && tab === 'writeoffs',
  })
  const returns = useQuery({
    queryKey: ['su-returns', wid], queryFn: () => getSmartupReturns(wid),
    enabled: !!wid && tab === 'writeoffs',
  })
  const erpPolicy = useQuery({ queryKey: ['erp-policy'], queryFn: getErpPolicy })
  const canWriteErp = !!(erpPolicy.data as any)?.can_write
  const recon = useQuery({
    queryKey: ['su-recon', wid], queryFn: () => getSmartupReconciliation(wid),
    enabled: !!wid && tab === 'svereka',
  })

  const refresh = async () => {
    setPulling(true)
    try {
      await pullSmartup()
      await Promise.all([orders.refetch(), purchases.refetch(), inputs.refetch(), recon.refetch()])
      qc.invalidateQueries({ queryKey: ['integration-status'] })
      toast.success('Smartup ma\'lumotlari yangilandi')
    } catch (e: any) {
      toast.error(errText(e) || 'Yangilashda xatolik')
    } finally { setPulling(false) }
  }

  const orderCount = (orders.data as any[])?.length ?? 0
  const purchaseCount = (purchases.data as any)?.count ?? 0
  const inputCount = (inputs.data as any)?.count ?? 0

  const TABS = [
    { id: 'orders', label: 'Buyurtmalar', icon: ArrowUpFromLine, badge: orderCount || undefined },
    { id: 'inputs', label: 'Kirimlar', icon: ArrowDownToLine, badge: (purchaseCount + inputCount) || undefined },
    { id: 'movements', label: "Ko'chirishlar", icon: ArrowLeftRight },
    { id: 'stocktaking', label: 'Inventarizatsiya', icon: ClipboardCheck },
    { id: 'writeoffs', label: 'Spisaniye/Vozvrat', icon: Package },
    { id: 'svereka', label: 'Qoldiq svereka', icon: GitCompareArrows },
  ]

  const org = currentOrg.data as any

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
      <PageHeader
        icon={<Package size={20} />}
        title="Smartup (ERP) ma'lumotlari"
        subtitle="Smartup'dan tortilgan barcha ma'lumot bir joyda"
        actions={
          <>
            <Select value={wid ?? ''} onChange={e => setWhId(e.target.value)} className="w-auto min-w-40">
              {(warehouses as any[]).map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </Select>
            <Button onClick={refresh} loading={pulling} icon={<RefreshCw size={14} className={pulling ? 'animate-spin' : ''} />}>
              {pulling ? 'Yuklanmoqda…' : 'Yangilash'}
            </Button>
          </>
        }
      />

      {/* Ulangan Smartup tashkiloti — Toshkent/Samarqand tasdig'i */}
      <Card padded={false} className="px-4 py-3">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="w-9 h-9 rounded-lg bg-blue-500/10 text-blue-600 flex items-center justify-center shrink-0">
            <Building2 size={17} />
          </div>
          {currentOrg.isLoading ? (
            <span className="text-sm text-slate-400">Ulangan tashkilot aniqlanmoqda…</span>
          ) : org ? (
            <div className="flex items-center gap-x-5 gap-y-1 flex-wrap text-sm">
              <span className="text-slate-500">Ulangan tashkilot:</span>
              <Badge tone="blue" dot>filial_id {org.filial_id_header ?? '—'}</Badge>
              <span className="text-slate-600">filial_code: <b className="text-slate-800">{org.filial_code}</b></span>
              {org.sample_customers?.length > 0 && (
                <span className="text-xs text-slate-400 truncate">
                  Namuna mijoz: {org.sample_customers.slice(0, 3).join(', ')}
                </span>
              )}
            </div>
          ) : (
            <div className="text-sm">
              <span className="text-amber-600 font-medium">Tashkilot aniqlanmadi.</span>
              <span className="text-slate-500"> Smartup xatosi: </span>
              <span className="text-slate-700">{errText(currentOrg.error) || "Smartup vaqtincha ishlamayapti yoki Sozlamalar > Integratsiya'da filial_id/filial_code'ni tekshiring."}</span>
            </div>
          )}
        </div>
      </Card>

      {/* Tablar */}
      <Tabs items={TABS} active={tab} onChange={(id) => setTab(id as Tab)} className="flex-wrap" />

      {tab === 'orders' && (() => {
        const all = (orders.data as any[]) ?? []
        const statusOpts = Array.from(new Set(all.map((o: any) => o.status)))
          .map(s => ({ value: s as string, label: statusBadge(s as string).label }))
        const s = orderSearch.trim().toLowerCase()
        // "dd.mm.yyyy hh:mm:ss" → taqqoslash uchun timestamp (yangi-birinchi saralash)
        const ts = (v: string | null | undefined) => {
          if (!v) return 0
          const [d, t] = v.split(' ')
          const [dd, mm, yy] = (d || '').split('.')
          return new Date(`${yy}-${mm}-${dd}T${t || '00:00:00'}`).getTime() || 0
        }
        const filtered = all.filter((o: any) => {
          if (orderStatus && o.status !== orderStatus) return false
          if (!s) return true
          return [o.customer_name, o.customer_tin, o.order_number, o.deal_id]
            .some(v => String(v ?? '').toLowerCase().includes(s))
        }).sort((a: any, b: any) => ts(b.order_date) - ts(a.order_date))  // yangi-birinchi (Smartup kabi)
        const hasActive = !!orderSearch || !!orderStatus
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5 w-fit text-sm">
              <button onClick={() => setShowAll(false)}
                className={`px-3 py-1 rounded-md transition ${!showAll ? 'bg-white shadow-sm text-slate-800 font-medium' : 'text-slate-500'}`}>
                Ochiq buyurtmalar
              </button>
              <button onClick={() => setShowAll(true)}
                className={`px-3 py-1 rounded-md transition ${showAll ? 'bg-white shadow-sm text-slate-800 font-medium' : 'text-slate-500'}`}>
                Barcha buyurtmalar
              </button>
            </div>
            <FilterBar hasActive={hasActive} onClear={() => { setOrderSearch(''); setOrderStatus('') }}>
              <SearchInput value={orderSearch} onChange={setOrderSearch}
                placeholder="Mijoz / STIR / buyurtma №…" className="w-64" />
              <FilterSelect label="Barcha holatlar" value={orderStatus} onChange={setOrderStatus} options={statusOpts} />
              <span className="text-xs text-slate-400">{filtered.length} / {all.length}</span>
            </FilterBar>
            <p className="text-xs text-slate-400">
              {showAll
                ? 'Barcha buyurtmalar (arxivdan tashqari) — Smartup "Все заказы" bilan mos.'
                : 'Terilishi kerak bo\'lgan ochiq buyurtmalar (Yangi / jarayonda).'}
            </p>
            {showAll && (() => {
              const bvCount = all.filter((o: any) => o.status === 'B#V').length
              return bvCount > 0 ? (
                <div className="flex items-start gap-2 text-xs text-violet-700 bg-violet-500/10 rounded-lg px-3 py-2">
                  <AlertCircle size={14} className="mt-0.5 shrink-0" />
                  <span>
                    Shundan <b>{bvCount} ta «Tasdiqlangan» (B#V)</b> buyurtma. Smartup UI'da bu status uchun
                    alohida karta yo'q — u ularni «Черновик»/«Доставлен»ga bo'lib yuboradi va bir nechtasini
                    umumiy songa qo'shmaydi. Shuning uchun WMS jami Smartup «Все заказы»dan ±bir necha ko'proq
                    bo'lishi mumkin (yo'qolgan buyurtma yo'q — WMS to'liqroq).
                  </span>
                </div>
              ) : null
            })()}
            <OrdersTable rows={filtered} loading={orders.isLoading}
              canWrite={canWriteErp} onChanged={() => orders.refetch()} />
          </div>
        )
      })()}
      {tab === 'inputs' && (
        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Ta'minotchidan xaridlar</h3>
            <PurchasesTable q={purchases} />
          </div>
          {((inputs.data as any)?.count ?? 0) > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">Zavod kirimi</h3>
              <InputsTable q={inputs} />
            </div>
          )}
        </div>
      )}
      {tab === 'movements' && <MovementsTable q={movements} />}
      {tab === 'stocktaking' && <StocktakingsTable q={stocktakings} />}
      {tab === 'writeoffs' && <WriteoffReturnTable wq={writeoffs} rq={returns} />}
      {tab === 'svereka' && <ReconTable q={recon} />}
    </div>
  )
}

function Empty({ loading, text }: { loading: boolean; text: string }) {
  return <div className="py-12 text-center text-slate-400 text-sm">{loading ? 'Yuklanmoqda…' : text}</div>
}

function OrdersTable({ rows, loading, canWrite, onChanged }: {
  rows: any[]; loading: boolean; canWrite?: boolean; onChanged?: () => void
}) {
  const [open, setOpen] = useState<string | null>(null)
  if (!rows.length) return <Empty loading={loading} text="Buyurtma topilmadi" />
  // ERP'ga status yuborish — OGOHLANTIRISH bilan.
  const changeStatus = async (o: any, newStatus: string) => {
    const lbl = statusBadge(newStatus).label
    const ok = window.confirm(
      `⚠️ DIQQAT: bu Smartup'dagi REAL buyurtmani o'zgartiradi.\n\n` +
      `Buyurtma №${o.order_number || o.deal_id} (${o.customer_name || ''})\n` +
      `Yangi holat: ${lbl}\n\nDavom etasizmi?`
    )
    if (!ok) return
    try {
      await pushOrderStatus(o.deal_id, newStatus)
      toast.success(`Smartup'ga yuborildi: ${lbl}`)
      onChanged?.()
    } catch (e: any) {
      toast.error(errText(e) || 'Yuborishda xatolik')
    }
  }
  return (
    <div className="border border-slate-200 rounded-lg overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-slate-500 text-xs">
          <tr>
            <th className="w-8 px-2 py-2"></th>
            <th className="text-left px-3 py-2">Buyurtma №</th>
            <th className="text-left px-3 py-2">Mijoz</th>
            <th className="text-left px-3 py-2">Sana</th>
            <th className="text-right px-3 py-2">Summa</th>
            <th className="text-left px-3 py-2">Holati</th>
            <th className="text-right px-3 py-2">Mahsulot</th>
            {canWrite && <th className="text-right px-3 py-2">ERP amal</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((o: any, i: number) => {
            const b = statusBadge(o.status)
            const id = String(o.deal_id ?? i)
            const isOpen = open === id
            const colspan = canWrite ? 8 : 7
            return (
              <Fragment key={id}>
                <tr onClick={() => setOpen(isOpen ? null : id)}
                  className="border-t border-slate-100 cursor-pointer hover:bg-slate-500/5 transition">
                  <td className="px-2 py-1.5 text-slate-400">
                    {isOpen ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                  </td>
                  <td className="px-3 py-1.5 font-mono text-xs">{o.order_number || o.deal_id}</td>
                  <td className="px-3 py-1.5">
                    <div className="font-medium text-slate-700">{o.customer_name || 'Noma\'lum mijoz'}</div>
                    {o.customer_tin && <div className="text-xs text-slate-400">STIR: {o.customer_tin}</div>}
                  </td>
                  <td className="px-3 py-1.5 text-slate-600">{fmtDate(o.order_date)}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{fmtSum(o.total_amount)}</td>
                  <td className="px-3 py-1.5">
                    <span className={`text-xs rounded px-1.5 py-0.5 ${b.cls}`}>{b.label}</span>
                    {o.with_marking === 'Y' && <span className="ml-1 text-xs rounded px-1.5 py-0.5 bg-teal-100 text-teal-700">markirovka</span>}
                  </td>
                  <td className="px-3 py-1.5 text-right">{o.lines?.length ?? 0} ta</td>
                  {canWrite && (
                    <td className="px-3 py-1.5 text-right" onClick={e => e.stopPropagation()}>
                      <select defaultValue="" onChange={e => { if (e.target.value) { changeStatus(o, e.target.value); e.target.value = '' } }}
                        className="border border-amber-200 text-amber-700 rounded px-1.5 py-0.5 text-xs bg-amber-50">
                        <option value="">Holatni o'zgartirish…</option>
                        <option value="B#S">Jo'natilgan (B#S)</option>
                        <option value="C">Yetkazilgan (C)</option>
                      </select>
                    </td>
                  )}
                </tr>
                {isOpen && (
                  <tr className="bg-slate-500/5">
                    <td colSpan={colspan} className="px-4 py-3">
                      <OrderLines lines={o.lines ?? []} />
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// Buyurtma mahsulot qatorlari (Smartup "Товар" tab kabi) — kod, GTIN, miqdor.
function OrderLines({ lines }: { lines: any[] }) {
  if (!lines.length) return <div className="text-xs text-slate-400">Mahsulot qatori yo'q</div>
  const totalQty = lines.reduce((s, l) => s + (Number(l.qty_ordered) || 0), 0)
  return (
    <div>
      <div className="text-xs font-semibold text-slate-500 mb-2 flex items-center gap-1.5">
        <Boxes size={13} className="text-blue-500" /> Buyurtma mahsulotlari ({lines.length} pozitsiya)
      </div>
      <div className="rounded-lg border border-slate-200 overflow-x-auto bg-white">
        <table className="w-full text-xs">
          <thead className="bg-slate-50 text-slate-400">
            <tr>
              <th className="text-left px-3 py-1.5">Kod (ТМЦ)</th>
              <th className="text-left px-3 py-1.5">Nomi</th>
              <th className="text-left px-3 py-1.5">GTIN</th>
              <th className="text-right px-3 py-1.5">Miqdor</th>
              <th className="text-left px-3 py-1.5">Birlik</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((l: any, i: number) => (
              <tr key={i} className="border-t border-slate-100">
                <td className="px-3 py-1.5 font-mono">{l.product_code || '—'}</td>
                <td className="px-3 py-1.5 text-slate-700">{l.product_name || <span className="text-slate-300">nomsiz (WMS'da mapping yo'q)</span>}</td>
                <td className="px-3 py-1.5 font-mono text-slate-500">
                  {l.gtin ? <span className="inline-flex items-center gap-1"><Barcode size={12} className="text-slate-400" />{l.gtin}</span> : '—'}
                </td>
                <td className="px-3 py-1.5 text-right tabular-nums font-medium">{l.qty_ordered ?? 0}</td>
                <td className="px-3 py-1.5 text-slate-500 uppercase">{l.uom || 'unit'}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-slate-200 bg-slate-50 font-medium text-slate-600">
              <td className="px-3 py-1.5" colSpan={3}>Jami</td>
              <td className="px-3 py-1.5 text-right tabular-nums">{totalQty}</td>
              <td className="px-3 py-1.5"></td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="text-[11px] text-slate-400 mt-1.5">
        GTIN — TSD terish (FIFO/FEFO) va Asl Belgisi kod solishtirish uchun ishlatiladi.
      </p>
    </div>
  )
}

// Ta'minotchidan xaridlar (purchase$export) — distributor uchun asosiy kirim.
const PURCHASE_STATUS: Record<string, { label: string; cls: string }> = {
  'A': { label: 'Faol', cls: 'bg-emerald-100 text-emerald-700' },
  'C': { label: 'Yakunlangan', cls: 'bg-rose-100 text-rose-700' },
  'D': { label: 'Qoralama', cls: 'bg-slate-100 text-slate-600' },
}
// Kirim/xarid qatorlari (item detali) — ochilgan hujjat ostida ko'rsatiladi.
function ReceiptItems({ items, colSpan }: { items: any[]; colSpan: number }) {
  const nf = (v: number | null | undefined) => (v == null ? '—' : new Intl.NumberFormat('uz-UZ').format(v))
  if (!items?.length) return (
    <tr><td colSpan={colSpan} className="px-8 py-2 text-xs text-slate-400 bg-slate-50/60">Qatorlar yo'q</td></tr>
  )
  return (
    <tr>
      <td colSpan={colSpan} className="px-3 py-2 bg-slate-50/60">
        <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
          <table className="w-full text-xs">
            <thead className="text-slate-400">
              <tr>
                <th className="text-left px-2 py-1.5">Kod</th>
                <th className="text-left px-2 py-1.5">Nomi</th>
                <th className="text-left px-2 py-1.5">GTIN</th>
                <th className="text-right px-2 py-1.5">Miqdor</th>
                <th className="text-left px-2 py-1.5">O'lch.</th>
                <th className="text-right px-2 py-1.5">Narx</th>
                <th className="text-right px-2 py-1.5">Summa</th>
                <th className="text-left px-2 py-1.5">Partiya</th>
                <th className="text-left px-2 py-1.5">I.ch. sana</th>
                <th className="text-left px-2 py-1.5">Muddati</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it: any, j: number) => (
                <tr key={j} className="border-t border-slate-100">
                  <td className="px-2 py-1 font-mono">{it.product_code || '—'}</td>
                  <td className="px-2 py-1">{it.product_name || '—'}</td>
                  <td className="px-2 py-1 font-mono text-slate-500">{it.gtin || '—'}</td>
                  <td className="px-2 py-1 text-right">{nf(it.quantity)}</td>
                  <td className="px-2 py-1 text-slate-500">{it.uom || '—'}</td>
                  <td className="px-2 py-1 text-right">{nf(it.price)}</td>
                  <td className="px-2 py-1 text-right">{nf(it.total)}</td>
                  <td className="px-2 py-1">{it.series_number || '—'}</td>
                  <td className="px-2 py-1 text-slate-500">{fmtDate(it.production_date)}</td>
                  <td className="px-2 py-1 text-slate-500">{fmtDate(it.expiry_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </td>
    </tr>
  )
}

function PurchasesTable({ q }: { q: any }) {
  const rows = (q.data as any)?.purchases ?? []
  const [open, setOpen] = useState<Record<number, boolean>>({})
  if (!rows.length) return <Empty loading={q.isLoading} text="Ta'minotchidan xarid yo'q (oxirgi 7 kun)" />
  return (
    <div className="border border-slate-200 rounded-lg overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-slate-500 text-xs">
          <tr>
            <th className="w-8 px-2 py-2"></th>
            <th className="text-left px-3 py-2">Xarid №</th>
            <th className="text-left px-3 py-2">Ta'minotchi</th>
            <th className="text-left px-3 py-2">Sana</th>
            <th className="text-left px-3 py-2">Schyot-faktura</th>
            <th className="text-left px-3 py-2">Sklad</th>
            <th className="text-left px-3 py-2">Holati</th>
            <th className="text-right px-3 py-2">Summa</th>
            <th className="text-right px-3 py-2">Mahsulot</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p: any, i: number) => {
            const b = PURCHASE_STATUS[p.status_code] ?? { label: p.status_code || '—', cls: 'bg-slate-100 text-slate-600' }
            const isOpen = !!open[i]
            return (
              <Fragment key={i}>
                <tr className="border-t border-slate-100 hover:bg-slate-50/60 cursor-pointer"
                  onClick={() => setOpen(o => ({ ...o, [i]: !o[i] }))}>
                  <td className="px-2 py-1.5 text-slate-400">
                    {(p.items?.length ?? 0) > 0 && (isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />)}
                  </td>
                  <td className="px-3 py-1.5 font-mono text-xs">{p.purchase_number || p.purchase_id}</td>
                  <td className="px-3 py-1.5">{p.supplier_name || p.supplier_code || '—'}</td>
                  <td className="px-3 py-1.5 text-slate-600">{fmtDate(p.date)}</td>
                  <td className="px-3 py-1.5 text-slate-500">{p.invoice_number || '—'}</td>
                  <td className="px-3 py-1.5 text-slate-500">{p.warehouse_name || p.warehouse_code || '—'}</td>
                  <td className="px-3 py-1.5"><span className={`text-xs rounded px-1.5 py-0.5 ${b.cls}`}>{b.label}</span></td>
                  <td className="px-3 py-1.5 text-right">{fmtSum(p.total)}</td>
                  <td className="px-3 py-1.5 text-right">{p.lines ?? 0} ta</td>
                </tr>
                {isOpen && <ReceiptItems items={p.items} colSpan={9} />}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function MovementsTable({ q }: { q: any }) {
  const internal = (q.data as any)?.internal ?? []
  const cross = (q.data as any)?.cross_org ?? []
  const rows = [
    ...internal.map((m: any) => ({ ...m, _kind: 'Ichki' })),
    ...cross.map((m: any) => ({ ...m, _kind: 'Tashkilotlararo' })),
  ]
  if (!rows.length) return <Empty loading={q.isLoading} text="Ko'chirish yo'q (oxirgi 7 kun)" />
  return (
    <div className="border border-slate-200 rounded-lg overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-slate-500 text-xs">
          <tr>
            <th className="text-left px-3 py-2">№</th>
            <th className="text-left px-3 py-2">Turi</th>
            <th className="text-left px-3 py-2">Qayerdan</th>
            <th className="text-left px-3 py-2">Qayerga</th>
            <th className="text-left px-3 py-2">Sana</th>
            <th className="text-left px-3 py-2">Holat</th>
            <th className="text-right px-3 py-2">Mahsulot</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((m: any, i: number) => (
            <tr key={i} className="border-t border-slate-100">
              <td className="px-3 py-1.5 font-mono text-xs">{m.movement_number || m.movement_id}</td>
              <td className="px-3 py-1.5">{m._kind}</td>
              <td className="px-3 py-1.5">{m.from_warehouse_code || '—'}</td>
              <td className="px-3 py-1.5">{m.to_warehouse_code || '—'}</td>
              <td className="px-3 py-1.5 text-slate-600">{(m.from_movement_date || '').split(' ')[0] || '—'}</td>
              <td className="px-3 py-1.5"><span className="text-xs bg-slate-100 text-slate-600 rounded px-1.5 py-0.5">{m.status || '—'}</span></td>
              <td className="px-3 py-1.5 text-right">{m.movement_items?.length ?? 0} ta</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MiniDocTable({ title, rows, numKey, dateKey, loading }: {
  title: string; rows: any[]; numKey: string; dateKey: string; loading: boolean
}) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700 mb-2">{title} <span className="text-slate-400 font-normal">({rows.length})</span></h3>
      {!rows.length ? <Empty loading={loading} text="Ma'lumot yo'q (oxirgi 7 kun)" /> : (
        <div className="border border-slate-200 rounded-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs">
              <tr><th className="text-left px-3 py-2">№</th><th className="text-left px-3 py-2">Sana</th>
                <th className="text-left px-3 py-2">Holat</th><th className="text-right px-3 py-2">Pozitsiya</th></tr>
            </thead>
            <tbody>
              {rows.map((r: any, i: number) => {
                const items = r.writeoff_items || r.return_items || r.return || []
                return (
                  <tr key={i} className="border-t border-slate-100">
                    <td className="px-3 py-1.5 font-mono text-xs">{r[numKey] || r.external_id || '—'}</td>
                    <td className="px-3 py-1.5 text-slate-600">{String(r[dateKey] || '').split(' ')[0] || '—'}</td>
                    <td className="px-3 py-1.5"><span className="text-xs bg-slate-100 text-slate-600 rounded px-1.5 py-0.5">{r.status || '—'}</span></td>
                    <td className="px-3 py-1.5 text-right">{Array.isArray(items) ? items.length : 0} ta</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function WriteoffReturnTable({ wq, rq }: { wq: any; rq: any }) {
  const writeoffs = (wq.data as any)?.writeoffs ?? []
  const sale = (rq.data as any)?.sale ?? []
  const supplier = (rq.data as any)?.supplier ?? []
  return (
    <div className="space-y-4">
      <MiniDocTable title="Spisaniye (hisobdan chiqarish)" rows={writeoffs} numKey="writeoff_number" dateKey="writeoff_date" loading={wq.isLoading} />
      <MiniDocTable title="Mijozdan qaytarish" rows={sale} numKey="return_number" dateKey="return_time" loading={rq.isLoading} />
      <MiniDocTable title="Ta'minotchiga qaytarish" rows={supplier} numKey="return_number" dateKey="return_time" loading={rq.isLoading} />
    </div>
  )
}

function StocktakingsTable({ q }: { q: any }) {
  const rows = (q.data as any)?.stocktakings ?? []
  if (!rows.length) return <Empty loading={q.isLoading} text="Inventarizatsiya yo'q (oxirgi 7 kun)" />
  return (
    <div className="border border-slate-200 rounded-lg overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-slate-500 text-xs">
          <tr>
            <th className="text-left px-3 py-2">№</th>
            <th className="text-left px-3 py-2">Sklad</th>
            <th className="text-left px-3 py-2">Sana</th>
            <th className="text-left px-3 py-2">Holat</th>
            <th className="text-right px-3 py-2">Pozitsiya</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s: any, i: number) => (
            <tr key={i} className="border-t border-slate-100">
              <td className="px-3 py-1.5 font-mono text-xs">{s.stocktaking_number || s.stocktaking_id}</td>
              <td className="px-3 py-1.5">{s.warehouse_code || '—'}</td>
              <td className="px-3 py-1.5 text-slate-600">{(s.stocktaking_date || '').split(' ')[0] || '—'}</td>
              <td className="px-3 py-1.5"><span className="text-xs bg-slate-100 text-slate-600 rounded px-1.5 py-0.5">{s.status || '—'}</span></td>
              <td className="px-3 py-1.5 text-right">{s.stocktaking_items?.length ?? 0} ta</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function InputsTable({ q }: { q: any }) {
  const rows = (q.data as any)?.inputs ?? []
  const [open, setOpen] = useState<Record<number, boolean>>({})
  if (!rows.length) return <Empty loading={q.isLoading} text="Smartup kirimlari yo'q" />
  return (
    <div className="border border-slate-200 rounded-lg overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-slate-500 text-xs">
          <tr>
            <th className="w-8 px-2 py-2"></th>
            <th className="text-left px-3 py-2">Kirim №</th>
            <th className="text-left px-3 py-2">Sana</th>
            <th className="text-left px-3 py-2">Sklad</th>
            <th className="text-left px-3 py-2">Holati</th>
            <th className="text-right px-3 py-2">Summa</th>
            <th className="text-right px-3 py-2">Qatorlar</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((inp: any, i: number) => {
            const isOpen = !!open[i]
            return (
              <Fragment key={i}>
                <tr className="border-t border-slate-100 hover:bg-slate-50/60 cursor-pointer"
                  onClick={() => setOpen(o => ({ ...o, [i]: !o[i] }))}>
                  <td className="px-2 py-1.5 text-slate-400">
                    {(inp.items?.length ?? 0) > 0 && (isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />)}
                  </td>
                  <td className="px-3 py-1.5 font-mono text-xs">{inp.input_number || inp.input_id}</td>
                  <td className="px-3 py-1.5">{fmtDate(inp.date)}</td>
                  <td className="px-3 py-1.5">{inp.warehouse_name || inp.warehouse_code || '—'}</td>
                  <td className="px-3 py-1.5"><span className="text-xs bg-slate-100 text-slate-600 rounded px-1.5 py-0.5">{inp.status_code || '—'}</span></td>
                  <td className="px-3 py-1.5 text-right">{fmtSum(inp.total)}</td>
                  <td className="px-3 py-1.5 text-right">{inp.lines ?? 0} ta</td>
                </tr>
                {isOpen && <ReceiptItems items={inp.items} colSpan={7} />}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

const DIR: Record<string, { label: string; cls: string }> = {
  match: { label: 'Mos', cls: 'text-green-600' },
  wms_more: { label: 'WMS ko‘p', cls: 'text-amber-600' },
  erp_more: { label: 'ERP ko‘p', cls: 'text-purple-600' },
  missing: { label: 'Faqat bitta', cls: 'text-slate-500' },
}

function ReconTable({ q }: { q: any }) {
  const data = q.data
  const rows = data?.lines ?? []
  const t = data?.totals
  const nf = (v: number | null | undefined) => (v == null ? '—' : new Intl.NumberFormat('uz-UZ').format(v))
  return (
    <div className="space-y-4">
      {/* Umumiy koʻlichestvo + nomenklatura */}
      {t && (
        <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard title="Smartup — umumiy birlik" value={nf(t.smartup_total_units)} sub="ERP qoldig'i" icon={Boxes} accent="blue" />
          <StatCard title="Smartup — nomenklatura" value={nf(t.smartup_nomenclature)} sub="turdagi mahsulot" icon={Layers} accent="purple" />
          <StatCard title="WMS — umumiy birlik" value={nf(t.wms_total_units)} sub="jismoniy qoldiq" icon={Boxes} accent="green" />
          <StatCard title="WMS — nomenklatura" value={nf(t.wms_nomenclature)} sub="turdagi mahsulot" icon={Layers} accent="teal" />
        </motion.div>
      )}
      {data && !data.erp_compared && (
        <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-500/10 rounded-lg px-3 py-2">
          <AlertCircle size={14} /> ERP bilan solishtirilmadi: {data.erp_error || 'sklad kodi yo‘q'}
        </div>
      )}
      {data?.summary && (
        <div className="flex flex-wrap gap-2">
          <Badge tone="green"><CheckCircle2 size={12} /> Mos: {data.summary.match}</Badge>
          <Badge tone="red">Farqli: {data.summary.mismatch}</Badge>
          <Badge tone="blue">Faqat WMS: {data.summary.only_wms}</Badge>
          <Badge tone="purple">Faqat ERP: {data.summary.only_erp}</Badge>
        </div>
      )}
      <div className="border border-slate-200 rounded-lg overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs">
            <tr>
              <th className="text-left px-3 py-2">Mahsulot kodi</th>
              <th className="text-left px-3 py-2">Nomi</th>
              <th className="text-right px-3 py-2">WMS</th>
              <th className="text-right px-3 py-2">Smartup</th>
              <th className="text-right px-3 py-2">Farq</th>
              <th className="text-left px-3 py-2">Holat</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((ln: any, i: number) => {
              const d = DIR[ln.direction] ?? DIR.missing
              return (
                <tr key={i} className="border-t border-slate-100">
                  <td className="px-3 py-1.5 font-mono text-xs">{ln.product_code ?? '—'}</td>
                  <td className="px-3 py-1.5">{ln.product_name ?? '—'}</td>
                  <td className="px-3 py-1.5 text-right">{ln.wms_qty}</td>
                  <td className="px-3 py-1.5 text-right">{ln.smartup_qty ?? '—'}</td>
                  <td className={`px-3 py-1.5 text-right font-medium ${ln.diff === 0 ? 'text-slate-400' : ln.diff > 0 ? 'text-amber-600' : 'text-purple-600'}`}>{ln.diff > 0 ? `+${ln.diff}` : ln.diff}</td>
                  <td className={`px-3 py-1.5 text-xs ${d.cls}`}>{d.label}</td>
                </tr>
              )
            })}
            {!rows.length && (
              <tr><td colSpan={6}><Empty loading={q.isLoading} text="Ma'lumot yo'q" /></td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
