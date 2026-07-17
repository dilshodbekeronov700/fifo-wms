/**
 * Hisobotlar (Faza 4) — qoldiq, harakat, muddat (FEFO), svereka, harorat.
 * Har birini CSV / Excel / PDF formatda yuklab olish.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getWarehouses, exportReport } from '../lib/api'
import { FileText, Download, Package, ArrowLeftRight, CalendarClock, Scale, Thermometer } from 'lucide-react'
import toast from 'react-hot-toast'

const REPORTS = [
  { kind: 'stock', label: 'Qoldiq hisoboti', desc: 'Zona/mahsulot/partiya bo\'yicha joriy qoldiq', Icon: Package, color: '#2563eb', params: {} },
  { kind: 'movement', label: 'Harakat hisoboti', desc: 'Kirim/chiqim/ko\'chirish (ledger)', Icon: ArrowLeftRight, color: '#16a34a', params: { days: 30 } },
  { kind: 'expiry', label: 'Muddat (FEFO)', desc: 'Partiyalar yaroqlilik muddati bo\'yicha', Icon: CalendarClock, color: '#d97706', params: {} },
  { kind: 'reconciliation', label: 'Svereka (WMS↔Smartup)', desc: 'Qoldiq farqlari hisoboti', Icon: Scale, color: '#7c3aed', params: {} },
  { kind: 'temperature', label: 'Harorat (IoT)', desc: 'Sensorlar harorat/namlik tarixi', Icon: Thermometer, color: '#dc2626', params: { hours: 168 } },
] as const

const FORMATS: { f: 'csv' | 'xlsx' | 'pdf'; label: string }[] = [
  { f: 'xlsx', label: 'Excel' }, { f: 'csv', label: 'CSV' }, { f: 'pdf', label: 'PDF' },
]

export default function Reports({ embedded = false }: { embedded?: boolean }) {
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [whId, setWhId] = useState('')
  const wid = whId || (warehouses as any[])[0]?.id
  const [busy, setBusy] = useState<string | null>(null)

  const download = async (kind: any, format: 'csv' | 'xlsx' | 'pdf', params: any) => {
    if (!wid) return
    setBusy(`${kind}-${format}`)
    try {
      await exportReport(kind, wid, format, params)
      toast.success('Yuklandi')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Yuklashda xatolik')
    } finally { setBusy(null) }
  }

  return (
    <div className={embedded ? 'space-y-5' : 'p-4 lg:p-6 space-y-5'}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          {!embedded && (
            <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
              <FileText size={20} className="text-blue-500" /> Hisobotlar
            </h1>
          )}
          {!embedded && <p className="text-slate-400 text-sm mt-0.5">Hisobotlarni Excel / CSV / PDF formatda yuklab oling</p>}
        </div>
        <select className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm bg-white"
          value={wid ?? ''} onChange={e => setWhId(e.target.value)}>
          {(warehouses as any[]).map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {REPORTS.map(r => (
          <div key={r.kind} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0" style={{ background: r.color + '18' }}>
              <r.Icon size={24} style={{ color: r.color }} />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-slate-700">{r.label}</h3>
              <p className="text-xs text-slate-400 mt-0.5 mb-3">{r.desc}</p>
              <div className="flex gap-2">
                {FORMATS.map(({ f, label }) => (
                  <button key={f} onClick={() => download(r.kind, f, r.params)}
                    disabled={busy === `${r.kind}-${f}`}
                    className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 flex items-center gap-1.5 disabled:opacity-50">
                    <Download size={13} /> {busy === `${r.kind}-${f}` ? '…' : label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-slate-400">
        💡 Hisobotlar joriy sklad bo'yicha. Harakat — oxirgi 30 kun, Harorat — oxirgi 7 kun.
      </p>
    </div>
  )
}
