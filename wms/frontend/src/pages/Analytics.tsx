import { useQuery } from '@tanstack/react-query'
import {
  getHeatmap, getAbcSuggestions, getKpi, getExpiryAlerts,
  getThroughput, getAnalyticsDashboard, getSensors, getOccupancy,
  getReturnsAnalytics, getZoneSummary,
} from '../lib/api'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  LineChart, Line, CartesianGrid, Legend, AreaChart, Area,
  PieChart, Pie,
} from 'recharts'
import { useAuthStore } from '../store/auth'
import { BarChart3, Thermometer, Droplets, AlertTriangle, Wifi, Undo2, LayoutGrid } from 'lucide-react'

const HEAT_COLORS = ['#e2e8f0', '#bfdbfe', '#93c5fd', '#3b82f6', '#1d4ed8', '#1e3a8a']

function heatColor(count: number, max: number) {
  const idx = Math.floor((count / Math.max(max, 1)) * (HEAT_COLORS.length - 1))
  return HEAT_COLORS[Math.min(idx, HEAT_COLORS.length - 1)]
}

export default function Analytics({ embedded = false }: { embedded?: boolean }) {
  const { selectedWarehouseId } = useAuthStore()

  const { data: kpi } = useQuery({
    queryKey: ['kpi', selectedWarehouseId],
    queryFn: () => getKpi(selectedWarehouseId!),
    enabled: !!selectedWarehouseId,
    refetchInterval: 60_000,
  })
  const { data: heatmap = [] } = useQuery({
    queryKey: ['heatmap', selectedWarehouseId],
    queryFn: () => getHeatmap(selectedWarehouseId!),
    enabled: !!selectedWarehouseId,
  })
  const { data: abcList = [] } = useQuery({
    queryKey: ['abc', selectedWarehouseId],
    queryFn: () => getAbcSuggestions(selectedWarehouseId!),
    enabled: !!selectedWarehouseId,
  })
  const { data: alerts = [] } = useQuery({
    queryKey: ['expiry', selectedWarehouseId],
    queryFn: () => getExpiryAlerts(selectedWarehouseId!, 60),
    enabled: !!selectedWarehouseId,
    refetchInterval: 60_000,
  })
  const { data: dash } = useQuery({
    queryKey: ['dashboard', selectedWarehouseId],
    queryFn: () => getAnalyticsDashboard(selectedWarehouseId!),
    enabled: !!selectedWarehouseId,
    refetchInterval: 30_000,
  })
  const { data: throughput = [] } = useQuery({
    queryKey: ['throughput', selectedWarehouseId],
    queryFn: () => getThroughput(selectedWarehouseId!, 14),
    enabled: !!selectedWarehouseId,
    refetchInterval: 60_000,
  })
  const { data: sensors = [] } = useQuery({
    queryKey: ['sensors', selectedWarehouseId],
    queryFn: () => getSensors(selectedWarehouseId!),
    enabled: !!selectedWarehouseId,
    refetchInterval: 15_000,
  })
  const { data: occupancy = [] } = useQuery({
    queryKey: ['occupancy', selectedWarehouseId],
    queryFn: () => getOccupancy(selectedWarehouseId!),
    enabled: !!selectedWarehouseId,
    refetchInterval: 60_000,
  })
  const { data: returns } = useQuery({
    queryKey: ['returns', selectedWarehouseId],
    queryFn: () => getReturnsAnalytics(selectedWarehouseId!, 30),
    enabled: !!selectedWarehouseId,
    refetchInterval: 60_000,
  })
  const { data: zoneSummary = [] } = useQuery({
    queryKey: ['zone-summary', selectedWarehouseId],
    queryFn: () => getZoneSummary(selectedWarehouseId!, 30),
    enabled: !!selectedWarehouseId,
    refetchInterval: 60_000,
  })

  // Occupancy donut (band/bo'sh)
  const occ = occupancy as any[]
  const occupied = occ.filter((c: any) => c.state === 'full' || c.state === 'partial').length
  const empty = occ.filter((c: any) => c.state === 'empty').length
  const occPct = occ.length ? Math.round((occupied / occ.length) * 100) : 0
  const occPie = [
    { name: 'Band', value: occupied, fill: '#16a34a' },
    { name: "Bo'sh", value: empty, fill: '#e2e8f0' },
  ]

  // IoT
  const sensorList = sensors as any[]
  const sensorAlerts = sensorList.filter((s: any) => s.status === 'alert').length
  const avgTemp = sensorList.filter((s: any) => s.last_temp != null).length
    ? (sensorList.reduce((a: number, s: any) => a + (s.last_temp || 0), 0) / sensorList.filter((s: any) => s.last_temp != null).length).toFixed(1)
    : null

  const maxMoves = Math.max(...(heatmap as any[]).map((p: any) => p.move_count), 1)

  const kpiChart = kpi ? [
    { name: 'Kirim', value: kpi.units_in, fill: '#3b82f6' },
    { name: 'Chiqim', value: kpi.units_out, fill: '#f59e0b' },
    { name: 'Qolgan', value: kpi.units_on_hand, fill: '#10b981' },
  ] : []

  const expiryChart = (alerts as any[]).slice(0, 15).map((a: any) => ({
    date: a.expiry_date,
    qty: a.total_qty,
    days: a.days_remaining,
  }))

  if (!selectedWarehouseId) {
    return (
      <div className="p-6 flex flex-col items-center justify-center h-64 text-slate-400">
        <BarChart3 size={40} className="mb-3 opacity-30" />
        <p>Sklad tanlanmagan. Chap paneldan sklad tanlang.</p>
      </div>
    )
  }

  return (
    <div className={embedded ? 'space-y-6' : 'p-4 lg:p-6 space-y-6'}>
      {!embedded && <h1 className="text-xl font-bold text-slate-800">Analitika</h1>}

      {/* Live monitor cards (shift lead) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-3">
        {[
          { label: 'Bugun kirim', value: dash?.today_inbound ?? 0, color: 'text-blue-600' },
          { label: 'Bugun chiqim', value: dash?.today_outbound ?? 0, color: 'text-amber-600' },
          { label: 'Qoldiq (birlik)', value: kpi?.units_on_hand ?? 0, color: 'text-emerald-600' },
          { label: 'To\'ldirilish', value: `${occPct}%`, color: 'text-indigo-600' },
          { label: 'Ochiq palletlar', value: dash?.open_pallets ?? 0, color: 'text-violet-600' },
          { label: 'Bloklangan', value: dash?.blocked_qty ?? 0, color: 'text-red-600' },
        ].map(c => (
          <div key={c.label} className="bg-white rounded-xl shadow-sm p-4">
            <div className="text-xs text-slate-400">{c.label}</div>
            <div className={`text-2xl font-bold ${c.color}`}>
              {typeof c.value === 'number' ? c.value.toLocaleString() : c.value}
            </div>
          </div>
        ))}
      </div>

      {/* IoT harorat tasmasi */}
      {sensorList.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-slate-700 flex items-center gap-2">
              <Thermometer size={16} className="text-red-500" /> IoT Harorat monitoringi
              {sensorAlerts > 0 && (
                <span className="text-xs text-red-600 flex items-center gap-1"><AlertTriangle size={13} /> {sensorAlerts} ogohlantirish</span>
              )}
            </h2>
            {avgTemp && <span className="text-xs text-slate-400">O'rtacha: <b className="text-slate-600">{avgTemp}°C</b></span>}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
            {sensorList.map((s: any) => {
              const alert = s.status === 'alert', off = s.status === 'offline' || s.status === 'no-data'
              return (
                <div key={s.id} className="rounded-lg border p-2.5"
                  style={{ borderColor: alert ? '#fecaca' : '#e2e8f0', background: alert ? '#fef2f2' : '#fff' }}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-600 truncate">{s.name}</span>
                    {off ? <Wifi size={12} className="text-slate-300" /> : <Wifi size={12} className="text-green-500" />}
                  </div>
                  <div className="flex items-baseline gap-1 mt-1">
                    <span className="text-xl font-bold" style={{ color: alert ? '#dc2626' : '#0f172a' }}>
                      {s.last_temp ?? '—'}<span className="text-xs text-slate-400">°C</span>
                    </span>
                    <span className="text-xs text-blue-500 flex items-center gap-0.5 ml-auto">
                      <Droplets size={11} /> {s.last_hum ?? '—'}%
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        {/* Throughput (daily in/out) */}
        <div className="bg-white rounded-xl shadow-sm p-5 lg:col-span-2">
          <h2 className="font-semibold text-slate-700 mb-1">Kunlik oqim (14 kun)</h2>
          <p className="text-xs text-slate-400 mb-4">Kirim va chiqim birliklari</p>
          {(throughput as any[]).length === 0 ? (
            <p className="text-sm text-slate-400">Ma'lumot yo'q</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={throughput as any[]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Area type="monotone" dataKey="inbound" stroke="#3b82f6" fill="#bfdbfe" name="Kirim" />
                <Area type="monotone" dataKey="outbound" stroke="#f59e0b" fill="#fde68a" name="Chiqim" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
        {/* KPI Bar chart */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="font-semibold text-slate-700 mb-1">Harakat hajmi (30 kun)</h2>
          <p className="text-xs text-slate-400 mb-4">Kirim, chiqim va qoldiq birliklarida</p>
          {kpiChart.length === 0 ? (
            <p className="text-sm text-slate-400">Ma'lumot yo'q</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={kpiChart} barSize={48}>
                <XAxis dataKey="name" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v: any) => v?.toLocaleString()} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {kpiChart.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Occupancy donut */}
        {occ.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="font-semibold text-slate-700 mb-1">Sklad to'ldirilishi</h2>
            <p className="text-xs text-slate-400 mb-2">Band va bo'sh yacheykalar nisbati</p>
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="55%" height={170}>
                <PieChart>
                  <Pie data={occPie} dataKey="value" nameKey="name" innerRadius={42} outerRadius={64} paddingAngle={2}>
                    {occPie.map((e, i) => <Cell key={i} fill={e.fill} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                <div className="text-3xl font-bold text-indigo-600">{occPct}%</div>
                <div className="text-xs text-slate-500">To'ldirilgan</div>
                <div className="text-sm text-slate-600 pt-2">
                  <div>🟢 Band: <b>{occupied}</b></div>
                  <div>⚪ Bo'sh: <b>{empty}</b></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Heatmap */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="font-semibold text-slate-700 mb-1">Yacheyka faolligi</h2>
          <p className="text-xs text-slate-400 mb-4">To'q rang = ko'p harakat (30 kun)</p>
          {(heatmap as any[]).length === 0 ? (
            <p className="text-sm text-slate-400">Ma'lumot yo'q</p>
          ) : (
            <div className="flex flex-wrap gap-1">
              {(heatmap as any[]).slice(0, 100).map((p: any) => (
                <div
                  key={p.location_id}
                  title={`${p.location_code}: ${p.move_count} harakat`}
                  style={{ backgroundColor: heatColor(p.move_count, maxMoves) }}
                  className="w-5 h-5 rounded-sm cursor-default border border-white/60"
                />
              ))}
            </div>
          )}
          <div className="flex items-center gap-1.5 mt-3">
            <span className="text-xs text-slate-400">Kam</span>
            {HEAT_COLORS.map(c => <div key={c} className="w-4 h-3 rounded-sm" style={{ background: c }} />)}
            <span className="text-xs text-slate-400">Ko'p</span>
          </div>
        </div>

        {/* Expiry alerts chart */}
        {expiryChart.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="font-semibold text-slate-700 mb-1">Muddati yaqinlashayotgan mahsulotlar</h2>
            <p className="text-xs text-slate-400 mb-4">Keyingi 60 kun ichida muddati tugaydigan</p>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={expiryChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="qty" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} name="Birlik" />
                <Line type="monotone" dataKey="days" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} name="Qolgan kun" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* ABC re-slotting */}
        {(abcList as any[]).length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="font-semibold text-slate-700 mb-1">ABC Qayta tasnif tavsiyalari</h2>
            <p className="text-xs text-slate-400 mb-4">So'nggi 30 kun terish chastotasi asosida</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-slate-400 uppercase">
                    <th className="text-left py-2 pr-4">Hozir</th>
                    <th className="text-left py-2 pr-4">Tavsiya</th>
                    <th className="text-left py-2 pr-4">Terish</th>
                    <th className="text-left py-2">Sabab</th>
                  </tr>
                </thead>
                <tbody>
                  {(abcList as any[]).map((s: any, i: number) => (
                    <tr key={i} className="border-b border-slate-50 last:border-0">
                      <td className="py-2 pr-4">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                          s.current_abc === 'A' ? 'bg-green-100 text-green-700'
                          : s.current_abc === 'B' ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-slate-100 text-slate-500'
                        }`}>
                          {s.current_abc ?? '—'}
                        </span>
                      </td>
                      <td className="py-2 pr-4">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                          s.suggested_abc === 'A' ? 'bg-green-100 text-green-700'
                          : s.suggested_abc === 'B' ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-slate-100 text-slate-500'
                        }`}>
                          {s.suggested_abc}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-slate-600">{s.move_count_30d}</td>
                      <td className="py-2 text-slate-400 text-xs">{s.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Возврат (returns) analitikasi */}
        {returns && (
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="font-semibold text-slate-700 mb-1 flex items-center gap-2">
              <Undo2 size={16} className="text-rose-500" /> Qaytarishlar (возврат)
            </h2>
            <p className="text-xs text-slate-400 mb-4">So'nggi {returns.period_days} kun · qaytarish darajasi {returns.return_rate_pct}%</p>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
              {[
                { label: 'Mijozdan qaytarish', value: returns.customer_return_units, cls: 'text-rose-600', sub: 'birlik' },
                { label: "Ta'minotchiga", value: returns.supplier_return_units, cls: 'text-violet-600', sub: 'birlik' },
                { label: 'Qaytarish hodisalari', value: returns.return_events, cls: 'text-slate-700', sub: 'ta' },
                { label: 'Qaytarish darajasi', value: returns.return_rate_pct + '%', cls: 'text-amber-600', sub: 'chiqimdan' },
              ].map((s, i) => (
                <div key={i} className="rounded-xl border border-slate-200/70 p-3">
                  <p className="text-xs text-slate-400">{s.label}</p>
                  <p className={`text-xl font-bold ${s.cls}`}>{s.value}</p>
                  <p className="text-xs text-slate-400">{s.sub}</p>
                </div>
              ))}
            </div>
            {returns.daily?.length > 0 && (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={returns.daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="customer" stackId="r" fill="#f43f5e" name="Mijozdan" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="supplier" stackId="r" fill="#8b5cf6" name="Ta'minotchiga" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
            {returns.top_products?.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-medium text-slate-500 mb-2">Eng ko'p qaytarilgan mahsulotlar</p>
                <div className="space-y-1">
                  {returns.top_products.slice(0, 6).map((p: any, i: number) => (
                    <div key={i} className="flex items-center justify-between text-sm py-1 border-b border-slate-50 last:border-0">
                      <span className="text-slate-600 truncate">{p.product_name}</span>
                      <span className="font-medium text-slate-700 tabular-nums">{p.qty} birlik</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {returns.return_events === 0 && (
              <p className="text-sm text-slate-400 text-center py-4">Bu davrda qaytarish bo'lmagan ✓</p>
            )}
          </div>
        )}

        {/* Zona/yacheyka analitikasi */}
        {(zoneSummary as any[]).length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="font-semibold text-slate-700 mb-1 flex items-center gap-2">
              <LayoutGrid size={16} className="text-blue-500" /> Zona analitikasi
            </h2>
            <p className="text-xs text-slate-400 mb-4">Har zona bo'yicha to'lish, qoldiq va harakat (30 kun)</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-slate-400 uppercase">
                    <th className="text-left py-2 pr-4">Zona</th>
                    <th className="text-right py-2 pr-4">Yacheyka</th>
                    <th className="text-right py-2 pr-4">Band</th>
                    <th className="text-right py-2 pr-4">Qoldiq</th>
                    <th className="text-left py-2 pr-4">To'lish</th>
                    <th className="text-right py-2">Harakat</th>
                  </tr>
                </thead>
                <tbody>
                  {(zoneSummary as any[]).map((z: any, i: number) => (
                    <tr key={i} className="border-b border-slate-50 last:border-0">
                      <td className="py-2 pr-4 font-medium text-slate-700">{z.name}</td>
                      <td className="py-2 pr-4 text-right text-slate-600">{z.location_count}</td>
                      <td className="py-2 pr-4 text-right text-slate-600">{z.occupied_count}</td>
                      <td className="py-2 pr-4 text-right text-slate-600 tabular-nums">{z.total_qty}</td>
                      <td className="py-2 pr-4">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden min-w-16">
                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${Math.min(100, z.fill_pct)}%` }} />
                          </div>
                          <span className="text-xs text-slate-500 w-10 text-right">{z.fill_pct}%</span>
                        </div>
                      </td>
                      <td className="py-2 text-right text-slate-600">{z.move_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
