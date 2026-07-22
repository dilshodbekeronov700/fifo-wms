import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getWarehouses,
  getShipmentOrders,
  createPickTask,
  confirmShipment,
} from '../lib/api'
import {
  ArrowUpFromLine,
  Route,
  RefreshCw,
  Package,
  CheckCircle2,
  AlertTriangle,
  Layers,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader, Card, CardHeader, Button, Select, Badge, EmptyState } from '../components/ui'
import type { Tone } from '../components/ui'

// Smartup order status badge tone
const ORDER_STATUS_TONE: Record<string, Tone> = {
  D: 'slate',
  'B#N': 'amber',
  'B#E': 'amber',
  'B#W': 'blue',
  'B#S': 'green',
  'B#V': 'red',
  A: 'slate',
  C: 'slate',
}

// Smartup `order_list:get_widget_data` bilan tasdiqlangan (2026-07-21): B#V=Доставлен.
const ORDER_STATUS_LABEL: Record<string, string> = {
  D: 'Qoralama',
  'B#N': 'Yangi',
  'B#E': 'Jarayonda',
  'B#W': "Kutilmoqda",
  'B#S': "Jo'natilgan",
  'B#V': 'Yetkazilgan',
  A: 'Arxiv',
  C: 'Yopilgan',
}

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

interface PickTaskResult {
  document_id: string
  task_id?: string
  route?: RouteStop[]
  shortfall_lines?: Array<string | { product_id?: string; product_code?: string; requested?: number; available?: number }>
  warnings?: string[]
}

export default function Shipment() {
  const qc = useQueryClient()
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [whId, setWhId] = useState<string>('')
  const wid = whId || warehouses[0]?.id

  const [selectedDeal, setSelectedDeal] = useState<string | null>(null)
  const [createdTask, setCreatedTask] = useState<PickTaskResult | null>(null)
  // Smartup (ERP) "Buyurtmalar" sahifasidan ?deal=<id> bilan kelsa — avtomatik tanlab, marshrut tuzamiz.
  const [searchParams, setSearchParams] = useSearchParams()
  const autoDeal = searchParams.get('deal')
  const autoDone = useRef<string | null>(null)

  // ── Smartup orders for the selected warehouse ───────────────────────────────
  const {
    data: orders = [],
    isLoading: ordersLoading,
    isFetching: ordersFetching,
    refetch: refetchOrders,
  } = useQuery({
    queryKey: ['shipment-orders', wid],
    queryFn: () => getShipmentOrders({ warehouse_id: wid }),
    enabled: !!wid,
  })

  // ── Create pick task for chosen order ───────────────────────────────────────
  const pickMut = useMutation({
    mutationFn: (order: any) =>
      createPickTask({
        warehouse_id: wid,
        smartup_deal_id: order.deal_id,
        order_number: order.order_number,
        lines: (order.lines ?? []).map((l: any) => ({
          product_id: l.product_id,
          product_code: l.product_code,
          gtin: l.gtin,
          order_line_id: l.product_unit_id ?? l.order_line_id,
          requested_boxes: l.qty_ordered ?? l.requested_boxes ?? 0,
        })),
      }),
    onSuccess: (data: PickTaskResult) => {
      setCreatedTask(data)
      const shortfalls = data.shortfall_lines?.length ?? 0
      if (shortfalls > 0) {
        toast(`Pick marshruti yaratildi, ${shortfalls} qatorda yetishmovchilik`, { icon: '⚠️' })
      } else {
        toast.success('Pick marshruti yaratildi')
      }
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Pick vazifa yaratishda xatolik'),
  })

  const confirmMut = useMutation({
    mutationFn: (doc_id: string) => confirmShipment(doc_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shipment-orders'] })
      qc.invalidateQueries({ queryKey: ['stock'] })
      setCreatedTask(null)
      setSelectedDeal(null)
      toast.success('Chiqim tasdiqlandi')
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Tasdiqlashda xatolik'),
  })

  const handleSelectOrder = (order: any) => {
    setSelectedDeal(order.deal_id)
    setCreatedTask(null)
    pickMut.mutate(order)
  }

  // ?deal=<id> bilan kelinganda — buyurtmani avtomatik tanlab, marshrutni bir marta tuzamiz.
  useEffect(() => {
    if (!autoDeal || autoDone.current === autoDeal || orders.length === 0) return
    const order = orders.find((o: any) => String(o.deal_id) === String(autoDeal))
    if (!order) return
    autoDone.current = autoDeal
    handleSelectOrder(order)
    // URL'ni tozalaymiz (qayta yuklanganda takror ishga tushmasin)
    searchParams.delete('deal')
    setSearchParams(searchParams, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoDeal, orders])

  if (!wid) {
    return (
      <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
        <Card className="min-h-[300px] flex items-center justify-center">
          <EmptyState
            icon={ArrowUpFromLine}
            title="Sklad mavjud emas yoki tanlanmagan"
          />
        </Card>
      </div>
    )
  }

  const fmtShortfall = (s: any) =>
    typeof s === 'string'
      ? s
      : `${s.product_code ?? s.product_id ?? ''} (so'ralgan ${s.requested ?? '?'}, mavjud ${s.available ?? '?'})`

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
      <PageHeader
        icon={<Route size={20} />}
        title="Pick marshruti"
        subtitle="Smartup buyurtmalari → Pick marshruti → Tasdiqlash"
        actions={
          <>
            <Select
              value={wid}
              onChange={e => {
                setWhId(e.target.value)
                setSelectedDeal(null)
                setCreatedTask(null)
              }}
              className="w-auto min-w-40"
            >
              {warehouses.map((wh: any) => (
                <option key={wh.id} value={wh.id}>{wh.name}</option>
              ))}
            </Select>
            <Button
              variant="secondary"
              onClick={() => refetchOrders()}
              disabled={ordersFetching}
              icon={<RefreshCw size={14} className={ordersFetching ? 'animate-spin' : ''} />}
            >
              Yangilash
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        {/* ── Orders list ──────────────────────────────────────────────────── */}
        <Card>
          <CardHeader icon={<Package size={16} className="text-blue-500" />} title="Buyurtmalar" />

          {ordersLoading && <p className="text-sm text-slate-400 py-8 text-center">Yuklanmoqda...</p>}
          {!ordersLoading && orders.length === 0 && (
            <EmptyState icon={Package} title="Jo'natiladigan buyurtmalar yo'q" />
          )}

          <div className="space-y-2">
            {orders.map((order: any) => {
              const active = selectedDeal === order.deal_id
              return (
                <button
                  key={order.deal_id}
                  onClick={() => handleSelectOrder(order)}
                  disabled={pickMut.isPending && active}
                  className={`w-full text-left rounded-xl border p-3 transition ${
                    active
                      ? 'border-blue-500/40 bg-blue-500/10'
                      : 'border-transparent hover:bg-slate-500/5'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-medium text-slate-700 text-sm truncate">
                        {order.order_number ?? order.deal_id}
                      </p>
                      <p className="text-xs text-slate-400 truncate">
                        {order.customer_tin ? `STIR: ${order.customer_tin}` : ''}
                        {order.with_marking ? ' · Markirovkali' : ''}
                      </p>
                    </div>
                    <Badge tone={ORDER_STATUS_TONE[order.status] ?? 'slate'} className="shrink-0">
                      {ORDER_STATUS_LABEL[order.status] ?? order.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{(order.lines ?? []).length} qator</p>
                  {active && pickMut.isPending && (
                    <p className="text-xs text-blue-500 mt-1 flex items-center gap-1">
                      <RefreshCw size={11} className="animate-spin" /> Marshrut tuzilmoqda...
                    </p>
                  )}
                </button>
              )
            })}
          </div>
        </Card>

        {/* ── Pick route ───────────────────────────────────────────────────── */}
        <Card>
          <CardHeader
            icon={<Route size={16} className="text-green-500" />}
            title="Pick marshruti"
            action={createdTask ? (
              <Button
                variant="success"
                size="sm"
                onClick={() => confirmMut.mutate(createdTask.document_id)}
                loading={confirmMut.isPending}
                disabled={confirmMut.isPending}
                icon={<CheckCircle2 size={14} />}
              >
                Chiqimni tasdiqlash
              </Button>
            ) : undefined}
          />

          {!createdTask && (
            <EmptyState
              icon={Route}
              title="Marshrut yo'q"
              description="Chapdan buyurtma tanlang — marshrut shu yerda paydo bo'ladi."
            />
          )}

          {createdTask && (
            <>
              {/* Warnings */}
              {createdTask.warnings && createdTask.warnings.length > 0 && (
                <div className="mb-3 rounded-xl bg-amber-500/10 border border-amber-500/30 p-2.5">
                  {createdTask.warnings.map((w, i) => (
                    <p key={i} className="text-xs text-amber-700 flex items-start gap-1.5">
                      <AlertTriangle size={12} className="mt-0.5 shrink-0" /> {w}
                    </p>
                  ))}
                </div>
              )}

              {/* Shortfalls */}
              {createdTask.shortfall_lines && createdTask.shortfall_lines.length > 0 && (
                <div className="mb-3 rounded-xl bg-rose-500/10 border border-rose-500/30 p-2.5">
                  <p className="text-xs font-medium text-rose-700 mb-1 flex items-center gap-1.5">
                    <AlertTriangle size={12} /> Yetishmaydigan qatorlar
                  </p>
                  {createdTask.shortfall_lines.map((s, i) => (
                    <p key={i} className="text-xs text-rose-600">• {fmtShortfall(s)}</p>
                  ))}
                </div>
              )}

              {/* Route stops */}
              <div className="space-y-1 max-h-[60vh] overflow-y-auto">
                {(createdTask.route ?? []).length === 0 && (
                  <p className="text-xs text-slate-400 py-4 text-center">Marshrut bo'sh</p>
                )}
                {(createdTask.route ?? []).map((stop, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 text-xs py-2 border-b border-slate-100 last:border-0"
                  >
                    <span className="w-6 h-6 bg-blue-500/10 text-blue-600 rounded-full flex items-center justify-center font-bold shrink-0">
                      {stop.sequence}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono font-medium text-slate-700">{stop.location_code}</span>
                        <span className="text-slate-500 font-medium">{stop.take_qty} dona</span>
                        {stop.is_partial_pallet && (
                          <Badge tone="orange">
                            <Layers size={10} /> Qisman pallet
                          </Badge>
                        )}
                      </div>
                      {(stop.product_name || stop.product_code || stop.product_id) && (
                        <p className="text-slate-500 truncate mt-0.5">
                          {stop.product_name ?? stop.product_id}
                          {stop.product_code && <span className="text-slate-400 font-mono"> · {stop.product_code}</span>}
                        </p>
                      )}
                      {(stop.lot_number || stop.production_date || stop.expiry_date) && (
                        <p className="text-slate-400 mt-0.5 flex flex-wrap gap-x-3">
                          {stop.lot_number && <span>Partiya: {stop.lot_number}</span>}
                          {stop.production_date && <span>I.ch.: {stop.production_date}</span>}
                          {stop.expiry_date && <span>Muddat: {stop.expiry_date}</span>}
                        </p>
                      )}
                      {stop.marking_codes && stop.marking_codes.length > 0 && (
                        <p className="text-slate-300 mt-0.5">{stop.marking_codes.length} markirovka kodi</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  )
}
