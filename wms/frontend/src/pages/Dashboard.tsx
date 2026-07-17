import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { getWarehouses, getKpi, getExpiryAlerts } from '../lib/api'
import { useAuthStore } from '../store/auth'
import {
  Package, Warehouse, TrendingUp, AlertTriangle,
  ArrowDown, ArrowUp, Box, ChevronRight,
} from 'lucide-react'
import { staggerContainer } from '../lib/motion'
import { Card, CardHeader, StatCard, Badge, EmptyState, PageHeader } from '../components/ui'

export default function Dashboard() {
  const { selectedWarehouseId, setWarehouse } = useAuthStore()
  const nav = useNavigate()

  const { data: warehouses = [] } = useQuery({
    queryKey: ['warehouses'],
    queryFn: getWarehouses,
    staleTime: 60_000,
  })

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
          <CardHeader icon={<Warehouse size={16} />} title="Barcha skladlar" />
          {(warehouses as any[]).length === 0 ? (
            <EmptyState icon={Warehouse} title="Sklad yo'q" />
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
    </div>
  )
}
