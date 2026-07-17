/**
 * Qoldiqlar markazi — "Qoldiqlar", "Qoldiq batafsil" va "ERP svereka" tablar.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layers, Boxes, GitCompareArrows } from 'lucide-react'
import Stock from './Stock'
import StockView from './StockView'
import { getWarehouses, getSmartupReconciliation } from '../lib/api'
import { PageHeader, Card, Select, Badge, EmptyState, Tabs } from '../components/ui'
import type { Tone } from '../components/ui'

export default function StockCenter({ embedded }: { embedded?: boolean }) {
  const [tab, setTab] = useState<'umumiy' | 'batafsil' | 'svereka'>('umumiy')
  const tabsEl = (
    <Tabs
      items={[
        { id: 'umumiy', label: 'Umumiy', icon: Layers },
        { id: 'batafsil', label: 'Batafsil', icon: Boxes },
        { id: 'svereka', label: 'ERP svereka', icon: GitCompareArrows },
      ]}
      active={tab}
      onChange={(id) => setTab(id as typeof tab)}
    />
  )
  return (
    <div className={embedded ? 'p-4 space-y-4' : 'p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto'}>
      {embedded ? (
        <div className="flex items-center justify-end flex-wrap gap-3">{tabsEl}</div>
      ) : (
        <PageHeader
          icon={<Boxes size={20} />}
          title="Qoldiqlar"
          actions={tabsEl}
        />
      )}
      {tab === 'umumiy' && <Stock embedded />}
      {tab === 'batafsil' && <StockView embedded />}
      {tab === 'svereka' && <ReconciliationTab />}
    </div>
  )
}

const DIR: Record<string, { label: string; tone: Tone }> = {
  match:    { label: 'Mos',      tone: 'green' },
  wms_more: { label: 'WMS ko‘p', tone: 'amber' },
  erp_more: { label: 'ERP ko‘p', tone: 'purple' },
  missing:  { label: 'Faqat bitta', tone: 'slate' },
}

function ReconciliationTab() {
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [whId, setWhId] = useState('')
  const wid = whId || (warehouses as any[])[0]?.id

  const { data, isFetching } = useQuery({
    queryKey: ['smartup-reconciliation', wid],
    queryFn: () => getSmartupReconciliation(wid),
    enabled: !!wid,
  })

  const lines = data?.lines ?? []
  const s = data?.summary ?? {}

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <Select className="w-auto min-w-40" value={wid ?? ''} onChange={e => setWhId(e.target.value)}>
          {(warehouses as any[]).map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
        </Select>
        {isFetching && <span className="text-xs text-slate-400">Yuklanmoqda…</span>}
        {data && !data.erp_compared && (
          <span className="text-xs text-amber-600">⚠ ERP bilan solishtirilmadi: {data.erp_error || 'sklad kodi yo‘q'}</span>
        )}
      </div>

      {data?.erp_compared && (
        <div className="flex flex-wrap gap-2">
          <Badge tone="green">Mos: {s.match}</Badge>
          <Badge tone="red">Farqli: {s.mismatch}</Badge>
          <Badge tone="blue">Faqat WMS: {s.only_wms}</Badge>
          <Badge tone="purple">Faqat ERP: {s.only_erp}</Badge>
        </div>
      )}

      <Card padded={false} className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-slate-500 text-xs">
              <tr className="border-b border-slate-100">
                <th className="text-left px-3 py-2">Mahsulot kodi</th>
                <th className="text-right px-3 py-2">WMS</th>
                <th className="text-right px-3 py-2">Smartup (ERP)</th>
                <th className="text-right px-3 py-2">Farq</th>
                <th className="text-left px-3 py-2">Holat</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((ln: any, i: number) => {
                const d = DIR[ln.direction] ?? DIR.missing
                return (
                  <tr key={i} className="border-t border-slate-100">
                    <td className="px-3 py-1.5 font-mono text-xs">{ln.product_code ?? '—'}{ln.batch ? <span className="text-slate-400"> · {ln.batch}</span> : null}</td>
                    <td className="px-3 py-1.5 text-right">{ln.wms_qty}</td>
                    <td className="px-3 py-1.5 text-right">{ln.smartup_qty ?? '—'}</td>
                    <td className={`px-3 py-1.5 text-right font-medium ${ln.diff === 0 ? 'text-slate-400' : ln.diff > 0 ? 'text-amber-600' : 'text-purple-600'}`}>{ln.diff > 0 ? `+${ln.diff}` : ln.diff}</td>
                    <td className="px-3 py-1.5"><Badge tone={d.tone}>{d.label}</Badge></td>
                  </tr>
                )
              })}
              {lines.length === 0 && (
                <tr><td colSpan={5} className="py-10">
                  <EmptyState icon={GitCompareArrows} title="Ma'lumot yo'q" />
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
