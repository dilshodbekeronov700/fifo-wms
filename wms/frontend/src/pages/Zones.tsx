/**
 * Zonalar — klassifikatsiya / joylash qoidalari muharriri.
 * Foydalanuvchi zonalarni xohlagancha nomlab, xohlagan mantiqni qo'yadi:
 *  - Muddati o'tgan/yaqin mahsulotlar uchun alohida zona (expiry_max_days)
 *  - Maxsus GTIN(lar) uchun zona (gtin_allowlist)
 *  - СТМ (mehmonxona/tashkilot uchun tayyorlangan suv) zonasi (gtin_allowlist + owner_label)
 *  - Разборка (qo'lda joylash) zonasi (manual_only)
 * Slotting engine bu qoidalarni HARD-constraint + kuchli yo'naltirish bonus sifatida ishlatadi.
 */
import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  LayoutGrid, Plus, Trash2, Save, Clock, Barcode, Building2, Wrench, Ban, Layers, Search,
} from 'lucide-react'
import {
  getWarehouses, getZones, createZone, updateZone, deleteZone, updateZoneRules,
} from '../lib/api'
import { PageHeader, Card, Button, Input, Select, Textarea, FormField, Badge, EmptyState } from '../components/ui'
import type { Tone } from '../components/ui'

// Preset ikon rangi — Tailwind statik klasslar (dinamik shablon purge bo'ladi).
const TONE_TEXT: Record<Tone, string> = {
  slate: 'text-slate-500', blue: 'text-blue-500', green: 'text-emerald-500',
  amber: 'text-amber-500', red: 'text-rose-500', purple: 'text-violet-500',
  teal: 'text-teal-500', orange: 'text-orange-500',
}

const ZONE_TYPES: { value: string; label: string }[] = [
  { value: 'reserve', label: 'Zaxira' },
  { value: 'pick', label: 'Terish' },
  { value: 'open_pallet', label: 'Ochiq pallet' },
  { value: 'staging', label: 'Qabul (staging)' },
  { value: 'dock', label: "Jo'natish (dock)" },
  { value: 'quarantine', label: 'Karantin' },
  { value: 'return', label: 'Qaytarish' },
]
const zoneTypeLabel = (t: string) => ZONE_TYPES.find(z => z.value === t)?.label ?? t

// Klassifikatsiya presetlari — bir bosishda putaway_rules to'ldiradi.
const PRESETS: { id: string; label: string; icon: any; tone: Tone; rules: any; desc: string }[] = [
  { id: 'expired', label: "Muddati o'tgan / yaqin", icon: Clock, tone: 'red',
    rules: { purpose: 'expired', expiry_max_days: 0 }, desc: 'Muddati o‘tgan yoki tugayotgan mahsulotlar' },
  { id: 'gtin', label: 'Maxsus GTIN', icon: Barcode, tone: 'blue',
    rules: { purpose: 'gtin', gtin_allowlist: [] }, desc: 'Faqat tanlangan GTIN(lar)' },
  { id: 'stm', label: 'СТМ (mehmonxona/tashkilot)', icon: Building2, tone: 'purple',
    rules: { purpose: 'stm', gtin_allowlist: [], owner_label: '' }, desc: 'Buyurtma bo‘yicha tayyorlangan mahsulot' },
  { id: 'disassembly', label: 'Разборка (qo‘lda)', icon: Wrench, tone: 'amber',
    rules: { purpose: 'disassembly', manual_only: true }, desc: 'Avto-joylashdan chiqarilgan, qo‘lda' },
  { id: 'blocked', label: 'Bloklangan', icon: Ban, tone: 'slate',
    rules: { purpose: 'blocked', blocked: true }, desc: 'Joylash butunlay to‘xtatilgan' },
]

type RulesForm = {
  purpose?: string
  owner_label: string
  blocked: boolean
  manual_only: boolean
  abc: string[]
  categories: string
  gtin_allowlist: string
  gtin_blocklist: string
  expiry_max_days: string
  min_volume: string
  max_volume: string
}

const emptyForm = (): RulesForm => ({
  purpose: undefined, owner_label: '', blocked: false, manual_only: false, abc: [],
  categories: '', gtin_allowlist: '', gtin_blocklist: '', expiry_max_days: '', min_volume: '', max_volume: '',
})

function rulesToForm(r: any): RulesForm {
  r = r || {}
  const list = (v: any) => Array.isArray(v) ? v.join('\n') : ''
  return {
    purpose: r.purpose,
    owner_label: r.owner_label ?? '',
    blocked: !!r.blocked,
    manual_only: !!r.manual_only,
    abc: Array.isArray(r.abc) ? r.abc : [],
    categories: Array.isArray(r.categories) ? r.categories.join(', ') : '',
    gtin_allowlist: list(r.gtin_allowlist),
    gtin_blocklist: list(r.gtin_blocklist),
    expiry_max_days: r.expiry_max_days != null ? String(r.expiry_max_days) : '',
    min_volume: r.min_volume_m3 != null ? String(r.min_volume_m3) : '',
    max_volume: r.max_volume_m3 != null ? String(r.max_volume_m3) : '',
  }
}

function formToRules(f: RulesForm): any {
  const r: any = {}
  if (f.purpose) r.purpose = f.purpose
  if (f.owner_label.trim()) r.owner_label = f.owner_label.trim()
  if (f.blocked) r.blocked = true
  if (f.manual_only) r.manual_only = true
  if (f.abc.length) r.abc = f.abc
  const cats = f.categories.split(',').map(s => s.trim()).filter(Boolean)
  if (cats.length) r.categories = cats
  const lines = (v: string) => v.split(/[\n,]/).map(s => s.trim()).filter(Boolean)
  const allow = lines(f.gtin_allowlist); if (allow.length) r.gtin_allowlist = allow
  const block = lines(f.gtin_blocklist); if (block.length) r.gtin_blocklist = block
  if (f.expiry_max_days !== '') r.expiry_max_days = Number(f.expiry_max_days)
  if (f.min_volume !== '') r.min_volume_m3 = Number(f.min_volume)
  if (f.max_volume !== '') r.max_volume_m3 = Number(f.max_volume)
  return r
}

// Zona kartasidagi qoida chiplari.
function ruleBadges(r: any): { tone: Tone; label: string }[] {
  r = r || {}
  const out: { tone: Tone; label: string }[] = []
  if (r.blocked) out.push({ tone: 'slate', label: 'Bloklangan' })
  if (r.manual_only) out.push({ tone: 'amber', label: "Qo'lda" })
  if (r.expiry_max_days != null) out.push({ tone: 'red', label: `Muddat ≤ ${r.expiry_max_days} kun` })
  if (Array.isArray(r.gtin_allowlist) && r.gtin_allowlist.length) out.push({ tone: 'blue', label: `${r.gtin_allowlist.length} GTIN` })
  if (Array.isArray(r.gtin_blocklist) && r.gtin_blocklist.length) out.push({ tone: 'slate', label: `${r.gtin_blocklist.length} GTIN blok` })
  if (r.owner_label) out.push({ tone: 'purple', label: r.owner_label })
  if (Array.isArray(r.abc) && r.abc.length) out.push({ tone: 'teal', label: `ABC: ${r.abc.join('')}` })
  if (Array.isArray(r.categories) && r.categories.length) out.push({ tone: 'green', label: `${r.categories.length} kategoriya` })
  return out
}

export default function Zones() {
  const qc = useQueryClient()
  const [whId, setWhId] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [form, setForm] = useState<RulesForm>(emptyForm())
  const [name, setName] = useState('')
  const [zoneType, setZoneType] = useState('reserve')
  const [allowMixed, setAllowMixed] = useState(false)
  const [saving, setSaving] = useState(false)

  const { data: warehouses = [] } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const wid = whId || (warehouses as any[])[0]?.id

  const zonesQ = useQuery({ queryKey: ['zones', wid], queryFn: () => getZones(wid), enabled: !!wid })
  const zones = (zonesQ.data as any[]) ?? []

  const selected = useMemo(() => zones.find(z => z.id === selectedId), [zones, selectedId])

  // Tanlangan zona o'zgarsa formani sinxronla.
  useEffect(() => {
    if (selected) {
      setForm(rulesToForm(selected.putaway_rules))
      setName(selected.name)
      setZoneType(selected.zone_type)
      setAllowMixed(!!selected.allow_mixed)
    }
  }, [selectedId, selected])

  const filtered = zones.filter(z => !search || z.name.toLowerCase().includes(search.toLowerCase()))

  const applyPreset = (p: typeof PRESETS[number]) => {
    setForm({ ...rulesToForm(p.rules), purpose: p.rules.purpose })
    toast.success(`"${p.label}" shabloni qo'llandi — sozlab, saqlang`)
  }

  const create = async () => {
    if (!wid) return
    try {
      const z = await createZone(wid, { name: 'Yangi zona', zone_type: 'reserve', allow_mixed: false })
      await zonesQ.refetch()
      setSelectedId(z.id)
      toast.success('Zona yaratildi')
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? 'Xatolik') }
  }

  const remove = async () => {
    if (!selected || !wid) return
    if (!window.confirm(`"${selected.name}" zonasini o'chirasizmi?`)) return
    try {
      await deleteZone(wid, selected.id)
      setSelectedId(null)
      await zonesQ.refetch()
      toast.success("Zona o'chirildi")
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? 'Xatolik') }
  }

  const save = async () => {
    if (!selected || !wid) return
    setSaving(true)
    try {
      await updateZone(wid, selected.id, { name: name.trim() || selected.name, zone_type: zoneType, allow_mixed: allowMixed })
      await updateZoneRules(selected.id, { putaway_rules: formToRules(form) })
      await zonesQ.refetch()
      qc.invalidateQueries({ queryKey: ['zones', wid] })
      toast.success('Saqlandi')
    } catch (e: any) { toast.error(e?.response?.data?.detail ?? 'Saqlashda xatolik') }
    finally { setSaving(false) }
  }

  const toggleAbc = (c: string) =>
    setForm(f => ({ ...f, abc: f.abc.includes(c) ? f.abc.filter(x => x !== c) : [...f.abc, c] }))

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
      <PageHeader
        icon={<LayoutGrid size={20} />}
        title="Zonalar — klassifikatsiya"
        subtitle="Zonalarni nomlab, joylash mantiqini belgilang (muddat / GTIN / СТМ / разборка)"
        actions={
          <>
            <Select value={wid ?? ''} onChange={e => { setWhId(e.target.value); setSelectedId(null) }} className="w-auto min-w-40">
              {(warehouses as any[]).map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </Select>
            <Button onClick={create} icon={<Plus size={15} />}>Yangi zona</Button>
          </>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-4 items-start">
        {/* Zonalar ro'yxati */}
        <Card padded={false} className="overflow-hidden">
          <div className="p-3 border-b border-slate-200/70">
            <div className="relative">
              <Search size={15} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Zona qidirish…" className="pl-8" />
            </div>
          </div>
          <div className="max-h-[70vh] overflow-y-auto p-2 space-y-1.5">
            {zonesQ.isLoading ? (
              <p className="text-sm text-slate-400 p-4 text-center">Yuklanmoqda…</p>
            ) : filtered.length === 0 ? (
              <EmptyState icon={LayoutGrid} title="Zona yo'q" description="'Yangi zona' bilan boshlang" />
            ) : filtered.map(z => {
              const on = z.id === selectedId
              const badges = ruleBadges(z.putaway_rules)
              return (
                <button key={z.id} onClick={() => setSelectedId(z.id)}
                  className={`w-full text-left p-3 rounded-xl border transition ${
                    on ? 'border-blue-500/40 bg-blue-500/10' : 'border-transparent hover:bg-slate-500/5'
                  }`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-slate-800 text-sm truncate">{z.name}</span>
                    <Badge tone="slate">{zoneTypeLabel(z.zone_type)}</Badge>
                  </div>
                  {badges.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {badges.map((b, i) => <Badge key={i} tone={b.tone}>{b.label}</Badge>)}
                    </div>
                  )}
                </button>
              )
            })}
          </div>
        </Card>

        {/* Muharrir */}
        {!selected ? (
          <Card className="min-h-[300px] flex items-center justify-center">
            <EmptyState icon={Layers} title="Zona tanlang" description="Chapdan zonani tanlang yoki yangi zona yarating" />
          </Card>
        ) : (
          <div className="space-y-4">
            {/* Asosiy */}
            <Card>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField label="Zona nomi">
                  <Input value={name} onChange={e => setName(e.target.value)} placeholder="masalan: Muddati o'tganlar" />
                </FormField>
                <FormField label="Zona turi">
                  <Select value={zoneType} onChange={e => setZoneType(e.target.value)}>
                    {ZONE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </Select>
                </FormField>
              </div>
              <label className="flex items-center gap-2 mt-4 text-sm text-slate-600 cursor-pointer w-fit">
                <input type="checkbox" checked={allowMixed} onChange={e => setAllowMixed(e.target.checked)} className="rounded" />
                Aralash SKU/partiyaga ruxsat (bitta yacheykada bir nechta mahsulot)
              </label>
            </Card>

            {/* Presetlar */}
            <Card>
              <p className="text-xs font-medium text-slate-500 mb-3">Tez shablon (bir bosishda qoidalarni to'ldiradi)</p>
              <div className="flex flex-wrap gap-2">
                {PRESETS.map(p => (
                  <button key={p.id} onClick={() => applyPreset(p)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-sm transition ${
                      form.purpose === p.rules.purpose
                        ? 'border-blue-500/50 bg-blue-500/10 text-slate-800'
                        : 'border-slate-200 hover:bg-slate-500/5 text-slate-600'
                    }`} title={p.desc}>
                    <p.icon size={15} className={TONE_TEXT[p.tone]} />
                    {p.label}
                  </button>
                ))}
              </div>
            </Card>

            {/* Klassifikatsiya qoidalari */}
            <Card>
              <p className="text-xs font-medium text-slate-500 mb-4">Joylash qoidalari (bo'sh qoldirilsa — cheklovsiz)</p>
              <div className="space-y-4">
                <div className="flex flex-wrap gap-4">
                  <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                    <input type="checkbox" checked={form.blocked} onChange={e => setForm(f => ({ ...f, blocked: e.target.checked }))} className="rounded" />
                    <Ban size={14} className="text-slate-400" /> Bloklangan (joylash yo'q)
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                    <input type="checkbox" checked={form.manual_only} onChange={e => setForm(f => ({ ...f, manual_only: e.target.checked }))} className="rounded" />
                    <Wrench size={14} className="text-amber-500" /> Faqat qo'lda (auto-slotting o'chiq)
                  </label>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <FormField label="Muddat filtri — ≤ N kun (muddati o'tgan/yaqin)" hint="0 = faqat muddati o'tgan; bo'sh = filtrsiz">
                    <Input type="number" value={form.expiry_max_days} onChange={e => setForm(f => ({ ...f, expiry_max_days: e.target.value }))} placeholder="masalan: 30" />
                  </FormField>
                  <FormField label="СТМ egasi — mehmonxona/tashkilot nomi" hint="Faqat yorliq uchun (ko'rinadi)">
                    <Input value={form.owner_label} onChange={e => setForm(f => ({ ...f, owner_label: e.target.value }))} placeholder="masalan: Hilton Tashkent" />
                  </FormField>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <FormField label="Ruxsat etilgan GTIN(lar)" hint="Har birini yangi qatorda yoki vergul bilan">
                    <Textarea value={form.gtin_allowlist} onChange={e => setForm(f => ({ ...f, gtin_allowlist: e.target.value }))} placeholder="04780000000001&#10;04780000000002" className="font-mono text-xs" />
                  </FormField>
                  <FormField label="Taqiqlangan GTIN(lar)" hint="Bu GTIN(lar) bu zonaga tushmaydi">
                    <Textarea value={form.gtin_blocklist} onChange={e => setForm(f => ({ ...f, gtin_blocklist: e.target.value }))} placeholder="—" className="font-mono text-xs" />
                  </FormField>
                </div>

                <FormField label="ABC klassi">
                  <div className="flex gap-2">
                    {['A', 'B', 'C'].map(c => (
                      <button key={c} onClick={() => toggleAbc(c)}
                        className={`w-10 h-9 rounded-lg border text-sm font-medium transition ${
                          form.abc.includes(c) ? 'border-blue-500/50 bg-blue-500/10 text-blue-600' : 'border-slate-200 text-slate-500 hover:bg-slate-500/5'
                        }`}>{c}</button>
                    ))}
                  </div>
                </FormField>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <FormField label="Kategoriyalar" hint="Vergul bilan">
                    <Input value={form.categories} onChange={e => setForm(f => ({ ...f, categories: e.target.value }))} placeholder="19L, 5L" />
                  </FormField>
                  <FormField label="Min hajm (m³)">
                    <Input type="number" value={form.min_volume} onChange={e => setForm(f => ({ ...f, min_volume: e.target.value }))} placeholder="—" />
                  </FormField>
                  <FormField label="Maks hajm (m³)">
                    <Input type="number" value={form.max_volume} onChange={e => setForm(f => ({ ...f, max_volume: e.target.value }))} placeholder="—" />
                  </FormField>
                </div>
              </div>

              <div className="flex items-center justify-between mt-6 pt-4 border-t border-slate-200/70">
                <Button variant="ghost" onClick={remove} icon={<Trash2 size={15} />} className="text-rose-600 hover:bg-rose-500/10">
                  O'chirish
                </Button>
                <Button onClick={save} loading={saving} icon={<Save size={15} />}>Saqlash</Button>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
