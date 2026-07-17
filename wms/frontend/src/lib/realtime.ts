import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { subscribeRealtime } from './api'

/**
 * Real-time SSE — server hodisalarini (stock / reservation) jonli qabul qiladi.
 * Avval `subscribeRealtime()` yozilgan edi, lekin hech qayerda ISHLATILMAGAN
 * (dead code). Endi:
 *   - React Query keshini invalidatsiya qiladi (jadval/karta o'zi yangilanadi),
 *   - ulanish holatini beradi (jonli indikator uchun),
 *   - lokal event-bus orqali 3D twin kabi komponentlarga uzatadi.
 */

export type RealtimeEvent = {
  type: 'stock' | 'reservation' | string
  location_id?: string
  product_id?: string
  qty?: number
  code?: string
  status?: string
  event?: string
}

type Listener = (e: RealtimeEvent) => void
const listeners = new Set<Listener>()

/** Komponent 3D twin kabi xom hodisalarni tinglashi uchun. */
export function onRealtimeEvent(fn: Listener): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export type RtStatus = 'connecting' | 'live' | 'offline'

/** Ilova bo'ylab bir marta (Layout'da) chaqiriladi. */
export function useRealtime(): { status: RtStatus; lastEventAt: number | null } {
  const qc = useQueryClient()
  const [status, setStatus] = useState<RtStatus>('connecting')
  const [lastEventAt, setLastEventAt] = useState<number | null>(null)
  const esRef = useRef<EventSource | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let disposed = false

    const connect = () => {
      if (disposed) return
      if (!localStorage.getItem('access_token')) {
        setStatus('offline')
        retryRef.current = setTimeout(connect, 3000)
        return
      }
      setStatus('connecting')
      const es = subscribeRealtime()
      esRef.current = es

      es.onopen = () => !disposed && setStatus('live')

      es.onmessage = (msg) => {
        if (disposed) return
        setStatus('live')
        setLastEventAt(Date.now())
        let data: RealtimeEvent
        try { data = JSON.parse(msg.data) } catch { return }
        // Tegishli so'rov keshlarini yangilaymiz — UI o'zi jonli yangilanadi.
        if (data.type === 'stock') {
          qc.invalidateQueries({ queryKey: ['all-locations'] })
          qc.invalidateQueries({ queryKey: ['stock'] })
          qc.invalidateQueries({ queryKey: ['dashboard'] })
        } else if (data.type === 'reservation') {
          qc.invalidateQueries({ queryKey: ['reservations'] })
          qc.invalidateQueries({ queryKey: ['all-locations'] })
        }
        listeners.forEach(fn => { try { fn(data) } catch { /* ignore */ } })
      }

      es.onerror = () => {
        if (disposed) return
        setStatus('offline')
        es.close()
        esRef.current = null
        retryRef.current = setTimeout(connect, 3000)   // avtomatik qayta ulanish
      }
    }

    connect()
    return () => {
      disposed = true
      if (retryRef.current) clearTimeout(retryRef.current)
      esRef.current?.close()
    }
  }, [qc])

  return { status, lastEventAt }
}
