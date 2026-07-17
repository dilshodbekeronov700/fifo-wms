import { useEffect, useState } from 'react'
import type { RtStatus } from '../lib/realtime'

/** Real-time ulanish holati — jonli "pulse" nuqta. Hodisa kelganda qisqa yonadi. */
export default function LiveIndicator({ status, lastEventAt }: { status: RtStatus; lastEventAt: number | null }) {
  const [pulse, setPulse] = useState(false)
  useEffect(() => {
    if (!lastEventAt) return
    setPulse(true)
    const t = setTimeout(() => setPulse(false), 700)
    return () => clearTimeout(t)
  }, [lastEventAt])

  const cfg = {
    live: { dot: 'bg-emerald-500', ring: 'bg-emerald-400', label: 'Jonli', text: 'text-emerald-600 dark:text-emerald-400' },
    connecting: { dot: 'bg-amber-500', ring: 'bg-amber-400', label: 'Ulanmoqda', text: 'text-amber-600 dark:text-amber-400' },
    offline: { dot: 'bg-slate-400', ring: 'bg-slate-300', label: 'Oflayn', text: 'text-slate-500' },
  }[status]

  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/85 dark:bg-slate-800/85 backdrop-blur border border-slate-200 dark:border-slate-700 shadow-card text-xs font-medium">
      <span className="relative flex h-2 w-2">
        {status === 'live' && (
          <span className={`absolute inline-flex h-full w-full rounded-full ${cfg.ring} opacity-70 ${pulse ? 'animate-ping' : 'animate-pulse'}`} />
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${cfg.dot}`} />
      </span>
      <span className={cfg.text}>{cfg.label}</span>
    </div>
  )
}
