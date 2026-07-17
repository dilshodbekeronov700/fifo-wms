import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

export type Tone = 'slate' | 'blue' | 'green' | 'amber' | 'red' | 'purple' | 'teal' | 'orange'

const TONES: Record<Tone, string> = {
  slate:  'bg-slate-100 text-slate-600',
  blue:   'bg-blue-100 text-blue-700',
  green:  'bg-emerald-100 text-emerald-700',
  amber:  'bg-amber-100 text-amber-700',
  red:    'bg-rose-100 text-rose-600',
  purple: 'bg-violet-100 text-violet-700',
  teal:   'bg-teal-100 text-teal-700',
  orange: 'bg-orange-100 text-orange-700',
}

export function Badge({
  tone = 'slate', dot, children, className,
}: {
  tone?: Tone
  dot?: boolean
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
        TONES[tone],
        className,
      )}
    >
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70" />}
      {children}
    </span>
  )
}
