/**
 * Karantin (QC) — jo'natishga yopiq partiyalar. Bu yerdan partiyani "bo'shatish"
 * (release → available) yoki "bloklash" mumkin. Karantindagi partiya pick'ga
 * tushmaydi (Qoldiqlar 'available' ko'rsatsa ham).
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getQuarantineBatches, releaseBatch, blockBatch } from '../lib/api'
import { ShieldCheck, CheckCircle2, Ban, PackageX } from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader, Card, Button, Badge, EmptyState } from '../components/ui'
import type { Tone } from '../components/ui'

const STATUS: Record<string, { label: string; tone: Tone }> = {
  quarantine: { label: 'Karantin', tone: 'amber' },
  blocked: { label: 'Bloklangan', tone: 'red' },
}

export default function Quarantine() {
  const qc = useQueryClient()
  const [busy, setBusy] = useState<string | null>(null)
  const { data: batches = [], isLoading } = useQuery({
    queryKey: ['quarantine-batches'],
    queryFn: getQuarantineBatches,
    refetchInterval: 20_000,
  })

  const releaseMut = useMutation({
    mutationFn: (id: string) => releaseBatch(id, 'QC release'),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['quarantine-batches'] }); toast.success('Partiya bo\'shatildi (available)') },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
    onSettled: () => setBusy(null),
  })
  const blockMut = useMutation({
    mutationFn: (id: string) => blockBatch(id, 'QC block'),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['quarantine-batches'] }); toast('Partiya bloklandi', { icon: '🚫' }) },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
    onSettled: () => setBusy(null),
  })

  const rows = batches as any[]

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-[1200px] mx-auto">
      <PageHeader
        icon={<ShieldCheck size={20} />}
        title="Karantin (QC)"
        subtitle="Jo'natishga yopiq partiyalar — bo'shatish yoki bloklash. Karantindagi partiya terishga (pick) tushmaydi."
      />

      {isLoading ? (
        <div className="space-y-2">{[1, 2, 3].map(i => <div key={i} className="rounded-2xl h-16 animate-pulse bg-slate-500/10" />)}</div>
      ) : rows.length === 0 ? (
        <Card><EmptyState icon={ShieldCheck} title="Karantinda partiya yo'q" description="Barcha partiyalar jo'natishga ochiq ✓" /></Card>
      ) : (
        <Card padded={false} className="overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200/70 bg-slate-500/5 text-left text-xs text-slate-500">
                <th className="px-4 py-3 font-semibold">Mahsulot</th>
                <th className="px-4 py-3 font-semibold">GTIN</th>
                <th className="px-4 py-3 font-semibold">Partiya</th>
                <th className="px-4 py-3 font-semibold">Muddat</th>
                <th className="px-4 py-3 font-semibold">Holat</th>
                <th className="px-4 py-3 font-semibold text-right">Amal</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((b: any) => {
                const s = STATUS[b.status] ?? { label: b.status, tone: 'slate' as Tone }
                return (
                  <tr key={b.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-500/5 transition">
                    <td className="px-4 py-3 text-slate-700">{b.product_name ?? <span className="text-slate-400">nomsiz</span>}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{b.gtin ?? '—'}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{b.lot_number ?? '—'}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{b.expiry_date ? String(b.expiry_date).slice(0, 10) : '—'}</td>
                    <td className="px-4 py-3"><Badge tone={s.tone}>{s.label}</Badge></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        {b.status !== 'blocked' ? (
                          <Button size="sm" variant="ghost" className="text-rose-600 hover:bg-rose-500/10"
                            icon={<Ban size={13} />} disabled={busy === b.id}
                            onClick={() => { setBusy(b.id); blockMut.mutate(b.id) }}>Bloklash</Button>
                        ) : null}
                        <Button size="sm" variant="success" icon={<CheckCircle2 size={13} />}
                          loading={busy === b.id && releaseMut.isPending} disabled={busy === b.id}
                          onClick={() => { setBusy(b.id); releaseMut.mutate(b.id) }}>Bo'shatish</Button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </Card>
      )}

      <p className="text-xs text-slate-400 flex items-center gap-1.5">
        <PackageX size={13} /> Karantin — «Sozlamalar → Integratsiya»dagi <b>quarantine_on_receipt</b> yoqilgan bo'lsa, har qabulda partiya avtomatik karantinga tushadi.
      </p>
    </div>
  )
}
