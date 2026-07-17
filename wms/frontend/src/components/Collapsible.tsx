import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import { accordionContent } from '../lib/motion'
import clsx from 'clsx'

interface Props {
  title: React.ReactNode
  defaultOpen?: boolean
  className?: string
  headerClassName?: string
  children: React.ReactNode
  badge?: React.ReactNode
}

export default function Collapsible({ title, defaultOpen = false, className, headerClassName, children, badge }: Props) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className={clsx('rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden', className)}>
      <button
        onClick={() => setOpen(o => !o)}
        className={clsx(
          'w-full flex items-center justify-between px-5 py-3.5 text-left',
          'bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors',
          headerClassName,
        )}
      >
        <div className="flex items-center gap-2 font-semibold text-slate-700 dark:text-slate-200 text-sm">
          {title}
          {badge}
        </div>
        <motion.span
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="text-slate-400 shrink-0"
        >
          <ChevronDown size={16} />
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="content"
            variants={accordionContent}
            initial="hidden"
            animate="visible"
            exit="exit"
            style={{ overflow: 'hidden' }}
          >
            <div className="px-5 pb-5 pt-2 bg-white dark:bg-slate-900">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
