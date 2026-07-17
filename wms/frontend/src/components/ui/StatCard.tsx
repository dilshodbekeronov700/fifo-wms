import type { ComponentType, ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '../../lib/cn'
import { cardItem } from '../../lib/motion'

type Accent = 'blue' | 'green' | 'orange' | 'purple' | 'teal' | 'rose' | 'amber'

const ACCENT: Record<Accent, { grad: string; soft: string; text: string }> = {
  blue:   { grad: 'from-blue-500 to-blue-600',       soft: 'bg-blue-500/10',    text: 'text-blue-600' },
  green:  { grad: 'from-emerald-500 to-emerald-600', soft: 'bg-emerald-500/10', text: 'text-emerald-600' },
  orange: { grad: 'from-orange-500 to-orange-600',   soft: 'bg-orange-500/10',  text: 'text-orange-600' },
  purple: { grad: 'from-violet-500 to-violet-600',   soft: 'bg-violet-500/10',  text: 'text-violet-600' },
  teal:   { grad: 'from-teal-500 to-teal-600',       soft: 'bg-teal-500/10',    text: 'text-teal-600' },
  rose:   { grad: 'from-rose-500 to-rose-600',       soft: 'bg-rose-500/10',    text: 'text-rose-600' },
  amber:  { grad: 'from-amber-500 to-amber-600',     soft: 'bg-amber-500/10',   text: 'text-amber-600' },
}

export function StatCard({
  title, value, sub, icon: Icon, accent = 'blue', onClick, trend,
}: {
  title: ReactNode
  value: ReactNode
  sub?: ReactNode
  icon: ComponentType<{ size?: number; className?: string }>
  accent?: Accent
  onClick?: () => void
  trend?: ReactNode
}) {
  const a = ACCENT[accent]
  return (
    <motion.div
      variants={cardItem}
      whileHover={onClick ? { y: -3 } : undefined}
      onClick={onClick}
      className={cn(
        'group relative overflow-hidden bg-white rounded-2xl border border-slate-200/70 p-5',
        'shadow-card transition-shadow',
        onClick ? 'cursor-pointer hover:shadow-card-hover' : 'cursor-default',
      )}
    >
      {/* nozik burchak aksent */}
      <div className={cn('absolute -right-6 -top-6 w-20 h-20 rounded-full opacity-60 blur-2xl', a.soft)} />
      <div className="relative flex items-start gap-4">
        <div className={cn('w-11 h-11 rounded-xl flex items-center justify-center shrink-0 bg-gradient-to-br shadow-sm', a.grad)}>
          <Icon size={21} className="text-white" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-slate-400 text-xs font-medium truncate">{title}</p>
          <p className="text-2xl font-bold text-slate-800 mt-0.5 tracking-tight">{value ?? '—'}</p>
          <div className="flex items-center gap-2">
            {sub && <p className="text-xs text-slate-400 truncate">{sub}</p>}
            {trend}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
