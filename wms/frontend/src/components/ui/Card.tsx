import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean
  padded?: boolean
}

/** Yagona sirt (surface) — barcha panel/karta shu bazadan. */
export function Card({ hover, padded = true, className, children, ...rest }: CardProps) {
  return (
    <div
      className={cn(
        'bg-white rounded-2xl border border-slate-200/60 shadow-card',
        'ring-1 ring-white/40 dark:ring-white/5',
        hover && 'transition-all duration-300 hover:shadow-card-hover hover:-translate-y-0.5',
        padded && 'p-5',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}

export function CardHeader({
  title, subtitle, icon, action, className,
}: {
  title: ReactNode
  subtitle?: ReactNode
  icon?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex items-start justify-between gap-3 mb-4', className)}>
      <div className="flex items-center gap-2.5 min-w-0">
        {icon && <span className="text-blue-500 shrink-0">{icon}</span>}
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-800 text-sm truncate">{title}</h3>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5 truncate">{subtitle}</p>}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}
