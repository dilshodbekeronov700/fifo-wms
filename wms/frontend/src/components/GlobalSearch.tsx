/**
 * Global qidiruv paleti — ⌘K / Ctrl+K bilan ochiladi.
 * Bo'limlar + mahsulotlar bo'yicha qidirib, tanlanganda o'sha sahifaga o'tadi.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, X, CornerDownLeft } from 'lucide-react'
import { getAllProducts } from '../lib/api'

const PAGES: { label: string; to: string; kw: string }[] = [
  { label: 'Boshqaruv paneli', to: '/', kw: 'dashboard bosh' },
  { label: 'Sklad', to: '/sklad', kw: 'sklad xarita' },
  { label: 'Mahsulotlar', to: '/products', kw: 'mahsulot sku tovar' },
  { label: 'Kirim', to: '/receipt', kw: 'kirim qabul priyom' },
  { label: 'Pick marshruti', to: '/shipment', kw: 'pick marshrut chiqim jonatma otgruzka buyurtma terish' },
  { label: "Ko'chirish", to: '/operations', kw: 'kochirish operatsiya' },
  { label: 'Vazifalar', to: '/tasks', kw: 'vazifa task' },
  { label: 'Analitika', to: '/analytics', kw: 'analitika hisobot' },
  { label: 'Harorat-namlik', to: '/monitoring', kw: 'harorat namlik sensor monitoring' },
  { label: 'Qoldiqlar', to: '/stock', kw: 'qoldiq svereka ostatok' },
  { label: 'Smartup (ERP)', to: '/smartup', kw: 'smartup erp buyurtma xarid' },
  { label: 'Sozlamalar', to: '/settings', kw: 'sozlama settings integratsiya' },
]

export default function GlobalSearch() {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [active, setActive] = useState(0)
  const nav = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)

  // ⌘K / Ctrl+K — ochish; ESC — yopish
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen(o => !o)
      } else if (e.key === 'Escape') {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    if (open) { setQ(''); setActive(0); setTimeout(() => inputRef.current?.focus(), 30) }
  }, [open])

  const { data: products = [] } = useQuery({
    queryKey: ['products', 'gs'], queryFn: () => getAllProducts(false), enabled: open,
  })

  const results = useMemo(() => {
    const s = q.trim().toLowerCase()
    const pages = PAGES.filter(p => !s || p.label.toLowerCase().includes(s) || p.kw.includes(s))
      .map(p => ({ type: 'Bo\'lim', label: p.label, to: p.to }))
    const prods = !s ? [] : (products as any[])
      .filter((p: any) =>
        (p.name?.ru ?? p.name?.uz ?? '').toLowerCase().includes(s) ||
        (p.gtin ?? '').toLowerCase().includes(s) ||
        (p.smartup_product_code ?? '').toLowerCase().includes(s))
      .slice(0, 8)
      .map((p: any) => ({ type: 'Mahsulot', label: p.name?.ru ?? p.name?.uz ?? p.gtin, to: '/products' }))
    return [...pages, ...prods]
  }, [q, products])

  useEffect(() => { if (active >= results.length) setActive(0) }, [results.length, active])

  if (!open) return null

  const go = (to: string) => { setOpen(false); nav(to) }

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[12vh] bg-black/30 backdrop-blur-sm"
      onClick={() => setOpen(false)}>
      <div className="w-full max-w-lg bg-white dark:bg-slate-900 rounded-xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-2 px-3 border-b border-slate-100 dark:border-slate-800">
          <Search size={16} className="text-slate-400" />
          <input
            ref={inputRef}
            value={q}
            onChange={e => setQ(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setActive(a => Math.min(a + 1, results.length - 1)) }
              else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(a => Math.max(a - 1, 0)) }
              else if (e.key === 'Enter' && results[active]) go(results[active].to)
            }}
            placeholder="Bo'lim yoki mahsulot qidirish…"
            className="flex-1 py-3 text-sm bg-transparent focus:outline-none text-slate-700 dark:text-slate-100"
          />
          <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-slate-600"><X size={16} /></button>
        </div>
        <div className="max-h-80 overflow-y-auto py-1">
          {results.length === 0 && <div className="px-4 py-6 text-center text-sm text-slate-400">Hech narsa topilmadi</div>}
          {results.map((r, i) => (
            <button key={i} onClick={() => go(r.to)} onMouseEnter={() => setActive(i)}
              className={`w-full flex items-center justify-between px-4 py-2 text-sm text-left ${i === active ? 'bg-blue-50 dark:bg-slate-800' : ''}`}>
              <span className="text-slate-700 dark:text-slate-200">{r.label}</span>
              <span className="text-[10px] uppercase text-slate-400">{r.type}</span>
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3 px-4 py-2 border-t border-slate-100 dark:border-slate-800 text-[10px] text-slate-400">
          <span className="flex items-center gap-1"><CornerDownLeft size={11} /> tanlash</span>
          <span>↑↓ harakat</span>
          <span>ESC yopish</span>
          <span className="ml-auto">⌘K</span>
        </div>
      </div>
    </div>
  )
}
