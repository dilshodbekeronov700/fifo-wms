import { lazy, Suspense, useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Settings as SettingsIcon, User, Shield, Plug, RefreshCw,
  CheckCircle2, XCircle, Activity, AlertTriangle, Bell, UserCog, ShieldCheck,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/auth'
import { useI18n, localeLabels, allLocales, type Locale } from '../lib/i18n'
import {
  getConnectorSpecs, getConnectors, upsertConnector,
  testConnector, syncSmartupProducts, syncAslbelgisiProducts,
  seedOcardProducts, getIntegrationStatus, approvePush, rejectPush, pullSmartup,
  getErpPolicy, setErpPolicy, getWarehouses, getSmartupCurrentOrg, updateWarehouse,
} from '../lib/api'
import Collapsible from '../components/Collapsible'
import { tabFade } from '../lib/motion'
import { PageHeader, Card, CardHeader, Button, Input, FormField, Badge, Tabs } from '../components/ui'

const AdminCenter = lazy(() => import('./AdminCenter'))
const Alerts      = lazy(() => import('./Alerts'))

type Field = { name: string; label: string; secret: boolean; required: boolean; placeholder?: string; help?: string }
type Spec = { type: string; kind: string; label: string; fields: Field[] }
type Existing = { connector_type: string; is_active: boolean; has_credentials: boolean; values: Record<string, any> }

const SETTINGS_TABS = [
  { id: 'general',  label: 'Umumiy',       icon: SettingsIcon },
  { id: 'integrations', label: 'Integratsiyalar', icon: Plug },
  { id: 'users',    label: 'Foydalanuvchilar', icon: UserCog },
  { id: 'alerts',   label: 'Ogohlantirishlar', icon: Bell },
]

function ConnectorForm({ spec, existing, onSaved }: { spec: Spec; existing?: Existing; onSaved: () => void }) {
  const [values, setValues] = useState<Record<string, any>>({})
  const [busy, setBusy] = useState(false)
  const [testRes, setTestRes] = useState<null | { ok: boolean; warn?: boolean; detail?: string }>(null)

  useEffect(() => { setValues(existing?.values ?? {}) }, [existing])

  const save = async () => {
    const missing = spec.fields.filter(f => f.required && !values[f.name])
    if (missing.length) { toast.error('Majburiy maydonlar: ' + missing.map(f => f.label).join(', ')); return }
    setBusy(true)
    try {
      await upsertConnector({ connector_type: spec.type, credentials: values, settings: {} })
      toast.success(`${spec.label} saqlandi`); onSaved()
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? 'Xatolik') }
    finally { setBusy(false) }
  }

  const runTest = async () => {
    setBusy(true); setTestRes(null)
    try {
      const r = await testConnector(spec.type)
      const rateLimited = r.status === 'rate_limited'
      setTestRes({ ok: r.status === 'ok', warn: rateLimited, detail: r.detail })
      if (r.status === 'ok') toast.success('Ulanish muvaffaqiyatli')
      else if (rateLimited) toast('⏳ ' + (r.detail ?? 'So\'rovlar chegarasi'))
      else toast.error('Ulanmadi: ' + (r.detail ?? ''))
    } catch (e: any) { setTestRes({ ok: false, detail: e?.response?.data?.detail }); toast.error('Test xatosi') }
    finally { setBusy(false) }
  }

  const doSync = async () => {
    setBusy(true)
    try {
      const r = spec.type === 'aslbelgisi'
        ? await syncAslbelgisiProducts()
        : await syncSmartupProducts(false)
      toast.success(`Sync: +${r.created} yangi, ${r.updated} yangilandi`)
    }
    catch (e: any) { toast.error(e?.response?.data?.detail ?? 'Sync xatosi') }
    finally { setBusy(false) }
  }

  return (
    <Collapsible
      title={
        <span className="flex items-center gap-2">
          {spec.label}
          <span className="text-[10px] uppercase bg-slate-500/10 text-slate-500 px-1.5 py-0.5 rounded font-normal">{spec.kind}</span>
          {existing?.is_active && <Badge tone="green">faol</Badge>}
        </span>
      }
      badge={testRes && (testRes.ok
        ? <CheckCircle2 size={14} className="text-emerald-500" />
        : testRes.warn
          ? <AlertTriangle size={14} className="text-amber-500" />
          : <XCircle size={14} className="text-rose-500" />)}
    >
      <div className="space-y-3 pt-1">
        <div className="grid grid-cols-2 gap-3">
          {spec.fields.map(f => (
            <FormField key={f.name} label={f.label} required={f.required} hint={f.help}>
              <Input
                type={f.secret ? 'password' : 'text'}
                value={values[f.name] ?? ''}
                placeholder={f.secret && existing?.has_credentials ? '•••••• (saqlangan)' : f.placeholder}
                onChange={e => setValues(v => ({ ...v, [f.name]: e.target.value }))}
              />
            </FormField>
          ))}
        </div>
        <div className="flex gap-2 pt-1">
          <Button size="sm" onClick={save} loading={busy}>Saqlash</Button>
          <Button size="sm" variant="secondary" onClick={runTest} disabled={busy}>Ulanishni tekshirish</Button>
          {(spec.type === 'smartup' || spec.type === 'aslbelgisi') && existing?.is_active && (
            <Button size="sm" variant="secondary" onClick={doSync} disabled={busy} icon={<RefreshCw size={14} />}>
              {spec.type === 'aslbelgisi' ? 'Mahsulotlarni sync' : 'SKU sync'}
            </Button>
          )}
        </div>
        {testRes && !testRes.ok && testRes.detail && (
          <p className={`text-xs ${testRes.warn ? 'text-amber-500' : 'text-rose-500'}`}>{testRes.detail}</p>
        )}
      </div>
    </Collapsible>
  )
}

export default function Settings() {
  const user = useAuthStore(s => s.user)
  const { locale, setLocale, t } = useI18n()
  const [specs, setSpecs] = useState<Spec[]>([])
  const [existing, setExisting] = useState<Record<string, Existing>>({})
  const [activeTab, setActiveTab] = useState('general')

  const reload = async () => {
    const list: Existing[] = await getConnectors()
    setExisting(Object.fromEntries(list.map(c => [c.connector_type, c])))
  }
  useEffect(() => {
    getConnectorSpecs().then(setSpecs).catch(() => {})
    reload().catch(() => {})
  }, [])

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
      <PageHeader
        icon={<SettingsIcon size={20} />}
        title="Sozlamalar"
        subtitle="Profil, integratsiyalar, foydalanuvchilar va ogohlantirishlar"
        actions={<Tabs items={SETTINGS_TABS} active={activeTab} onChange={setActiveTab} />}
      />

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={activeTab}
          variants={tabFade}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          {activeTab === 'general' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
              {/* Profil */}
              <Card>
                <CardHeader icon={<User size={16} />} title="Profil" />
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span className="text-slate-400">Email</span>
                    <span className="font-medium text-slate-700">{user?.email}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span className="text-slate-400">Ism</span>
                    <span className="font-medium text-slate-700">{user?.full_name}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span className="text-slate-400">Rol</span>
                    <span className="font-medium text-slate-700">
                      {user?.is_superadmin ? 'Super Admin' : user?.roles?.join(', ') || '—'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Tenant ID</span>
                    <span className="font-mono text-xs text-slate-500">{user?.tenant_id ?? 'Platform darajasi'}</span>
                  </div>
                </div>
              </Card>

              <div className="space-y-4">
                {/* Til */}
                <Card>
                  <CardHeader title={t('common.language')} />
                  <div className="flex gap-2">
                    {allLocales.map(l => (
                      <button
                        key={l}
                        onClick={() => setLocale(l as Locale)}
                        className={`text-sm px-3 py-1.5 rounded-lg border transition ${
                          locale === l
                            ? 'bg-blue-500 text-white border-blue-500'
                            : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-500/5'
                        }`}
                      >
                        {localeLabels[l]}
                      </button>
                    ))}
                  </div>
                </Card>

                {/* API */}
                <Card>
                  <CardHeader icon={<Shield size={16} />} title="API" />
                  <p className="text-sm text-slate-500">
                    Swagger:{' '}
                    <a href="http://localhost:8000/docs" target="_blank" rel="noopener" className="text-blue-500 hover:underline">localhost:8000/docs</a>
                  </p>
                </Card>
              </div>
            </div>
          )}

          {activeTab === 'integrations' && (
            <div className="space-y-4">
              <IntegrationStatusPanel />

              {/* ── Smartup: ulangan org + sklad↔kod mapping ──────────────── */}
              <SmartupMappingPanel />

              {/* ── ERP-yozuv ruxsati (rol asosida) ───────────────────────── */}
              <ErpPolicyPanel />

              {/* ── Ocard mahsulotlar seed ────────────────────────────────── */}
              <OcardSeedPanel />

              <Card>
                <CardHeader icon={<Plug size={16} />} title="Konnektorlar" />
                {specs.length === 0 && <p className="text-sm text-slate-400">Konnektorlar yuklanmoqda…</p>}
                <div className="space-y-2">
                  {specs.map(spec => (
                    <ConnectorForm key={spec.type} spec={spec} existing={existing[spec.type]} onSaved={reload} />
                  ))}
                </div>
              </Card>
            </div>
          )}

          {activeTab === 'users' && (
            <Suspense fallback={<div className="p-8 text-center text-slate-400">Yuklanmoqda…</div>}>
              <AdminCenter embedded />
            </Suspense>
          )}

          {activeTab === 'alerts' && (
            <Suspense fallback={<div className="p-8 text-center text-slate-400">Yuklanmoqda…</div>}>
              <Alerts embedded />
            </Suspense>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

// ── Integratsiya holati paneli ───────────────────────────────────────────────
function fmtTime(iso?: string | null) {
  if (!iso) return '—'
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

const FLOW_LABEL: Record<string, string> = {
  products: 'Mahsulot', orders: 'Buyurtma', inputs: 'Kirim', reconciliation: 'Svereka',
}

function IntegrationStatusPanel() {
  const qc = useQueryClient()
  const { data } = useQuery({
    queryKey: ['integration-status'], queryFn: getIntegrationStatus, refetchInterval: 20_000,
  })
  const connectors = data?.connectors ?? []
  const failures = data?.recent_failures ?? []
  const pendingApproval = data?.pending_approval ?? []
  const [busy, setBusy] = useState<string | null>(null)
  const [pulling, setPulling] = useState(false)
  if (!data) return null

  const act = async (id: string, kind: 'approve' | 'reject') => {
    setBusy(id)
    try {
      if (kind === 'approve') { await approvePush(id); toast.success('Tasdiqlandi — yuboriladi') }
      else { await rejectPush(id, 'Operator rad etdi'); toast('Rad etildi') }
      qc.invalidateQueries({ queryKey: ['integration-status'] })
    } catch { toast.error('Xatolik') } finally { setBusy(null) }
  }

  const refresh = async () => {
    setPulling(true)
    try {
      const r = await pullSmartup()
      const res = r?.results ?? {}
      const ok = Object.values(res).filter((x: any) => x?.ok).length
      const fail = Object.values(res).filter((x: any) => x && !x.ok).length
      toast.success(`Yangilandi: ${ok} oqim${fail ? `, ${fail} xato` : ''}`)
      qc.invalidateQueries({ queryKey: ['integration-status'] })
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Yangilashda xatolik')
    } finally { setPulling(false) }
  }

  const smartup = connectors.find((c: any) => c.type === 'smartup')
  const recon = smartup?.reconciliation
  const snaps = smartup?.snapshots ?? {}

  return (
    <Card>
      <CardHeader
        icon={<Activity size={16} />}
        title="Integratsiya holati"
        action={
          <Button size="sm" onClick={refresh} loading={pulling} icon={<RefreshCw size={13} />}>
            {pulling ? 'Yuklanmoqda…' : 'Yangilash'}
          </Button>
        }
      />

      <div className="space-y-3">
        {/* Qo'lda-push tasdiq navbati */}
        {pendingApproval.length > 0 && (
          <div className="border border-amber-500/30 bg-amber-500/5 rounded-lg p-3">
            <h3 className="text-xs font-semibold text-amber-700 mb-2">
              ⏳ Tasdiq kutmoqda — Smartup'ga yuborish ({pendingApproval.length})
            </h3>
            <div className="space-y-1.5 max-h-44 overflow-auto">
              {pendingApproval.map((m: any) => (
                <div key={m.id} className="flex items-center justify-between gap-2 text-xs bg-white rounded p-2 border border-slate-200/70">
                  <div className="min-w-0">
                    <span className="font-medium text-slate-700">{m.event_type}</span>
                    <span className="text-slate-400"> · {fmtTime(m.created_at)}</span>
                  </div>
                  <div className="flex gap-1.5 shrink-0">
                    <Button size="sm" variant="success" disabled={busy === m.id} onClick={() => act(m.id, 'approve')}>Tasdiqlash</Button>
                    <Button size="sm" variant="secondary" disabled={busy === m.id} onClick={() => act(m.id, 'reject')}>Rad etish</Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {connectors.map((c: any) => {
            const pending = c.queue?.pending ?? 0, failed = c.queue?.failed ?? 0, sent = c.queue?.sent ?? 0
            const st = c.sync_times ?? {}
            return (
              <div key={c.type} className="border border-slate-200 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-medium text-slate-700 capitalize text-sm">{c.type}</span>
                  <Badge tone={c.is_active ? 'green' : 'slate'} dot>{c.is_active ? 'faol' : 'o\'chiq'}</Badge>
                </div>
                {c.type === 'smartup' && (
                  <div className="space-y-0.5 text-xs text-slate-500">
                    {(['products', 'orders', 'inputs', 'reconciliation'] as const).map(f => (
                      <div key={f} className="flex justify-between">
                        <span>{FLOW_LABEL[f]} pull:</span>
                        <b>{fmtTime(st[f])}</b>
                      </div>
                    ))}
                    {(snaps.orders?.fetched != null || snaps.inputs?.fetched != null) && (
                      <div className="pt-1 text-slate-400">
                        Kutmoqda: {snaps.orders?.fetched ?? 0} buyurtma · {snaps.inputs?.fetched ?? 0} kirim
                      </div>
                    )}
                  </div>
                )}
                <div className="flex gap-3 mt-2 text-xs">
                  <span className="text-amber-600">Navbatda: <b>{pending}</b></span>
                  <span className="text-rose-600">Xato: <b>{failed}</b></span>
                  <span className="text-emerald-600">Yuborilgan: <b>{sent}</b></span>
                </div>
              </div>
            )
          })}
          {connectors.length === 0 && <p className="text-sm text-slate-400">Konnektor sozlanmagan</p>}
        </div>

        {/* Svereka xulosasi */}
        {recon?.totals && (
          <div className="border border-slate-200 rounded-lg p-3">
            <h3 className="text-xs font-semibold text-slate-600 mb-1.5">
              📊 Qoldiq svereka (oxirgi: {fmtTime(recon.generated_at)})
            </h3>
            <div className="flex flex-wrap gap-3 text-xs">
              <span className="text-emerald-600">Mos: <b>{recon.totals.match}</b></span>
              <span className="text-rose-600">Farqli: <b>{recon.totals.mismatch}</b></span>
              <span className="text-blue-600">Faqat WMS: <b>{recon.totals.only_wms}</b></span>
              <span className="text-purple-600">Faqat ERP: <b>{recon.totals.only_erp}</b></span>
            </div>
          </div>
        )}

        {failures.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold text-rose-600 flex items-center gap-1 mb-2">
              <AlertTriangle size={12} /> Oxirgi xatolar
            </h3>
            <div className="space-y-1.5 max-h-32 overflow-auto">
              {failures.map((f: any, i: number) => (
                <div key={i} className="text-xs bg-rose-500/5 border border-rose-500/20 rounded p-2">
                  <span className="font-medium text-rose-700">{f.connector} · {f.event_type}</span>
                  <span className="text-slate-400"> · {f.attempts}× · {fmtTime(f.at)}</span>
                  <div className="text-slate-500 truncate">{f.error}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}

// ── Buxgalteriya Ocard 64 mahsulot seed paneli ──────────────────────────────
function OcardSeedPanel() {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<{ created: number; updated: number; total: number } | null>(null)

  const run = async () => {
    setBusy(true)
    try {
      const r = await seedOcardProducts()
      setResult(r)
      toast.success(`✓ ${r.created} yangi, ${r.updated} yangilandi (jami ${r.total})`)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Seed xatosi')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card className="border-blue-500/20 bg-blue-500/5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-700 text-sm">
            Buxgalteriya Ocard mahsulotlari
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            64 ta Green White mahsulotini (Blanc Bleu, Salqin kofe, OCARD suv va h.k.) WMS bazasiga bir marta seed qiladi.
            Asl Belgisi ulanishi shart emas — ma'lumotlar to'g'ridan-to'g'ri kiritiladi.
          </p>
        </div>
        <Button size="sm" className="shrink-0" onClick={run} loading={busy} icon={<RefreshCw size={14} />}>
          {busy ? 'Yuklanmoqda…' : 'Seed qilish'}
        </Button>
      </div>
      {result && (
        <div className="text-xs text-slate-600 flex gap-4 mt-2">
          <span className="text-emerald-600 font-medium">+{result.created} yangi</span>
          <span className="text-blue-600 font-medium">↺ {result.updated} yangilandi</span>
          <span className="text-slate-500">jami {result.total}</span>
        </div>
      )}
    </Card>
  )
}

// ── ERP-yozuv ruxsati (rol asosida) ──────────────────────────────────────────
function ErpPolicyPanel() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['erp-policy'], queryFn: getErpPolicy })
  const [sel, setSel] = useState<string[] | null>(null)
  const [busy, setBusy] = useState(false)

  const allRoles: string[] = (data as any)?.all_roles ?? []
  const allowed: string[] = sel ?? (data as any)?.allowed_roles ?? []
  const dirty = sel !== null

  const toggle = (r: string) => {
    const base = sel ?? (data as any)?.allowed_roles ?? []
    setSel(base.includes(r) ? base.filter((x: string) => x !== r) : [...base, r])
  }
  const save = async () => {
    setBusy(true)
    try {
      await setErpPolicy(allowed)
      toast.success('ERP-yozuv ruxsati saqlandi')
      setSel(null)
      qc.invalidateQueries({ queryKey: ['erp-policy'] })
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Saqlashda xatolik')
    } finally { setBusy(false) }
  }

  return (
    <Card className="border-amber-500/30 bg-amber-500/5 space-y-3">
      <h2 className="font-semibold text-slate-700 flex items-center gap-2 text-sm">
        <ShieldCheck size={14} className="text-amber-600" /> ERP-yozuv ruxsati (rol asosida)
      </h2>
      <p className="text-xs text-slate-500">
        Smartup'ga YOZISH (buyurtma statusini o'zgartirish, marka biriktirish...) — bu REAL ERP'ni
        o'zgartiradi. Quyidagi rollargina bajara oladi. Superadmin har doim ruxsatli.
      </p>
      {isLoading ? <p className="text-sm text-slate-400">Yuklanmoqda…</p> : (
        <div className="flex flex-wrap gap-2">
          {allRoles.map(r => (
            <label key={r} className={`flex items-center gap-1.5 text-sm px-2.5 py-1 rounded-lg border cursor-pointer select-none ${
              allowed.includes(r) ? 'border-amber-500/40 bg-amber-500/15 text-amber-800' : 'border-slate-200 text-slate-500'}`}>
              <input type="checkbox" checked={allowed.includes(r)} onChange={() => toggle(r)} className="accent-amber-600" />
              {r}
            </label>
          ))}
        </div>
      )}
      {dirty && (
        <Button size="sm" onClick={save} loading={busy} className="bg-amber-600 hover:bg-amber-700 shadow-amber-600/25">
          {busy ? 'Saqlanmoqda…' : 'Saqlash'}
        </Button>
      )}
    </Card>
  )
}

// ── Smartup: ulangan tashkilot + sklad↔kod mapping ───────────────────────────
function SmartupMappingPanel() {
  const qc = useQueryClient()
  const org = useQuery({ queryKey: ['smartup-current-org'], queryFn: getSmartupCurrentOrg, retry: false })
  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState<string | null>(null)

  const save = async (id: string) => {
    setBusy(id)
    try {
      await updateWarehouse(id, { smartup_warehouse_code: edits[id] ?? '' })
      toast.success('Sklad kodi saqlandi')
      setEdits(e => { const n = { ...e }; delete n[id]; return n })
      qc.invalidateQueries({ queryKey: ['warehouses'] })
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Saqlashda xatolik')
    } finally { setBusy(null) }
  }
  const o = org.data as any

  return (
    <Card className="space-y-3">
      <h2 className="font-semibold text-slate-700 flex items-center gap-2 text-sm">
        <Plug size={14} /> Smartup: ulangan tashkilot va sklad mapping
      </h2>
      {/* Ulangan org */}
      {org.isLoading ? <p className="text-sm text-slate-400">Tekshirilmoqda…</p> : org.isError ? (
        <p className="text-sm text-rose-500">Smartup'ga ulanib bo'lmadi (kredit yoki tarmoq).</p>
      ) : o && (
        <div className="text-xs text-slate-600 bg-slate-500/5 rounded p-2 space-y-0.5">
          <div>filial_id (header): <b>{o.filial_id_header ?? '—'}</b> · filial_code: <b>{o.filial_code}</b></div>
          <div>Namuna buyurtmalar: {o.sample_order_count} · mijozlar: {(o.sample_customers ?? []).join(', ') || '—'}</div>
          <div className="text-slate-400">{o.note}</div>
        </div>
      )}
      {/* Sklad mapping */}
      <div className="space-y-2">
        {(warehouses as any[]).map((w: any) => {
          const cur = edits[w.id] ?? w.smartup_warehouse_code ?? ''
          const dirty = edits[w.id] !== undefined && edits[w.id] !== (w.smartup_warehouse_code ?? '')
          return (
            <div key={w.id} className="flex items-center gap-2 text-sm">
              <span className="flex-1 text-slate-700">{w.name}</span>
              <Input value={cur} onChange={e => setEdits(s => ({ ...s, [w.id]: e.target.value }))}
                placeholder="Smartup kodi yoki *"
                className="w-40 h-9" />
              <Button size="sm" onClick={() => save(w.id)} disabled={!dirty || busy === w.id}>
                {busy === w.id ? '…' : 'Saqlash'}
              </Button>
            </div>
          )
        })}
        <p className="text-[10px] text-slate-400">
          "*" = butun filial qoldig'i (sklad kodi null bo'lganda svereka uchun). Aniq kod bo'lsa — o'sha sklad.
        </p>
      </div>
    </Card>
  )
}
