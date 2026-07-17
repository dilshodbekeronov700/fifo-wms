import { useQuery } from '@tanstack/react-query'
import { getWarehouses, getExpiryAlerts } from '../lib/api'
import { useState } from 'react'
import { AlertTriangle, CheckCircle2, MapPin } from 'lucide-react'
import { PageHeader, Card, Select, Badge, EmptyState, type Tone } from '../components/ui'

export default function Alerts({ embedded }: { embedded?: boolean }) {
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [whId, setWhId] = useState('')
  const [warnDays, setWarnDays] = useState(30)
  const wid = whId || warehouses[0]?.id

  const { data: alerts = [], isLoading } = useQuery({
    queryKey: ['alerts', wid, warnDays],
    queryFn: () => getExpiryAlerts(wid, warnDays),
    enabled: !!wid,
  })

  const alertTone = (d: number): Tone => (d <= 7 ? 'red' : d <= 14 ? 'orange' : 'amber')
  const alertBar = (d: number) => (d <= 7 ? 'border-rose-400' : d <= 14 ? 'border-orange-400' : 'border-amber-300')

  const controls = (
    <div className="flex gap-2">
      <Select value={wid ?? ''} onChange={e => setWhId(e.target.value)} className="w-auto min-w-40">
        {warehouses.map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
      </Select>
      <Select value={warnDays} onChange={e => setWarnDays(Number(e.target.value))} className="w-auto">
        {[7, 14, 30, 60, 90].map(d => <option key={d} value={d}>{d} kun</option>)}
      </Select>
    </div>
  )

  const body = (
    <>
      {isLoading && <p className="text-slate-400 text-sm">Yuklanmoqda...</p>}

      {!isLoading && alerts.length === 0 && (
        <Card>
          <EmptyState
            icon={CheckCircle2}
            title="Muddat yaqinlashgan mahsulot yo'q"
            description={`${warnDays} kun ichida barcha partiyalar xavfsiz`}
          />
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {alerts.map((a: any, i: number) => (
          <Card key={i} hover className={`border-l-4 ${alertBar(a.days_remaining)}`}>
            <div className="flex justify-between items-start mb-2">
              <Badge tone={alertTone(a.days_remaining)}>{a.days_remaining} kun qoldi</Badge>
              <span className="text-xs text-slate-400">{a.expiry_date}</span>
            </div>
            <p className="font-semibold text-slate-700 text-sm">
              {a.lot_number ? `Partiya: ${a.lot_number}` : 'Partiya raqami yo\'q'}
            </p>
            <p className="text-slate-500 text-sm mt-1">{a.total_qty} birlik</p>
            <div className="flex flex-wrap gap-1 mt-2">
              {a.locations.map((loc: string) => (
                <span key={loc} className="inline-flex items-center gap-1 text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">
                  <MapPin size={10} className="text-slate-400" />{loc}
                </span>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </>
  )

  if (embedded) {
    return (
      <div className="p-4 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <AlertTriangle size={16} className="text-orange-400" /> Muddat ogohlantirishi
          </h2>
          {controls}
        </div>
        {body}
      </div>
    )
  }

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
      <PageHeader
        icon={<AlertTriangle size={20} />}
        title="Muddat ogohlantirishi"
        subtitle="Muddati yaqinlashgan partiyalar"
        actions={controls}
      />
      {body}
    </div>
  )
}
