import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getWarehouses,
  getProducts,
  getAllLocations,
  createMovement,
  createInventoryCount,
  createWriteoff,
  createReturn,
  getReconciliation,
  exportStockCsv,
  exportReconciliationCsv,
} from '../lib/api'
import {
  ArrowLeftRight,
  ClipboardCheck,
  Trash2,
  Undo2,
  Scale,
  Download,
  ClipboardList,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader, Card, CardHeader, Button, Select, FormField, Input, Badge, EmptyState, Tabs } from '../components/ui'
import type { TabItem } from '../components/ui'

type TabKey = 'movement' | 'inventory' | 'writeoff' | 'return' | 'reconciliation'

const TABS: (TabItem & { key: TabKey })[] = [
  { key: 'movement', id: 'movement', label: "Ko'chirish", icon: ArrowLeftRight },
  { key: 'inventory', id: 'inventory', label: 'Inventarizatsiya', icon: ClipboardCheck },
  { key: 'writeoff', id: 'writeoff', label: 'Hisobdan chiqarish', icon: Trash2 },
  { key: 'return', id: 'return', label: 'Qaytarish', icon: Undo2 },
  { key: 'reconciliation', id: 'reconciliation', label: 'Solishtirish', icon: Scale },
]

export default function Operations({ embedded }: { embedded?: boolean }) {
  const qc = useQueryClient()
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [whId, setWhId] = useState<string>('')
  const wid = whId || warehouses[0]?.id
  const [tab, setTab] = useState<TabKey>('movement')

  const { data: products = [] } = useQuery({ queryKey: ['products'], queryFn: getProducts })
  const { data: locations = [] } = useQuery({
    queryKey: ['all-locations', wid],
    queryFn: () => getAllLocations(wid),
    enabled: !!wid,
  })

  const onMutError = (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik yuz berdi')
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['stock'] })
    qc.invalidateQueries({ queryKey: ['reconciliation'] })
  }

  if (!wid) {
    return (
      <div className={embedded ? 'p-4 space-y-4' : 'p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto'}>
        <Card className="min-h-[300px] flex items-center justify-center">
          <EmptyState
            icon={ClipboardList}
            title="Sklad mavjud emas yoki tanlanmagan"
          />
        </Card>
      </div>
    )
  }

  return (
    <div className={embedded ? 'p-4 space-y-4' : 'p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto'}>
      {embedded ? (
        <div className="flex items-center justify-between flex-wrap gap-3">
          <p className="text-xs text-slate-400">Ko'chirish, inventarizatsiya, hisobdan chiqarish, qaytarish</p>
          <div className="flex items-center gap-2">
            <Select value={wid} onChange={e => setWhId(e.target.value)} className="w-auto min-w-40">
              {warehouses.map((wh: any) => (
                <option key={wh.id} value={wh.id}>{wh.name}</option>
              ))}
            </Select>
            <Button
              variant="secondary"
              onClick={() => wid && exportStockCsv(wid)}
              icon={<Download size={14} />}
            >
              Qoldiqlar CSV
            </Button>
          </div>
        </div>
      ) : (
        <PageHeader
          icon={<ClipboardList size={20} />}
          title="Operatsiyalar"
          subtitle="Ko'chirish, inventarizatsiya, hisobdan chiqarish, qaytarish"
          actions={
            <>
              <Select value={wid} onChange={e => setWhId(e.target.value)} className="w-auto min-w-40">
                {warehouses.map((wh: any) => (
                  <option key={wh.id} value={wh.id}>{wh.name}</option>
                ))}
              </Select>
              <Button
                variant="secondary"
                onClick={() => wid && exportStockCsv(wid)}
                icon={<Download size={14} />}
              >
                Qoldiqlar CSV
              </Button>
            </>
          }
        />
      )}

      {/* Tabs */}
      <Tabs
        items={TABS}
        active={tab}
        onChange={id => setTab(id as TabKey)}
        className="overflow-x-auto max-w-full"
      />

      {tab === 'movement' && (
        <MovementForm
          wid={wid}
          products={products}
          locations={locations}
          onDone={invalidate}
          onError={onMutError}
        />
      )}
      {tab === 'inventory' && (
        <InventoryForm
          wid={wid}
          products={products}
          locations={locations}
          onDone={invalidate}
          onError={onMutError}
        />
      )}
      {tab === 'writeoff' && (
        <WriteoffForm
          wid={wid}
          products={products}
          locations={locations}
          onDone={invalidate}
          onError={onMutError}
        />
      )}
      {tab === 'return' && (
        <ReturnForm
          wid={wid}
          products={products}
          locations={locations}
          onDone={invalidate}
          onError={onMutError}
        />
      )}
      {tab === 'reconciliation' && <ReconciliationView wid={wid} products={products} />}
    </div>
  )
}

// ── Shared sub-components ──────────────────────────────────────────────────────
interface FormProps {
  wid: string
  products: any[]
  locations: any[]
  onDone: () => void
  onError: (e: any) => void
}

function ProductSelect({ products, value, onChange }: { products: any[]; value: string; onChange: (v: string) => void }) {
  return (
    <Select value={value} onChange={e => onChange(e.target.value)}>
      <option value="">— Mahsulot tanlang —</option>
      {products.map((p: any) => (
        <option key={p.id} value={p.id}>
          {p.name?.ru ?? p.name?.uz ?? p.code ?? p.id}
        </option>
      ))}
    </Select>
  )
}

function LocationSelect({
  locations,
  value,
  onChange,
  placeholder,
}: {
  locations: any[]
  value: string
  onChange: (v: string) => void
  placeholder: string
}) {
  return (
    <Select value={value} onChange={e => onChange(e.target.value)}>
      <option value="">{placeholder}</option>
      {locations.map((l: any) => (
        <option key={l.id} value={l.id}>{l.code ?? l.id}</option>
      ))}
    </Select>
  )
}

function FormCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="max-w-2xl">
      <CardHeader title={title} />
      <div className="space-y-4">{children}</div>
    </Card>
  )
}

function SubmitButton({ pending, label }: { pending: boolean; label: string }) {
  return (
    <Button type="submit" loading={pending} disabled={pending}>
      {label}
    </Button>
  )
}

// ── Movement ───────────────────────────────────────────────────────────────────
function MovementForm({ wid, products, locations, onDone, onError }: FormProps) {
  const [productId, setProductId] = useState('')
  const [fromLoc, setFromLoc] = useState('')
  const [toLoc, setToLoc] = useState('')
  const [qty, setQty] = useState(1)
  const [markingCode, setMarkingCode] = useState('')

  const mut = useMutation({
    mutationFn: () =>
      createMovement({
        warehouse_id: wid,
        product_id: productId,
        from_location_id: fromLoc,
        to_location_id: toLoc,
        qty,
        marking_code: markingCode || undefined,
      }),
    onSuccess: () => {
      toast.success("Ko'chirish bajarildi")
      setQty(1)
      setMarkingCode('')
      onDone()
    },
    onError,
  })

  return (
    <FormCard title="Mahsulotni ko'chirish">
      <form
        className="space-y-4"
        onSubmit={e => {
          e.preventDefault()
          if (!productId || !fromLoc || !toLoc) return toast.error("Mahsulot va lokatsiyalarni tanlang")
          if (fromLoc === toLoc) return toast.error("Manba va manzil bir xil bo'lmasin")
          mut.mutate()
        }}
      >
        <FormField label="Mahsulot">
          <ProductSelect products={products} value={productId} onChange={setProductId} />
        </FormField>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Qayerdan">
            <LocationSelect locations={locations} value={fromLoc} onChange={setFromLoc} placeholder="— Manba —" />
          </FormField>
          <FormField label="Qayerga">
            <LocationSelect locations={locations} value={toLoc} onChange={setToLoc} placeholder="— Manzil —" />
          </FormField>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Miqdor">
            <Input type="number" min={1} value={qty} onChange={e => setQty(Number(e.target.value))} />
          </FormField>
          <FormField label="Markirovka kodi (ixtiyoriy)">
            <Input type="text" value={markingCode} onChange={e => setMarkingCode(e.target.value)} />
          </FormField>
        </div>
        <SubmitButton pending={mut.isPending} label="Ko'chirish" />
      </form>
    </FormCard>
  )
}

// ── Inventory count ─────────────────────────────────────────────────────────────
function InventoryForm({ wid, products, locations, onDone, onError }: FormProps) {
  const [productId, setProductId] = useState('')
  const [locId, setLocId] = useState('')
  const [countedQty, setCountedQty] = useState(0)
  const [note, setNote] = useState('')

  const mut = useMutation({
    mutationFn: () =>
      createInventoryCount({
        warehouse_id: wid,
        product_id: productId,
        location_id: locId,
        counted_qty: countedQty,
        note: note || undefined,
      }),
    onSuccess: () => {
      toast.success('Inventarizatsiya yozildi')
      setNote('')
      onDone()
    },
    onError,
  })

  return (
    <FormCard title="Inventarizatsiya (sanab chiqish)">
      <form
        className="space-y-4"
        onSubmit={e => {
          e.preventDefault()
          if (!productId || !locId) return toast.error('Mahsulot va lokatsiyani tanlang')
          mut.mutate()
        }}
      >
        <FormField label="Mahsulot">
          <ProductSelect products={products} value={productId} onChange={setProductId} />
        </FormField>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Lokatsiya">
            <LocationSelect locations={locations} value={locId} onChange={setLocId} placeholder="— Lokatsiya —" />
          </FormField>
          <FormField label="Sanalgan miqdor">
            <Input
              type="number"
              min={0}
              value={countedQty}
              onChange={e => setCountedQty(Number(e.target.value))}
            />
          </FormField>
        </div>
        <FormField label="Izoh (ixtiyoriy)">
          <Input type="text" value={note} onChange={e => setNote(e.target.value)} />
        </FormField>
        <SubmitButton pending={mut.isPending} label="Saqlash" />
      </form>
    </FormCard>
  )
}

// ── Write-off ───────────────────────────────────────────────────────────────────
const WRITEOFF_REASONS = [
  { v: 'damage', l: 'Shikastlanish' },
  { v: 'expiry', l: "Muddati o'tgan" },
  { v: 'loss', l: "Yo'qotish" },
  { v: 'other', l: 'Boshqa' },
]

function WriteoffForm({ wid, products, locations, onDone, onError }: FormProps) {
  const [productId, setProductId] = useState('')
  const [locId, setLocId] = useState('')
  const [qty, setQty] = useState(1)
  const [reason, setReason] = useState('damage')
  const [markingCode, setMarkingCode] = useState('')

  const mut = useMutation({
    mutationFn: () =>
      createWriteoff({
        warehouse_id: wid,
        product_id: productId,
        location_id: locId,
        qty,
        reason,
        marking_code: markingCode || undefined,
      }),
    onSuccess: () => {
      toast.success('Hisobdan chiqarildi')
      setQty(1)
      setMarkingCode('')
      onDone()
    },
    onError,
  })

  return (
    <FormCard title="Hisobdan chiqarish (writeoff)">
      <form
        className="space-y-4"
        onSubmit={e => {
          e.preventDefault()
          if (!productId || !locId) return toast.error('Mahsulot va lokatsiyani tanlang')
          mut.mutate()
        }}
      >
        <FormField label="Mahsulot">
          <ProductSelect products={products} value={productId} onChange={setProductId} />
        </FormField>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Lokatsiya">
            <LocationSelect locations={locations} value={locId} onChange={setLocId} placeholder="— Lokatsiya —" />
          </FormField>
          <FormField label="Miqdor">
            <Input type="number" min={1} value={qty} onChange={e => setQty(Number(e.target.value))} />
          </FormField>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Sabab">
            <Select value={reason} onChange={e => setReason(e.target.value)}>
              {WRITEOFF_REASONS.map(r => (
                <option key={r.v} value={r.v}>{r.l}</option>
              ))}
            </Select>
          </FormField>
          <FormField label="Markirovka kodi (ixtiyoriy)">
            <Input type="text" value={markingCode} onChange={e => setMarkingCode(e.target.value)} />
          </FormField>
        </div>
        <SubmitButton pending={mut.isPending} label="Hisobdan chiqarish" />
      </form>
    </FormCard>
  )
}

// ── Return ──────────────────────────────────────────────────────────────────────
function ReturnForm({ wid, products, locations, onDone, onError }: FormProps) {
  const [productId, setProductId] = useState('')
  const [toLoc, setToLoc] = useState('')
  const [qty, setQty] = useState(1)
  const [dealId, setDealId] = useState('')
  const [markingCode, setMarkingCode] = useState('')

  const mut = useMutation({
    mutationFn: () =>
      createReturn({
        warehouse_id: wid,
        product_id: productId,
        to_location_id: toLoc,
        qty,
        smartup_deal_id: dealId || undefined,
        marking_code: markingCode || undefined,
      }),
    onSuccess: () => {
      toast.success('Qaytarish qabul qilindi')
      setQty(1)
      setMarkingCode('')
      onDone()
    },
    onError,
  })

  return (
    <FormCard title="Qaytarish (return)">
      <form
        className="space-y-4"
        onSubmit={e => {
          e.preventDefault()
          if (!productId || !toLoc) return toast.error('Mahsulot va lokatsiyani tanlang')
          mut.mutate()
        }}
      >
        <FormField label="Mahsulot">
          <ProductSelect products={products} value={productId} onChange={setProductId} />
        </FormField>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Qabul lokatsiyasi">
            <LocationSelect locations={locations} value={toLoc} onChange={setToLoc} placeholder="— Lokatsiya —" />
          </FormField>
          <FormField label="Miqdor">
            <Input type="number" min={1} value={qty} onChange={e => setQty(Number(e.target.value))} />
          </FormField>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Smartup Deal ID (ixtiyoriy)">
            <Input type="text" value={dealId} onChange={e => setDealId(e.target.value)} />
          </FormField>
          <FormField label="Markirovka kodi (ixtiyoriy)">
            <Input type="text" value={markingCode} onChange={e => setMarkingCode(e.target.value)} />
          </FormField>
        </div>
        <SubmitButton pending={mut.isPending} label="Qaytarishni qabul qilish" />
      </form>
    </FormCard>
  )
}

// ── Reconciliation ──────────────────────────────────────────────────────────────
function ReconciliationView({ wid, products }: { wid: string; products: any[] }) {
  const prodMap: Record<string, any> = Object.fromEntries(products.map((p: any) => [p.id, p]))
  const { data: report = [], isLoading } = useQuery({
    queryKey: ['reconciliation', wid],
    queryFn: () => getReconciliation(wid),
    enabled: !!wid,
  })

  const rows: any[] = Array.isArray(report) ? report : report.rows ?? []

  return (
    <Card padded={false} className="overflow-hidden">
      <CardHeader
        icon={<Scale size={16} className="text-blue-500" />}
        title="WMS ↔ Smartup solishtirish"
        action={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => wid && exportReconciliationCsv(wid)}
            icon={<Download size={14} />}
          >
            CSV yuklab olish
          </Button>
        }
        className="p-5 pb-3"
      />

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200/70 text-slate-400 text-xs uppercase">
            <th className="text-left px-4 py-3">Mahsulot</th>
            <th className="text-right px-4 py-3">WMS qoldiq</th>
            <th className="text-right px-4 py-3">Smartup qoldiq</th>
            <th className="text-right px-4 py-3">Farq</th>
            <th className="text-left px-4 py-3">Holat</th>
          </tr>
        </thead>
        <tbody>
          {isLoading && (
            <tr><td colSpan={5} className="text-center py-8 text-slate-400">Yuklanmoqda...</td></tr>
          )}
          {!isLoading && rows.length === 0 && (
            <tr><td colSpan={5} className="text-center py-8 text-slate-400">Ma'lumot yo'q</td></tr>
          )}
          {rows.map((r: any, i: number) => {
            const wmsQty = r.wms_qty ?? r.wms ?? 0
            const erpQty = r.smartup_qty ?? r.erp_qty ?? r.smartup ?? 0
            const diff = r.diff ?? wmsQty - erpQty
            const match = diff === 0
            const prod = prodMap[r.product_id]
            const name =
              r.product_name ?? prod?.name?.ru ?? prod?.name?.uz ?? r.product_code ?? r.product_id
            return (
              <tr
                key={r.product_id ?? i}
                className={`border-b border-slate-100 ${match ? '' : 'bg-rose-500/5'}`}
              >
                <td className="px-4 py-3 text-slate-700 font-medium">{name}</td>
                <td className="px-4 py-3 text-right text-slate-600">{wmsQty}</td>
                <td className="px-4 py-3 text-right text-slate-600">{erpQty}</td>
                <td className={`px-4 py-3 text-right font-medium ${match ? 'text-slate-400' : diff > 0 ? 'text-amber-600' : 'text-rose-600'}`}>
                  {diff > 0 ? `+${diff}` : diff}
                </td>
                <td className="px-4 py-3">
                  <Badge tone={match ? 'green' : 'red'}>
                    {match ? 'Mos' : 'Farq bor'}
                  </Badge>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </Card>
  )
}
