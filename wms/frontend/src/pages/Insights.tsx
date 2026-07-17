/**
 * Tahlil markazi — "Analitika" (grafiklar) va "Hisobotlar" (eksport) bitta
 * sahifaga (tablar bilan) birlashtirildi (P3 navigatsiya merge).
 */
import { useState } from 'react'
import { BarChart3, FileText } from 'lucide-react'
import Analytics from './Analytics'
import Reports from './Reports'

export default function Insights({ embedded }: { embedded?: boolean }) {
  const [tab, setTab] = useState<'grafik' | 'hisobot'>('grafik')
  return (
    <div className={embedded ? 'p-4 space-y-4' : 'p-4 lg:p-6 space-y-4'}>
      <div className="flex items-center justify-between flex-wrap gap-3">
        {!embedded && <h1 className="text-xl font-bold text-slate-800">Tahlil</h1>}
        <div className="flex rounded-lg border border-slate-200 overflow-hidden text-sm">
          {([['grafik', 'Analitika', BarChart3], ['hisobot', 'Hisobotlar', FileText]] as const).map(([k, lbl, Icon]) => (
            <button key={k} onClick={() => setTab(k)}
              className={`px-4 py-1.5 flex items-center gap-1.5 transition ${tab === k ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`}>
              <Icon size={14} /> {lbl}
            </button>
          ))}
        </div>
      </div>
      {tab === 'grafik' ? <Analytics embedded /> : <Reports embedded />}
    </div>
  )
}
