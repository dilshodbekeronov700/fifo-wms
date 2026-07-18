import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

export function PageHeader({
  title, subtitle, icon, actions, className,
}: {
  title: ReactNode
  subtitle?: ReactNode
  icon?: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex items-start justify-between gap-4 flex-wrap', className)}>
      <div className="flex items-center gap-3.5 min-w-0">
        {icon && (
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white flex items-center justify-center shrink-0 shadow-lg shadow-blue-500/25 ring-1 ring-white/20">
            {icon}
          </div>
        )}
        <div className="min-w-0">
          <h1 className="text-[22px] font-extrabold tracking-tight truncate text-gradient">{title}</h1>
          {subtitle && <p className="text-slate-400 text-sm mt-0.5 truncate">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  )
}
