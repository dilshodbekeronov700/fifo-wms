/**
 * Boshqaruv markazi (P4) — bitta sahifa, 4 tab:
 *   Foydalanuvchilar  — sign-up tasdiqlash, rol biriktirish, faollashtirish
 *   Rollar va ruxsatlar — rollarga ruxsat berish (super-admin/admin)
 *   O'zgarishlar (audit) — kim/qachon/nima qildi
 *   Integratsiya       — Smartup + Asl Belgisi holati va WMS↔Smartup solishtirish
 */
import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getAdminUsers, approveUser, rejectUser, updateAdminUser,
  getRoles, createRole, setRolePermissions, getPermissions, getAuditLog,
  getIntegrationStatus, getReconciliation, getWarehouses,
} from '../lib/api'
import {
  Users, Shield, History, Plug, Check, X, UserCheck, RefreshCw, Plus, UserCog,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader, Card, Button, Select, Badge, EmptyState, Tabs } from '../components/ui'

type Tab = 'users' | 'roles' | 'audit' | 'integration'

const ADMIN_TABS = [
  { id: 'users', label: 'Foydalanuvchilar', icon: Users },
  { id: 'roles', label: 'Rollar', icon: Shield },
  { id: 'audit', label: "O'zgarishlar", icon: History },
  { id: 'integration', label: 'Integratsiya', icon: Plug },
]

export default function AdminCenter({ embedded }: { embedded?: boolean }) {
  const [tab, setTab] = useState<Tab>('users')

  const tabsBar = <Tabs items={ADMIN_TABS} active={tab} onChange={id => setTab(id as Tab)} />

  const body = (
    <>
      {tab === 'users' && <UsersTab />}
      {tab === 'roles' && <RolesTab />}
      {tab === 'audit' && <AuditTab />}
      {tab === 'integration' && <IntegrationTab />}
    </>
  )

  if (embedded) {
    return (
      <div className="p-4 space-y-4">
        {tabsBar}
        {body}
      </div>
    )
  }

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
      <PageHeader
        icon={<UserCog size={20} />}
        title="Boshqaruv"
        subtitle="Foydalanuvchilar, rollar, audit va integratsiya"
        actions={tabsBar}
      />
      {body}
    </div>
  )
}

// ─── Users ───────────────────────────────────────────────────────────────────
function UsersTab() {
  const qc = useQueryClient()
  const [status, setStatus] = useState('all')
  const { data: users = [] } = useQuery({ queryKey: ['admin-users', status], queryFn: () => getAdminUsers(status) })
  const { data: roles = [] } = useQuery({ queryKey: ['admin-roles'], queryFn: getRoles })
  const reload = () => qc.invalidateQueries({ queryKey: ['admin-users'] })

  const [picker, setPicker] = useState<{ id: string; roleIds: string[] } | null>(null)

  const doApprove = async (id: string, roleIds: string[]) => {
    try { await approveUser(id, roleIds); toast.success('Tasdiqlandi'); setPicker(null); reload() }
    catch { toast.error('Xatolik') }
  }
  const doReject = async (id: string) => {
    if (!confirm('Rad etilsinmi?')) return
    try { await rejectUser(id); toast.success('Rad etildi'); reload() } catch { toast.error('Xatolik') }
  }
  const toggleActive = async (u: any) => {
    try { await updateAdminUser(u.id, { is_active: !u.is_active }); reload() } catch { toast.error('Xatolik') }
  }
  const setRole = async (u: any, roleId: string) => {
    try { await updateAdminUser(u.id, { role_ids: roleId ? [roleId] : [] }); toast.success('Rol o\'zgartirildi'); reload() }
    catch { toast.error('Xatolik') }
  }

  const STATUS_FILTERS = [
    { id: 'all', label: 'Hammasi' },
    { id: 'pending', label: 'Tasdiq kutmoqda' },
    { id: 'active', label: 'Faol' },
    { id: 'inactive', label: 'Nofaol' },
  ]

  return (
    <div className="space-y-3">
      <Tabs
        size="sm"
        items={STATUS_FILTERS}
        active={status}
        onChange={setStatus}
      />
      <Card padded={false} className="overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-500/5">
            <tr className="text-left text-slate-500">
              {['Email', 'Ism', 'Holat', 'Rol', 'Amal'].map(h => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {users.map((u: any) => (
              <tr key={u.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-medium text-slate-700">{u.email}</td>
                <td className="px-3 py-2 text-slate-600">{u.full_name}</td>
                <td className="px-3 py-2">
                  {!u.is_approved ? <Badge tone="amber">Tasdiq kutmoqda</Badge>
                    : u.is_active ? <Badge tone="green">Faol</Badge>
                    : <Badge tone="slate">Nofaol</Badge>}
                  {u.is_superadmin && <Badge tone="purple" className="ml-1">Super</Badge>}
                </td>
                <td className="px-3 py-2">
                  {u.is_superadmin ? '—' : (
                    <Select className="w-auto min-w-32 h-8 text-xs"
                      value={u.role_ids?.[0] ?? ''} onChange={e => setRole(u, e.target.value)}>
                      <option value="">— rolsiz —</option>
                      {roles.map((r: any) => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </Select>
                  )}
                </td>
                <td className="px-3 py-2">
                  {!u.is_approved ? (
                    <div className="flex gap-1">
                      <Button size="sm" variant="success" onClick={() => setPicker({ id: u.id, roleIds: [] })} icon={<UserCheck size={12} />}>Tasdiqlash</Button>
                      <Button size="sm" variant="danger" onClick={() => doReject(u.id)} className="px-2"><X size={12} /></Button>
                    </div>
                  ) : !u.is_superadmin && (
                    <Button size="sm" variant="secondary" onClick={() => toggleActive(u)}>
                      {u.is_active ? 'O\'chirish' : 'Faollashtirish'}
                    </Button>
                  )}
                </td>
              </tr>
            ))}
            {users.length === 0 && <tr><td colSpan={5}><EmptyState icon={Users} title="Foydalanuvchi yo'q" /></td></tr>}
          </tbody>
        </table>
      </Card>

      {/* Approve with role picker */}
      {picker && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setPicker(null)}>
          <Card className="w-80 space-y-3" onClick={(e: any) => e.stopPropagation()}>
            <h3 className="font-semibold text-slate-800 flex items-center gap-2"><UserCheck size={18} className="text-emerald-600" /> Tasdiqlash + rol</h3>
            <p className="text-xs text-slate-500">Foydalanuvchiga rol biriktiring (keyin o'zgartirsa bo'ladi).</p>
            <div className="space-y-1 max-h-60 overflow-auto">
              {roles.map((r: any) => (
                <label key={r.id} className="flex items-center gap-2 text-sm p-1.5 rounded hover:bg-slate-500/5">
                  <input type="radio" name="role" checked={picker.roleIds[0] === r.id}
                    onChange={() => setPicker({ ...picker, roleIds: [r.id] })} />
                  {r.name} <span className="text-xs text-slate-400">({r.permissions?.length ?? 0} ruxsat)</span>
                </label>
              ))}
            </div>
            <div className="flex gap-2">
              <Button variant="success" className="flex-1" onClick={() => doApprove(picker.id, picker.roleIds)} icon={<Check size={14} />}>Tasdiqlash</Button>
              <Button variant="secondary" onClick={() => setPicker(null)}>Bekor</Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

// ─── Roles & permissions ──────────────────────────────────────────────────────
function RolesTab() {
  const qc = useQueryClient()
  const { data: roles = [] } = useQuery({ queryKey: ['admin-roles'], queryFn: getRoles })
  const { data: perms = [] } = useQuery({ queryKey: ['admin-perms'], queryFn: getPermissions })
  const [sel, setSel] = useState<string | null>(null)
  const [draft, setDraft] = useState<Set<string>>(new Set())
  const reload = () => qc.invalidateQueries({ queryKey: ['admin-roles'] })

  const selRole = roles.find((r: any) => r.id === sel)
  const grouped = useMemo(() => {
    const g: Record<string, any[]> = {}
    for (const p of perms) (g[p.resource] ??= []).push(p)
    return g
  }, [perms])

  const openRole = (r: any) => { setSel(r.id); setDraft(new Set(r.permission_ids)) }
  const toggle = (id: string) => setDraft(d => { const n = new Set(d); n.has(id) ? n.delete(id) : n.add(id); return n })
  const save = async () => {
    if (!sel) return
    try { await setRolePermissions(sel, [...draft]); toast.success('Saqlandi'); reload() }
    catch (e: any) { toast.error(e?.response?.data?.detail === 'system_role_readonly' ? 'Tizim roli o\'zgartirilmaydi' : 'Xatolik') }
  }
  const addRole = async () => {
    const name = prompt('Yangi rol nomi:')
    if (!name) return
    try { await createRole(name); toast.success('Rol yaratildi'); reload() } catch { toast.error('Xatolik') }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[256px_1fr] gap-4 items-start">
      <div className="space-y-2">
        <Button variant="secondary" className="w-full border-dashed" onClick={addRole} icon={<Plus size={14} />}>Yangi rol</Button>
        {roles.map((r: any) => {
          const on = sel === r.id
          return (
            <button key={r.id} onClick={() => openRole(r)}
              className={`w-full text-left px-3 py-2 rounded-xl border text-sm transition ${on ? 'border-blue-500/40 bg-blue-500/10' : 'border-slate-200 hover:bg-slate-500/5'}`}>
              <div className="font-medium text-slate-700 flex items-center justify-between gap-2">
                {r.name}
                {r.is_system && <Badge tone="slate">tizim</Badge>}
              </div>
              <div className="text-xs text-slate-400 mt-0.5">{r.permissions?.length ?? 0} ruxsat · {r.user_count} foydalanuvchi</div>
            </button>
          )
        })}
      </div>
      <Card>
        {!selRole ? <EmptyState icon={Shield} title="Rol tanlang" description="Ruxsatlarni ko'rish/o'zgartirish uchun rol tanlang" /> : (
          <>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-slate-700">{selRole.name} {selRole.is_system && <span className="text-xs text-slate-400">(tizim roli — faqat ko'rish)</span>}</h3>
              {!selRole.is_system && <Button size="sm" onClick={save}>Saqlash</Button>}
            </div>
            <div className="grid md:grid-cols-2 gap-x-6 gap-y-3 max-h-[60vh] overflow-auto">
              {Object.entries(grouped).map(([res, list]) => (
                <div key={res}>
                  <div className="text-xs font-semibold uppercase text-slate-400 mb-1">{res}</div>
                  {list.map((p: any) => (
                    <label key={p.id} className="flex items-center gap-2 text-sm py-0.5">
                      <input type="checkbox" disabled={selRole.is_system}
                        checked={draft.has(p.id)} onChange={() => toggle(p.id)} />
                      <span className="text-slate-600">{p.action}</span>
                    </label>
                  ))}
                </div>
              ))}
            </div>
          </>
        )}
      </Card>
    </div>
  )
}

// ─── Audit ─────────────────────────────────────────────────────────────────────
function AuditTab() {
  const { data: logs = [] } = useQuery({ queryKey: ['admin-audit'], queryFn: () => getAuditLog({ limit: 200 }) })
  return (
    <Card padded={false} className="overflow-auto max-h-[72vh]">
      <table className="w-full text-sm">
        <thead className="bg-slate-500/5 sticky top-0">
          <tr className="text-left text-slate-500">
            {['Vaqt', 'Kim', 'Amal', 'Resurs', 'Tafsilot'].map(h => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {logs.map((a: any) => (
            <tr key={a.id} className="border-t border-slate-100 hover:bg-slate-500/5">
              <td className="px-3 py-1.5 text-slate-500 whitespace-nowrap">{a.created_at?.replace('T', ' ').slice(0, 19)}</td>
              <td className="px-3 py-1.5 text-slate-600">{a.user_email ?? '—'}</td>
              <td className="px-3 py-1.5"><Badge tone="slate">{a.action}</Badge></td>
              <td className="px-3 py-1.5 text-slate-500">{a.resource}</td>
              <td className="px-3 py-1.5 text-slate-400 text-xs font-mono max-w-md truncate">{a.detail ? JSON.stringify(a.detail) : ''}</td>
            </tr>
          ))}
          {logs.length === 0 && <tr><td colSpan={5}><EmptyState icon={History} title="Yozuv yo'q" /></td></tr>}
        </tbody>
      </table>
    </Card>
  )
}

// ─── Integration + reconciliation ───────────────────────────────────────────────
function IntegrationTab() {
  const { data: status } = useQuery({ queryKey: ['integration-status'], queryFn: getIntegrationStatus, refetchInterval: 20000 })
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [wid, setWid] = useState('')
  const w = wid || warehouses[0]?.id
  const [recon, setRecon] = useState<any>(null)
  const [busy, setBusy] = useState(false)

  const runRecon = async () => {
    if (!w) return
    setBusy(true)
    try { setRecon(await getReconciliation(w)) } catch (e: any) { toast.error(e?.response?.data?.detail ?? 'Xatolik') }
    finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      {/* Connector cards */}
      <div className="grid md:grid-cols-2 gap-4">
        {(status?.connectors ?? []).map((c: any) => (
          <Card key={c.type}>
            <div className="flex items-center justify-between">
              <div className="font-semibold text-slate-700 capitalize flex items-center gap-2"><Plug size={16} className="text-blue-500" /> {c.type}</div>
              <Badge tone={c.is_active ? 'green' : 'slate'} dot>{c.is_active ? 'Faol' : 'O\'chirilgan'}</Badge>
            </div>
            <div className="mt-2 text-xs text-slate-500 space-y-0.5">
              {c.last_product_sync && <div>Mahsulot sync: {c.last_product_sync.replace('T', ' ').slice(0, 16)}</div>}
              {c.last_balance_sync && <div>Qoldiq sync: {c.last_balance_sync.replace('T', ' ').slice(0, 16)}</div>}
              <div className="flex gap-3 pt-1">
                <span className="text-amber-600">Navbatda: {c.queue?.pending ?? 0}</span>
                <span className="text-emerald-600">Yuborilgan: {c.queue?.sent ?? 0}</span>
                <span className="text-rose-600">Xato: {c.queue?.failed ?? 0}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>
      {(status?.recent_failures ?? []).length > 0 && (
        <Card className="border-rose-500/30 bg-rose-500/5">
          <div className="font-semibold text-rose-700 mb-1 text-sm">So'nggi xatolar</div>
          {status.recent_failures.map((f: any, i: number) => (
            <div key={i} className="text-xs text-rose-600 font-mono">{f.connector} · {f.event_type} · {f.error}</div>
          ))}
        </Card>
      )}

      {/* WMS ↔ Smartup reconciliation */}
      <Card className="space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h3 className="font-semibold text-slate-700">WMS ↔ Smartup solishtirish (svereka)</h3>
          <div className="flex gap-2">
            <Select className="w-auto min-w-40" value={w ?? ''} onChange={e => setWid(e.target.value)}>
              {warehouses.map((wh: any) => <option key={wh.id} value={wh.id}>{wh.name}</option>)}
            </Select>
            <Button onClick={runRecon} loading={busy} icon={<RefreshCw size={14} />}>Solishtirish</Button>
          </div>
        </div>
        {recon && (
          <>
            <div className="flex flex-wrap gap-3 text-sm">
              {[['Mos', recon.summary?.match, '#16a34a'], ['Farqli', recon.summary?.mismatch, '#d97706'],
                ['Faqat WMS', recon.summary?.only_wms, '#3b82f6'], ['Faqat ERP', recon.summary?.only_erp, '#dc2626']].map(([l, v, c]) => (
                <div key={l as string} className="px-3 py-1.5 rounded-lg border border-slate-200 flex items-baseline gap-1.5">
                  <span className="font-bold" style={{ color: c as string }}>{v ?? 0}</span><span className="text-xs text-slate-400">{l}</span>
                </div>
              ))}
            </div>
            {recon.erp_error && <div className="text-xs text-amber-600">Smartup ulanmadi: {recon.erp_error}</div>}
            <div className="overflow-auto max-h-80 border border-slate-100 rounded-lg">
              <table className="w-full text-sm">
                <thead className="bg-slate-500/5 sticky top-0"><tr className="text-left text-slate-500">
                  {['Mahsulot', 'Partiya', 'WMS', 'Smartup', 'Farq'].map(h => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}
                </tr></thead>
                <tbody>
                  {(recon.lines ?? []).map((l: any, i: number) => (
                    <tr key={i} className={`border-t border-slate-100 ${l.direction !== 'match' ? 'bg-amber-500/5' : ''}`}>
                      <td className="px-3 py-1.5 text-slate-700">{l.product_code ?? l.product_id ?? '—'}</td>
                      <td className="px-3 py-1.5 text-slate-500">{l.batch ?? '—'}</td>
                      <td className="px-3 py-1.5">{l.wms_qty}</td>
                      <td className="px-3 py-1.5">{l.smartup_qty ?? '—'}</td>
                      <td className="px-3 py-1.5 font-medium" style={{ color: l.diff === 0 ? '#16a34a' : '#d97706' }}>{l.diff > 0 ? '+' : ''}{l.diff}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        {!recon && <div className="text-sm text-slate-400">Solishtirishni boshlash uchun tugmani bosing.</div>}
      </Card>
    </div>
  )
}
