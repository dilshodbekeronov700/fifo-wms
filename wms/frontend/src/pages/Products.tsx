import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAllProducts, createProduct, updateProduct, deleteProduct } from '../lib/api'
import { Plus, Package, Pencil, Search, X, Trash2, RotateCcw, Download } from 'lucide-react'
import toast from 'react-hot-toast'
import { z } from 'zod'
import { downloadCsv } from '../components/Filters'
import { PageHeader, Card, Button, Input, Select, FormField, Badge, EmptyState } from '../components/ui'
import type { Tone } from '../components/ui'

// Mahsulot formasi validatsiyasi (Zod).
const productFormSchema = z.object({
  name_ru: z.string().trim().min(2, 'Nomi kamida 2 belgi'),
  gtin: z.string().trim().regex(/^\d{8,14}$/u, 'GTIN 8–14 raqam').or(z.literal('')),
  units_per_box: z.string().refine(v => v === '' || (Number(v) > 0 && Number.isInteger(Number(v))), 'Musbat butun son'),
  boxes_per_pallet: z.string().refine(v => v === '' || (Number(v) > 0 && Number.isInteger(Number(v))), 'Musbat butun son'),
})

function exportProductsCsv(rows: any[]) {
  downloadCsv('mahsulotlar.csv', rows, [
    ['Nom', (p) => p.name?.ru ?? p.name?.uz ?? ''],
    ['GTIN', (p) => p.gtin ?? ''],
    ['Smartup kodi', (p) => p.smartup_product_code ?? ''],
    ['UOM', (p) => p.uom ?? ''],
    ['Box ichida', (p) => p.units_per_box ?? ''],
    ['ABC', (p) => p.abc_class ?? ''],
    ['Faol', (p) => (p.is_active ? 'ha' : "yo'q")],
  ])
}

const EMPTY = { name_ru: '', gtin: '', smartup_product_code: '', uom: 'unit', units_per_box: '', boxes_per_pallet: '', abc_class: '', is_active: true }
const UOMS = ['unit', 'box', 'pallet', 'kg', 'l']

export default function Products() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState({ ...EMPTY })
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [search, setSearch] = useState('')
  const [showInactive, setShowInactive] = useState(false)

  const validateAndSave = () => {
    const res = productFormSchema.safeParse(form)
    if (!res.success) {
      const errs: Record<string, string> = {}
      for (const i of res.error.issues) { const k = i.path[0] as string; if (!errs[k]) errs[k] = i.message }
      setFormErrors(errs)
      return
    }
    setFormErrors({})
    save.mutate()
  }

  const { data: products = [], isLoading } = useQuery({
    queryKey: ['products', 'manage', showInactive],
    queryFn: () => getAllProducts(showInactive),
  })

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return products
    return products.filter((p: any) =>
      (p.name?.ru ?? '').toLowerCase().includes(q) ||
      (p.name?.uz ?? '').toLowerCase().includes(q) ||
      (p.gtin ?? '').toLowerCase().includes(q) ||
      (p.smartup_product_code ?? '').toLowerCase().includes(q)
    )
  }, [products, search])

  const resetForm = () => { setForm({ ...EMPTY }); setEditingId(null); setShowForm(false) }
  const openCreate = () => { setForm({ ...EMPTY }); setEditingId(null); setShowForm(true) }
  const openEdit = (p: any) => {
    setForm({
      name_ru: p.name?.ru ?? p.name?.uz ?? '',
      gtin: p.gtin ?? '',
      smartup_product_code: p.smartup_product_code ?? '',
      uom: p.uom ?? 'unit',
      units_per_box: p.units_per_box != null ? String(p.units_per_box) : '',
      boxes_per_pallet: p.boxes_per_pallet != null ? String(p.boxes_per_pallet) : '',
      abc_class: p.abc_class ?? '',
      is_active: p.is_active,
    })
    setEditingId(p.id)
    setShowForm(true)
  }

  const payload = () => ({
    name: { ru: form.name_ru, uz: form.name_ru },
    gtin: form.gtin || undefined,
    smartup_product_code: form.smartup_product_code || undefined,
    uom: form.uom || 'unit',
    units_per_box: form.units_per_box ? Number(form.units_per_box) : undefined,
    boxes_per_pallet: form.boxes_per_pallet ? Number(form.boxes_per_pallet) : undefined,
    abc_class: form.abc_class || undefined,
    ...(editingId ? { is_active: form.is_active } : {}),
  })

  const invalidate = () => qc.invalidateQueries({ queryKey: ['products'] })

  const save = useMutation({
    mutationFn: () => editingId ? updateProduct(editingId, payload()) : createProduct(payload()),
    onSuccess: () => { invalidate(); toast.success(editingId ? 'Mahsulot yangilandi' : 'Mahsulot qo\'shildi'); resetForm() },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Xato yuz berdi'),
  })

  const toggleActive = useMutation({
    mutationFn: (p: any) => updateProduct(p.id, { is_active: !p.is_active }),
    onSuccess: () => { invalidate(); toast.success('Holat o\'zgartirildi') },
    onError: () => toast.error('Xato yuz berdi'),
  })

  const remove = useMutation({
    mutationFn: (id: string) => deleteProduct(id),
    onSuccess: () => { invalidate(); toast.success('Mahsulot nofaol qilindi') },
    onError: () => toast.error('O\'chirishda xato'),
  })

  const abcTone: Record<string, Tone> = { A: 'green', B: 'amber', C: 'slate' }

  return (
    <div className="p-4 lg:p-6 space-y-4 max-w-[1600px] mx-auto">
      <PageHeader
        icon={<Package size={20} />}
        title="Mahsulotlar (SKU)"
        subtitle={`${products.length} ta mahsulot`}
        actions={
          <>
            <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer select-none">
              <input type="checkbox" checked={showInactive} onChange={e => setShowInactive(e.target.checked)} className="accent-blue-600" />
              Nofaollarni ko'rsatish
            </label>
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              <Input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Nom / GTIN / kod…"
                className="pl-8 w-56"
              />
            </div>
            <Button variant="secondary" onClick={() => exportProductsCsv(filtered)} disabled={!filtered.length} icon={<Download size={14} />}>
              CSV
            </Button>
            <Button onClick={openCreate} icon={<Plus size={14} />}>Qo'shish</Button>
          </>
        }
      />

      {showForm && (
        <Card className="border-blue-500/40">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-700">{editingId ? 'Mahsulotni tahrirlash' : 'Yangi mahsulot'}</h2>
              <button onClick={resetForm} className="text-slate-400 hover:text-slate-600"><X size={16} /></button>
            </div>
            {[
              { name: 'name_ru', label: 'Nomi', required: true },
              { name: 'gtin', label: 'GTIN' },
              { name: 'smartup_product_code', label: 'Smartup kodi' },
              { name: 'units_per_box', label: 'Box ichida birlik', type: 'number' },
              { name: 'boxes_per_pallet', label: 'Palletda box', type: 'number' },
            ].map(f => (
              <FormField key={f.name} label={f.label} required={f.required} error={formErrors[f.name]}>
                <Input
                  type={f.type ?? 'text'}
                  aria-invalid={!!formErrors[f.name]}
                  value={(form as any)[f.name]}
                  onChange={e => { setForm(v => ({ ...v, [f.name]: e.target.value })); if (formErrors[f.name]) setFormErrors(p => ({ ...p, [f.name]: '' })) }}
                />
              </FormField>
            ))}
            <FormField label="O'lchov birligi (UOM)">
              <Select value={form.uom} onChange={e => setForm(v => ({ ...v, uom: e.target.value }))}>
                {UOMS.map(u => <option key={u} value={u}>{u}</option>)}
              </Select>
            </FormField>
            <FormField label="ABC sinfi">
              <Select value={form.abc_class} onChange={e => setForm(v => ({ ...v, abc_class: e.target.value }))}>
                <option value="">Tanlang</option>
                {['A', 'B', 'C'].map(c => <option key={c}>{c}</option>)}
              </Select>
            </FormField>
            {editingId && (
              <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
                <input type="checkbox" checked={form.is_active} onChange={e => setForm(v => ({ ...v, is_active: e.target.checked }))} className="accent-blue-600 w-4 h-4" />
                Faol (is_active)
              </label>
            )}
            <div className="col-span-2 flex gap-2 pt-1">
              <Button onClick={validateAndSave} loading={save.isPending}>
                Saqlash
              </Button>
              <Button variant="ghost" onClick={resetForm}>Bekor</Button>
            </div>
          </div>
        </Card>
      )}

      <Card padded={false} className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-slate-400 text-xs uppercase tracking-wide">
                <th className="text-right px-4 py-3 w-12">#</th>
                <th className="text-left px-4 py-3">Mahsulot</th>
                <th className="text-left px-4 py-3">GTIN</th>
                <th className="text-left px-4 py-3">Smartup kodi</th>
                <th className="text-left px-4 py-3">UOM</th>
                <th className="text-left px-4 py-3">Box/Pallet</th>
                <th className="text-left px-4 py-3">ABC</th>
                <th className="text-left px-4 py-3">Holat</th>
                <th className="text-right px-4 py-3 w-24">Amal</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={9} className="text-center py-8 text-slate-400">Yuklanmoqda...</td></tr>
              )}
              {filtered.map((p: any, i: number) => (
                <tr key={p.id} className={`border-b border-slate-50 hover:bg-slate-500/5 transition ${!p.is_active ? 'opacity-50' : ''}`}>
                  <td className="px-4 py-3 text-right text-slate-400 tabular-nums">{i + 1}</td>
                  <td className="px-4 py-3 font-medium text-slate-700">{p.name?.ru ?? p.name?.uz ?? '—'}</td>
                  <td className="px-4 py-3 font-mono text-slate-500 text-xs">{p.gtin ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{p.smartup_product_code ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs uppercase">{p.uom ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-500">
                    {p.units_per_box ?? '?'} / {p.boxes_per_pallet ?? '?'}
                  </td>
                  <td className="px-4 py-3">
                    {p.abc_class
                      ? <Badge tone={abcTone[p.abc_class] ?? 'slate'}>{p.abc_class}</Badge>
                      : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => toggleActive.mutate(p)} title="Holatni almashtirish" className="cursor-pointer">
                      <Badge tone={p.is_active ? 'green' : 'red'} dot>{p.is_active ? 'Faol' : 'Nofaol'}</Badge>
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button onClick={() => openEdit(p)} title="Tahrirlash" className="text-slate-400 hover:text-blue-600 p-1 rounded hover:bg-blue-500/10 transition">
                      <Pencil size={14} />
                    </button>
                    {p.is_active
                      ? <button onClick={() => remove.mutate(p.id)} title="Nofaol qilish (o'chirish)" className="text-slate-400 hover:text-rose-600 p-1 rounded hover:bg-rose-500/10 transition ml-1">
                          <Trash2 size={14} />
                        </button>
                      : <button onClick={() => toggleActive.mutate(p)} title="Qayta faollashtirish" className="text-slate-400 hover:text-emerald-600 p-1 rounded hover:bg-emerald-500/10 transition ml-1">
                          <RotateCcw size={14} />
                        </button>}
                  </td>
                </tr>
              ))}
              {!isLoading && filtered.length === 0 && (
                <tr><td colSpan={9} className="py-10">
                  <EmptyState icon={Package} title={search ? 'Qidiruv bo\'yicha mahsulot topilmadi' : 'Mahsulot yo\'q'} />
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
