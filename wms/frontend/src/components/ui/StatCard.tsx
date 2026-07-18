import type { ComponentType, ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '../../lib/cn'
import { cardItem } from '../../lib/motion'
import { AnimatedNumber } from './AnimatedNumber'

type Accent = 'blue' | 'green' | 'orange' | 'purple' | 'teal' | 'rose' | 'amber'

const ACCENT: Record<Accent, { grad: string; a: string; b: string; glow: string }> = {
  blue:   { grad: 'from-blue-500 to-indigo-600',     a: '#3b82f6', b: '#6366f1', glow: 'rgba(59,130,246,.30)' },
  green:  { grad: 'from-emerald-500 to-teal-600',    a: '#10b981', b: '#0d9488', glow: 'rgba(16,185,129,.30)' },
  orange: { grad: 'from-orange-500 to-rose-600',     a: '#f97316', b: '#e11d48', glow: 'rgba(249,115,22,.30)' },
  purple: { grad: 'from-violet-500 to-fuchsia-600',  a: '#8b5cf6', b: '#c026d3', glow: 'rgba(139,92,246,.30)' },
  teal:   { grad: 'from-teal-500 to-cyan-600',       a: '#14b8a6', b: '#0891b2', glow: 'rgba(20,184,166,.30)' },
  rose:   { grad: 'from-rose-500 to-pink-600',       a: '#f43f5e', b: '#db2777', glow: 'rgba(244,63,94,.30)' },
  amber:  { grad: 'from-amber-500 to-orange-600',    a: '#f59e0b', b: '#ea580c', glow: 'rgba(245,158,11,.30)' },
}

/** Qiymat son bo'lsa — count-up animatsiya; aks holda oddiy ko'rsatiladi. */
function toNum(v: ReactNode): number | null {
  if (typeof v === 'number') return v
  if (typeof v === 'string') {
    const n = Number(v.replace(/[\s,]/g, ''))
    return Number.isFinite(n) && v.trim() !== '' ? n : null
  }
  return null
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
  const num = toNum(value)
  return (
    <motion.div
      variants={cardItem}
      whileHover={onClick ? { y: -4 } : undefined}
      whileTap={onClick ? { scale: 0.98 } : undefined}
      onClick={onClick}
      style={{ ['--sc-a' as string]: a.a, ['--sc-b' as string]: a.b, ['--sc-glow' as string]: a.glow }}
      className={cn(
        'stat-card glass sheen-on-hover group relative overflow-hidden rounded-2xl',
        'border border-slate-200/60 p-5 transition-all duration-300',
        onClick ? 'cursor-pointer' : 'cursor-default',
      )}
    >
      {/* katta yumshoq burchak yorug'ligi */}
      <div className={cn('absolute -right-8 -top-10 w-28 h-28 rounded-full opacity-25 blur-3xl bg-gradient-to-br', a.grad)} />
      <div className="relative flex items-start gap-4">
        <div className={cn(
          'w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 bg-gradient-to-br shadow-lg',
          'ring-1 ring-white/20 transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3',
          a.grad,
        )}>
          <Icon size={22} className="text-white drop-shadow" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-slate-500 text-[11px] font-semibold uppercase tracking-wider truncate">{title}</p>
          <p className="text-[26px] leading-tight font-extrabold text-slate-800 mt-1 tracking-tight tabular-nums">
            {num != null ? <AnimatedNumber value={num} /> : (value ?? '—')}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            {sub && <p className="text-xs text-slate-400 truncate">{sub}</p>}
            {trend}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
