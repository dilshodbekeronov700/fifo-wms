import { useEffect, useRef, useState } from 'react'

/** Raqamni 0 dan haqiqiy qiymatgacha silliq sanaydi (wow effekt). */
export function AnimatedNumber({
  value, duration = 900, format = true, className,
}: {
  value: number | null | undefined
  duration?: number
  format?: boolean
  className?: string
}) {
  const [display, setDisplay] = useState(0)
  const fromRef = useRef(0)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    if (value == null || Number.isNaN(value)) return
    const from = fromRef.current
    const to = value
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)      // easeOutCubic
      setDisplay(from + (to - from) * eased)
      if (t < 1) rafRef.current = requestAnimationFrame(tick)
      else fromRef.current = to
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [value, duration])

  if (value == null) return <span className={className}>—</span>
  const n = Math.round(display)
  return <span className={className}>{format ? n.toLocaleString() : n}</span>
}
