import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { getWarehouses, getKpi, getExpiryAlerts, createWarehouse, deleteWarehouse } from '../lib/api'
import { useAuthStore } from '../store/auth'
import {
  Package, Warehouse, TrendingUp, AlertTriangle,
  ArrowDown, ArrowUp, Box, ChevronRight, Plus, Trash2, X,
} from 'lucide-react'
import { staggerContainer } from '../lib/motion'
import { Card, CardHeader, StatCard, Badge, EmptyState, PageHeader, Button, FormField, Input } from '../components/ui'

export default function Dashboard() {
  const { selectedWarehouseId, setWarehouse } = useAuthStore()
  const nav = useNavigate()
  const qc = useQueryClient()
  const [addOpen, setAddOpen] = useState(false)

  const { data: warehouses = [] } = useQuery({
    queryKey: ['warehouses'],
    queryFn: getWarehouses,
    staleTime: 60_000,
  })

  const removeWarehouse = async (wh: any, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!window.confirm(`"${wh.name}" skladini o'chirasizmi? Bu amalni qaytarib bo'lmaydi.`)) return
    try {
      await deleteWarehouse(wh.id)
      if (wh.id === selectedWarehouseId) setWarehouse('')
      await qc.invalidateQueries({ queryKey: ['warehouses'] })
      toast.success('Sklad o\'chirildi')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'O\'chirishda xatolik')
    }
  }

  useEffect(() => {
    if (!selectedWarehouseId && (warehouses as any[]).length > 0) {
      setWarehouse((warehouses as any[])[0].id)
    }
  }, [warehouses, selectedWarehouseId, setWarehouse])

  const activeWh = (warehouses as any[]).find((w: any) => w.id === selectedWarehouseId)

  const { data: kpi } = useQuery({
    queryKey: ['kpi', selectedWarehouseId],
    queryFn: () => getKpi(selectedWarehouseId!),
    enabled: !!selectedWarehouseId,
    refetchInterval: 30_000,
  })

  const { data: alerts = [] } = useQuery({
    queryKey: ['expiry', selectedWarehouseId],
    queryFn: () => getExpiryAlerts(selectedWarehouseId!),
    enabled: !!selectedWarehouseId,
    refetchInterval: 60_000,
  })

  return (
    <div className="p-4 lg:p-6 space-y-5 max-w-[1600px] mx-auto">
      <PageHeader
        icon={<Warehouse size={20} />}
        title="Boshqaruv paneli"
        subtitle={activeWh ? `${activeWh.name}${activeWh.address ? ' · ' + activeWh.address : ''}` : 'Sklad tanlanmagan — chap paneldan tanlang'}
      />

      {/* KPI kartalar */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4"
      >
        <StatCard
          title="Qoldiqlar (birlik)"
          value={kpi?.units_on_hand?.toLocaleString()}
          sub={`${kpi?.sku_count ?? 0} SKU`}
          icon={Package}
          accent="blue"
          onClick={() => nav('/stock')}
        />
        <StatCard
          title="Kirim (30 kun)"
          value={kpi?.units_in?.toLocaleString()}
          sub={`${kpi?.receipts ?? 0} hujjat`}
          icon={ArrowDown}
          accent="green"
          onClick={() => nav('/receipt')}
        />
        <StatCard
          title="Chiqim (30 kun)"
          value={kpi?.units_out?.toLocaleString()}
          sub={`${kpi?.shipments ?? 0} hujjat`}
          icon={ArrowUp}
          accent="orange"
          onClick={() => nav('/shipment')}
        />
        <StatCard
          title="Ochiq palletlar"
          value={kpi?.open_pallets}
          sub={`${kpi?.open_tasks ?? 0} vazifa`}
          icon={Box}
          accent="purple"
          onClick={() => nav('/tasks')}
        />
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Skladlar ro'yxati */}
        <Card>
          <CardHeader icon={<Warehouse size={16} />} title="Barcha skladlar"
            action={<Button size="sm" variant="secondary" icon={<Plus size={14} />} onClick={() => setAddOpen(true)}>Yangi sklad</Button>} />
          {(warehouses as any[]).length === 0 ? (
            <EmptyState icon={Warehouse} title="Sklad yo'q" description="'Yangi sklad' bilan boshlang" />
          ) : (
            <div className="space-y-2">
              {(warehouses as any[]).map((wh: any) => {
                const on = wh.id === selectedWarehouseId
                return (
                  <div
                    key={wh.id}
                    onClick={() => setWarehouse(wh.id)}
                    className={`group flex items-center justify-between py-2.5 px-3 rounded-xl cursor-pointer transition border ${
                      on
                        ? 'border-blue-500/40 bg-blue-500/10'
                        : 'border-transparent hover:bg-slate-500/5'
                    }`}
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-700 truncate">{wh.name}</p>
                      <p className="text-xs text-slate-400 truncate">{wh.address ?? 'Manzil yo\'q'}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge tone={wh.is_active ? 'green' : 'red'} dot>
                        {wh.is_active ? 'Faol' : 'Nofaol'}
                      </Badge>
                      <button
                        onClick={(e) => removeWarehouse(wh, e)}
                        title="Skladni o'chirish"
                        className="text-slate-300 hover:text-rose-500 opacity-0 group-hover:opacity-100 transition p-1 rounded-lg hover:bg-rose-500/10"
                      >
                        <Trash2 size={15} />
                      </button>
                      <ChevronRight size={16} className={`transition ${on ? 'text-blue-500' : 'text-slate-300 group-hover:text-slate-400'}`} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </Card>

        {/* Muddat ogohlantirishi */}
        <Card>
          <CardHeader
            icon={<AlertTriangle size={16} className="text-amber-500" />}
            title="Muddat ogohlantirishi"
            action={(alerts as any[]).length > 0 ? <Badge tone="amber">{(alerts as any[]).length}</Badge> : undefined}
          />
          {(alerts as any[]).length === 0 ? (
            <EmptyState icon={AlertTriangle} title="Muddat yaqinlashgan mahsulot yo'q" description="Barcha partiyalar xavfsiz muddatda ✓" />
          ) : (
            <div className="space-y-1">
              {(alerts as any[]).slice(0, 6).map((a: any, i: number) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                  <div className="min-w-0">
                    <p className="text-sm text-slate-700">{a.expiry_date}</p>
                    <p className="text-xs text-slate-400 truncate">{a.total_qty} birlik · {a.locations?.slice(0, 2).join(', ')}</p>
                  </div>
                  <Badge tone={a.days_remaining <= 7 ? 'red' : 'amber'}>{a.days_remaining} kun</Badge>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Throughput */}
      {kpi && (
        <Card className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-500 flex items-center justify-center shrink-0">
            <TrendingUp size={17} />
          </div>
          <p className="text-sm text-slate-500">
            Kunlik o'rtacha:{' '}
            <span className="font-semibold text-slate-800">{kpi.throughput_per_day} birlik/kun</span>
            <span className="text-slate-400"> · {kpi.period_days} kunlik davr</span>
          </p>
        </Card>
      )}

      {addOpen && (
        <AddWarehouseModal
          onClose={() => setAddOpen(false)}
          onCreated={(wh) => {
            setAddOpen(false)
            setWarehouse(wh.id)
            qc.invalidateQueries({ queryKey: ['warehouses'] })
          }}
        />
      )}
    </div>
  )
}

// ─── Yangi sklad qo'shish modali ─────────────────────────────────────────────
function AddWarehouseModal({ onClose, onCreated }: { onClose: () => void; onCreated: (wh: any) => void }) {
  const [name, setName] = useState('')
  const [address, setAddress] = useState('')
  const [smartupCode, setSmartupCode] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    if (!name.trim()) { toast.error('Sklad nomini kiriting'); return }
    setBusy(true)
    try {
      const wh = await createWarehouse({
        name: name.trim(),
        address: address.trim() || null,
        smartup_warehouse_code: smartupCode.trim() || null,
      })
      toast.success('Sklad yaratildi')
      onCreated(wh)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Yaratishda xatolik')
    } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <Card className="w-full max-w-md space-y-4" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-slate-800 flex items-center gap-2">
            <Warehouse size={18} className="text-blue-500" /> Yangi sklad
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={18} /></button>
        </div>
        <FormField label="Sklad nomi">
          <Input autoFocus value={name} onChange={e => setName(e.target.value)} placeholder="masalan: Xomashyo skladi"
            onKeyDown={e => { if (e.key === 'Enter') submit() }} />
        </FormField>
        <FormField label="Manzil" hint="Ixtiyoriy">
          <Input value={address} onChange={e => setAddress(e.target.value)} placeholder="masalan: Toshkent, Sergeli" />
        </FormField>
        <FormField label="Smartup sklad kodi" hint="Ixtiyoriy — ERP bilan bog'lash uchun">
          <Input value={smartupCode} onChange={e => setSmartupCode(e.target.value)} placeholder="—" className="font-mono" />
        </FormField>
        <div className="flex justify-end gap-2 pt-1">
          <Button variant="secondary" onClick={onClose}>Bekor</Button>
          <Button onClick={submit} loading={busy} icon={<Plus size={15} />}>Yaratish</Button>
        </div>
      </Card>
    </div>
  )
}
