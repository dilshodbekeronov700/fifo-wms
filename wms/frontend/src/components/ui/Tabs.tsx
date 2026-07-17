import type { ComponentType, ReactNode } from 'react'
import { cn } from '../../lib/cn'

export interface TabItem {
  id: string
  label: ReactNode
  icon?: ComponentType<{ size?: number; className?: string }>
  badge?: ReactNode
}

/** Segment (pill) uslubidagi tablar — konteyner ichida siljiydigan indikator bilan. */
export function Tabs({
  items, active, onChange, className, size = 'md',
}: {
  items: TabItem[]
  active: string
  onChange: (id: string) => void
  className?: string
  size?: 'sm' | 'md'
}) {
  return (
    <div className={cn('inline-flex items-center gap-1 p-1 rounded-xl bg-slate-100 border border-slate-200/70', className)}>
      {items.map(t => {
        const on = t.id === active
        const Icon = t.icon
        return (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-lg font-medium transition-all',
              size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3.5 py-1.5 text-sm',
              on
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-slate-500 hover:text-slate-700 hover:bg-white/60',
            )}
          >
            {Icon && <Icon size={size === 'sm' ? 13 : 15} />}
            {t.label}
            {t.badge != null && (
              <span className={cn(
                'ml-0.5 min-w-4 px-1 rounded-full text-[10px] leading-4 text-center',
                on ? 'bg-blue-100 text-blue-700' : 'bg-slate-200 text-slate-500',
              )}>
                {t.badge}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
