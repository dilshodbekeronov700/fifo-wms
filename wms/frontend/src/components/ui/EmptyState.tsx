import type { ComponentType, ReactNode } from 'react'
import { cn } from '../../lib/cn'

export function EmptyState({
  icon: Icon, title, description, action, className,
}: {
  icon?: ComponentType<{ size?: number; className?: string }>
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center text-center py-12 px-6', className)}>
      {Icon && (
        <div className="w-14 h-14 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mb-4">
          <Icon size={26} />
        </div>
      )}
      <p className="text-slate-700 font-medium text-sm">{title}</p>
      {description && <p className="text-slate-400 text-sm mt-1 max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
