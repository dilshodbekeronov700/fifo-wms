import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTasks, updateTask } from '../lib/api'
import { useAuthStore } from '../store/auth'
import { ClipboardList, Play, CheckCheck, Clock } from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader, Card, Button, Select, Badge, EmptyState, StatCard } from '../components/ui'
import type { Tone } from '../components/ui'

const TYPE_LABEL: Record<string, string> = {
  putaway: 'Joylash',
  pick: 'Terish',
  replenish: 'To\'ldirish',
  count: 'Inventarizatsiya',
  move: 'Ko\'chirish',
}
const TYPE_TONE: Record<string, Tone> = {
  putaway: 'purple',
  pick: 'blue',
  replenish: 'orange',
  count: 'teal',
  move: 'slate',
}
const STATUS_LABEL: Record<string, string> = {
  pending: 'Kutmoqda',
  assigned: 'Tayinlangan',
  in_progress: 'Jarayonda',
  completed: 'Tugallangan',
  cancelled: 'Bekor',
}
const STATUS_TONE: Record<string, Tone> = {
  pending: 'amber',
  assigned: 'blue',
  in_progress: 'purple',
  completed: 'green',
  cancelled: 'red',
}

const STATUSES = ['', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled']
const TYPES = ['', 'putaway', 'pick', 'replenish', 'count', 'move']

export default function Tasks({ embedded }: { embedded?: boolean }) {
  const qc = useQueryClient()
  const { selectedWarehouseId } = useAuthStore()
  const [filterStatus, setFilterStatus] = useState('')
  const [filterType, setFilterType] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ['tasks', selectedWarehouseId, filterStatus, filterType],
    queryFn: () => getTasks({
      warehouse_id: selectedWarehouseId ?? undefined,
      status: filterStatus || undefined,
      task_type: filterType || undefined,
    }),
    refetchInterval: 15_000,
  })

  const updateMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => updateTask(id, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] })
      toast.success('Vazifa yangilandi')
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Xatolik'),
  })

  const counts = {
    pending: (tasks as any[]).filter((t: any) => t.status === 'pending').length,
    in_progress: (tasks as any[]).filter((t: any) => t.status === 'in_progress').length,
    completed: (tasks as any[]).filter((t: any) => t.status === 'completed').length,
  }

  if (!selectedWarehouseId) {
    return (
      <div className="p-6">
        <EmptyState icon={ClipboardList} title="Sklad tanlanmagan" description="Chap paneldan sklad tanlang." />
      </div>
    )
  }

  return (
    <div className={embedded ? 'p-4 space-y-4' : 'p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto'}>
      {!embedded && (
        <PageHeader
          icon={<ClipboardList size={20} />}
          title="Operator vazifalar"
          subtitle="Picking, putaway, ko'chirish va inventarizatsiya"
        />
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard title="Kutmoqda" value={counts.pending} icon={Clock} accent="amber" />
        <StatCard title="Jarayonda" value={counts.in_progress} icon={Play} accent="blue" />
        <StatCard title="Tugallangan" value={counts.completed} icon={CheckCheck} accent="green" />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <Select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="w-auto">
          <option value="">Barcha holatlar</option>
          {STATUSES.slice(1).map(s => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
        </Select>
        <Select value={filterType} onChange={e => setFilterType(e.target.value)} className="w-auto">
          <option value="">Barcha turlar</option>
          {TYPES.slice(1).map(t => <option key={t} value={t}>{TYPE_LABEL[t]}</option>)}
        </Select>
      </div>

      {/* Tasks list */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4].map(i => <div key={i} className="rounded-2xl h-16 animate-pulse bg-slate-500/10" />)}
        </div>
      ) : (tasks as any[]).length === 0 ? (
        <Card>
          <EmptyState icon={ClipboardList} title="Vazifa topilmadi" />
        </Card>
      ) : (
        <div className="space-y-2">
          {(tasks as any[]).map((task: any) => (
            <Card key={task.id} padded={false} className="overflow-hidden">
              <div
                className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-slate-500/5 transition"
                onClick={() => setExpanded(expanded === task.id ? null : task.id)}
              >
                <Badge tone={TYPE_TONE[task.task_type] ?? 'slate'}>
                  {TYPE_LABEL[task.task_type] ?? task.task_type}
                </Badge>
                <span className="font-mono text-xs text-slate-400 shrink-0">{task.id.slice(0, 8)}…</span>
                <span className="flex-1 min-w-0" />
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs text-slate-400">Prioritet: {task.priority}</span>
                  <Badge tone={STATUS_TONE[task.status] ?? 'slate'}>
                    {STATUS_LABEL[task.status] ?? task.status}
                  </Badge>
                </div>
              </div>

              {expanded === task.id && (
                <div className="border-t border-slate-100 px-4 py-3 bg-slate-500/5 space-y-3">
                  {/* Payload preview */}
                  {task.payload && Object.keys(task.payload).length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-slate-500 mb-1">Payload</p>
                      <pre className="text-xs text-slate-600 bg-white rounded p-2 border border-slate-100 overflow-x-auto max-h-32">
                        {JSON.stringify(task.payload, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Pick route */}
                  {task.task_type === 'pick' && task.payload?.route && (
                    <div>
                      <p className="text-xs font-medium text-slate-500 mb-1">Marshrut</p>
                      <div className="space-y-1">
                        {task.payload.route.map((stop: any, i: number) => (
                          <div key={i} className="flex items-center gap-2 text-xs text-slate-600">
                            <span className="w-5 h-5 bg-blue-500/10 text-blue-700 rounded-full flex items-center justify-center font-bold text-xs shrink-0">{i + 1}</span>
                            <span className="font-mono">{stop.location_id?.slice(0, 8)}…</span>
                            <span className="text-slate-400">→ {stop.take_qty} dona</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2">
                    {task.status === 'pending' && (
                      <Button
                        size="sm"
                        onClick={() => updateMut.mutate({ id: task.id, status: 'in_progress' })}
                        disabled={updateMut.isPending}
                      >
                        Boshlash
                      </Button>
                    )}
                    {task.status === 'in_progress' && (
                      <Button
                        size="sm"
                        variant="success"
                        onClick={() => updateMut.mutate({ id: task.id, status: 'completed' })}
                        disabled={updateMut.isPending}
                      >
                        Tugallash
                      </Button>
                    )}
                    {['pending', 'assigned', 'in_progress'].includes(task.status) && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => updateMut.mutate({ id: task.id, status: 'cancelled' })}
                        disabled={updateMut.isPending}
                        className="text-rose-600 hover:bg-rose-500/10"
                      >
                        Bekor qilish
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
