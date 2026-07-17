import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { createReceipt, getDocuments } from '../lib/api'
import { useAuthStore } from '../store/auth'
import { Plus, ArrowDownToLine, CheckCircle, Clock, XCircle, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { SearchInput, FilterSelect, FilterBar } from '../components/Filters'
import { PageHeader, Card, CardHeader, Button, Textarea, Input, FormField, Badge, EmptyState } from '../components/ui'
import type { Tone } from '../components/ui'

const STATUS_TONE: Record<string, Tone> = {
  draft: 'slate',
  in_progress: 'blue',
  completed: 'green',
  cancelled: 'red',
}
const STATUS_LABEL: Record<string, string> = {
  draft: 'Qoralama',
  in_progress: 'Jarayonda',
  completed: 'Tugallangan',
  cancelled: 'Bekor',
}
const STATUS_ICON: Record<string, any> = {
  draft: AlertCircle,
  in_progress: Clock,
  completed: CheckCircle,
  cancelled: XCircle,
}

export default function Receipt() {
  const qc = useQueryClient()
  const { selectedWarehouseId } = useAuthStore()
  const [showForm, setShowForm] = useState(false)
  const [codes, setCodes] = useState('')
  const [notes, setNotes] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ['documents', selectedWarehouseId, 'receipt'],
    queryFn: () => getDocuments(selectedWarehouseId!, 'receipt'),
    enabled: !!selectedWarehouseId,
    refetchInterval: 20_000,
  })

  const sQ = search.trim().toLowerCase()
  const filteredDocs = (docs as any[]).filter((d: any) => {
    if (status && d.status !== status) return false
    if (!sQ) return true
    return [d.id, d.notes, d.external_id].some(v => String(v ?? '').toLowerCase().includes(sQ))
  })

  const createMut = useMutation({
    mutationFn: () => createReceipt({
      warehouse_id: selectedWarehouseId,
      codes: codes.split('\n').map(s => s.trim()).filter(Boolean),
      notes: notes || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      setShowForm(false)
      setCodes('')
      setNotes('')
      toast.success('Kirim hujjati yaratildi')
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
  })

  if (!selectedWarehouseId) {
    return (
      <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
        <Card className="min-h-[300px] flex items-center justify-center">
          <EmptyState
            icon={ArrowDownToLine}
            title="Sklad tanlanmagan"
            description="Chap paneldan sklad tanlang."
          />
        </Card>
      </div>
    )
  }

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
      <PageHeader
        icon={<ArrowDownToLine size={20} />}
        title="Kirim hujjatlari"
        subtitle="Mahsulot qabul qilish va joylash"
        actions={
          <Button onClick={() => setShowForm(true)} icon={<Plus size={15} />}>
            Yangi kirim
          </Button>
        }
      />

      {/* Create form */}
      {showForm && (
        <Card>
          <CardHeader icon={<Plus size={16} />} title="Yangi kirim hujjati" />
          <div className="space-y-3 max-w-lg">
            <FormField
              label="DataMatrix kodlar (har qatorda bitta)"
              hint={`${codes.split('\n').filter(s => s.trim()).length} ta kod`}
            >
              <Textarea
                rows={6}
                value={codes}
                onChange={e => setCodes(e.target.value)}
                placeholder="010460308339464321dGVzdA==&#10;010460308339464322abc..."
                className="font-mono text-xs resize-none"
              />
            </FormField>
            <FormField label="Izoh (ixtiyoriy)">
              <Input
                type="text"
                value={notes}
                onChange={e => setNotes(e.target.value)}
              />
            </FormField>
            <div className="flex gap-2 pt-1">
              <Button
                onClick={() => createMut.mutate()}
                loading={createMut.isPending}
                disabled={createMut.isPending || !codes.trim()}
              >
                Saqlash
              </Button>
              <Button
                variant="ghost"
                onClick={() => { setShowForm(false); setCodes(''); setNotes('') }}
              >
                Bekor
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Filtr */}
      <FilterBar hasActive={!!search || !!status} onClear={() => { setSearch(''); setStatus('') }}>
        <SearchInput value={search} onChange={setSearch} placeholder="ID / izoh…" className="w-56" />
        <FilterSelect label="Barcha holatlar" value={status} onChange={setStatus} options={[
          { value: 'draft', label: 'Qoralama' },
          { value: 'in_progress', label: 'Jarayonda' },
          { value: 'completed', label: 'Tugallangan' },
          { value: 'cancelled', label: 'Bekor' },
        ]} />
        <span className="text-xs text-slate-400">{filteredDocs.length} / {(docs as any[]).length}</span>
      </FilterBar>

      {/* Documents list */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="rounded-2xl h-16 animate-pulse bg-slate-500/10" />
          ))}
        </div>
      ) : filteredDocs.length === 0 ? (
        <Card>
          <EmptyState
            icon={ArrowDownToLine}
            title={(docs as any[]).length ? 'Filtrga mos hujjat yo\'q' : 'Hali kirim hujjat yo\'q'}
          />
        </Card>
      ) : (
        <Card padded={false} className="overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200/70 bg-slate-500/5">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500">ID</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500">Holat</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500">Izoh</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500">Sana</th>
              </tr>
            </thead>
            <tbody>
              {filteredDocs.map((doc: any) => {
                const Icon = STATUS_ICON[doc.status] ?? AlertCircle
                return (
                  <tr key={doc.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-500/5 transition">
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{doc.id.slice(0, 8)}…</td>
                    <td className="px-4 py-3">
                      <Badge tone={STATUS_TONE[doc.status] ?? 'slate'}>
                        <Icon size={11} />
                        {STATUS_LABEL[doc.status] ?? doc.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-600 text-xs">{doc.notes ?? '—'}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {doc.created_at ? new Date(doc.created_at).toLocaleString('uz-UZ') : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
