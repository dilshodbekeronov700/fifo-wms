/**
 * IoT Monitoring — harorat/namlik real-vaqt (ESP32 + DHT-21).
 *  Sensor kartochkalari (jonli qiymat + holat), tarix grafigi, sensor qo'shish.
 *  Har 10 soniyada avto-yangilanadi.
 */
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getWarehouses, getSensors, createSensor, deleteSensor, getSensorHistory,
} from '../lib/api'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { Thermometer, Droplets, Plus, Trash2, Wifi, WifiOff, AlertTriangle, X } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  PageHeader, Card, Button, Select, Badge, EmptyState, FormField, Input, type Tone,
} from '../components/ui'

const STATUS: Record<string, { tone: Tone; color: string; label: string; Icon: any }> = {
  online:    { tone: 'green', color: '#16a34a', label: 'Online',           Icon: Wifi },
  alert:     { tone: 'red',   color: '#dc2626', label: 'Ogohlantirish',    Icon: AlertTriangle },
  offline:   { tone: 'slate', color: '#94a3b8', label: 'Offline',          Icon: WifiOff },
  'no-data': { tone: 'slate', color: '#94a3b8', label: "Ma'lumot yo'q",    Icon: WifiOff },
}

export default function Monitoring() {
  const qc = useQueryClient()
  const [whId, setWhId] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [onlyAlert, setOnlyAlert] = useState(false)

  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const wid = whId || (warehouses as any[])[0]?.id

  const { data: sensors = [] } = useQuery({
    queryKey: ['sensors', wid], queryFn: () => getSensors(wid),
    enabled: !!wid, refetchInterval: 10000,  // 10s avto-yangilanish
  })

  const alertCount = (sensors as any[]).filter(s => s.status === 'alert').length

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
      <PageHeader
        icon={<Thermometer size={20} />}
        title="Harorat monitoringi"
        subtitle={`Real-vaqt IoT sensorlar (ESP32 + DHT-21) · har 10s yangilanadi${alertCount > 0 ? ` · ${alertCount} ogohlantirish` : ''}`}
        actions={
          <>
            <Button
              variant={onlyAlert ? 'danger' : 'secondary'}
              onClick={() => setOnlyAlert(v => !v)}
              icon={<AlertTriangle size={15} />}
            >
              Faqat ogohlantirish{alertCount > 0 && ` (${alertCount})`}
            </Button>
            <Button onClick={() => setAddOpen(true)} icon={<Plus size={15} />}>Sensor qo'shish</Button>
            <Select value={wid ?? ''} onChange={e => setWhId(e.target.value)} className="w-auto min-w-40">
              {(warehouses as any[]).map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </Select>
          </>
        }
      />

      {(sensors as any[]).length === 0 && (
        <Card>
          <EmptyState
            icon={Thermometer}
            title="Hali sensor yo'q"
            description={
              <>
                "Sensor qo'shish" bosib, ESP32 qurilmasiga <code className="bg-slate-100 px-1 rounded">device_key</code> bering.
                Qurilma <code className="bg-slate-100 px-1 rounded">POST /api/v1/sensors/ingest</code> ga ma'lumot yuboradi.
              </>
            }
            action={<Button onClick={() => setAddOpen(true)} icon={<Plus size={15} />}>Sensor qo'shish</Button>}
          />
        </Card>
      )}

      {/* Sensor kartochkalari */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {(sensors as any[]).filter((s: any) => !onlyAlert || s.status === 'alert').map((s: any) => {
          const st = STATUS[s.status] ?? STATUS['no-data']
          return (
            <Card key={s.id} padded={false} hover className="overflow-hidden">
              <div className="px-4 py-3 flex items-center justify-between border-b border-slate-200/70">
                <div className="flex items-center gap-2">
                  <st.Icon size={16} style={{ color: st.color }} />
                  <span className="font-semibold text-slate-700 text-sm">{s.name}</span>
                </div>
                <Badge tone={st.tone} dot>{st.label}</Badge>
              </div>
              <div className="p-4 grid grid-cols-2 gap-3">
                <div className="flex items-center gap-2">
                  <Thermometer size={26} className="text-orange-500" />
                  <div>
                    <div className="text-2xl font-bold text-slate-800">{s.last_temp ?? '—'}<span className="text-sm text-slate-400">°C</span></div>
                    <div className="text-[11px] text-slate-400">{s.temp_min}–{s.temp_max}°C</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Droplets size={26} className="text-blue-500" />
                  <div>
                    <div className="text-2xl font-bold text-slate-800">{s.last_hum ?? '—'}<span className="text-sm text-slate-400">%</span></div>
                    <div className="text-[11px] text-slate-400">namlik</div>
                  </div>
                </div>
              </div>
              <div className="px-4 pb-3 flex items-center justify-between">
                <span className="text-[11px] text-slate-400">
                  {s.last_seen ? new Date(s.last_seen).toLocaleString() : 'hech qachon'}
                </span>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="ghost" onClick={() => setExpanded(expanded === s.id ? null : s.id)}>
                    {expanded === s.id ? 'Yopish' : 'Tarix'}
                  </Button>
                  <button onClick={async () => { if (confirm('O\'chirilsinmi?')) { await deleteSensor(s.id); qc.invalidateQueries({ queryKey: ['sensors', wid] }) } }}
                    className="text-slate-300 hover:text-rose-500 transition"><Trash2 size={14} /></button>
                </div>
              </div>
              {expanded === s.id && <SensorChart id={s.id} />}
            </Card>
          )
        })}
      </div>

      {addOpen && <AddSensorModal wid={wid} warehouses={warehouses as any[]}
        onClose={() => setAddOpen(false)} onDone={() => { setAddOpen(false); qc.invalidateQueries({ queryKey: ['sensors', wid] }) }} />}
    </div>
  )
}

function SensorChart({ id }: { id: string }) {
  const { data = [] } = useQuery({
    queryKey: ['sensor-history', id], queryFn: () => getSensorHistory(id, 24), refetchInterval: 15000,
  })
  const chart = (data as any[]).map(r => ({
    t: new Date(r.t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    temp: r.temp, hum: r.hum,
  }))
  return (
    <div className="px-2 pb-3 h-44 border-t border-slate-100">
      {chart.length === 0 ? (
        <div className="h-full flex items-center justify-center text-xs text-slate-400">Tarix yo'q</div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chart} margin={{ top: 12, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="t" tick={{ fontSize: 9 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 9 }} stroke="#94a3b8" />
            <Tooltip />
            <Line type="monotone" dataKey="temp" stroke="#f97316" strokeWidth={2} dot={false} name="°C" />
            <Line type="monotone" dataKey="hum" stroke="#3b82f6" strokeWidth={2} dot={false} name="%" />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

function AddSensorModal({ wid, onClose, onDone }: any) {
  const [f, setF] = useState({ name: '', device_key: '', temp_min: 5, temp_max: 25, hum_max: 80 })
  const [busy, setBusy] = useState(false)
  const set = (k: string, v: any) => setF((s: any) => ({ ...s, [k]: v }))
  const run = async () => {
    if (!f.name || !f.device_key) { toast.error('Nom va device_key kiriting'); return }
    setBusy(true)
    try {
      await createSensor({ ...f, warehouse_id: wid, temp_min: +f.temp_min, temp_max: +f.temp_max, hum_max: +f.hum_max })
      toast.success('Sensor qo\'shildi'); onDone()
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? 'Xatolik') } finally { setBusy(false) }
  }
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <Card className="w-[380px] space-y-3" onClick={(e: any) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-slate-800 flex items-center gap-2"><Thermometer size={18} className="text-blue-500" /> Yangi sensor</h3>
          <button onClick={onClose}><X size={16} className="text-slate-400 hover:text-slate-600 transition" /></button>
        </div>
        <FormField label="Nom">
          <Input value={f.name} onChange={e => set('name', e.target.value)} placeholder="Sklad-1 harorat" />
        </FormField>
        <FormField label="Device key (ESP32 firmware'ga yoziladi)">
          <Input value={f.device_key} onChange={e => set('device_key', e.target.value)} placeholder="esp32-gp-001" />
        </FormField>
        <div className="grid grid-cols-3 gap-2">
          <FormField label="Temp min °C">
            <Input type="number" value={f.temp_min} onChange={e => set('temp_min', e.target.value)} />
          </FormField>
          <FormField label="Temp max °C">
            <Input type="number" value={f.temp_max} onChange={e => set('temp_max', e.target.value)} />
          </FormField>
          <FormField label="Namlik max %">
            <Input type="number" value={f.hum_max} onChange={e => set('hum_max', e.target.value)} />
          </FormField>
        </div>
        <Button onClick={run} loading={busy} icon={<Plus size={16} />} className="w-full">
          {busy ? 'Saqlanmoqda…' : 'Qo\'shish'}
        </Button>
      </Card>
    </div>
  )
}
