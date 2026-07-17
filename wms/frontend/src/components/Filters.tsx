/**
 * Qayta ishlatiladigan filtr/qidiruv komponentlari (barcha bo'limlar uchun).
 *  - useDebounced: qiymatni kechiktirib qaytaradi (qidiruvda ortiqcha so'rovlarsiz).
 *  - SearchInput: tozalash tugmali qidiruv maydoni.
 *  - FilterSelect: yorliqli dropdown filtr.
 *  - FilterBar: filtrlar konteyneri + faol filtr chiplari + "Tozalash".
 *  - useColumnSort: jadval ustun bo'yicha saralash holati.
 */
import { useEffect, useMemo, useState } from 'react'
import { Search, X, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

/** Umumiy CSV eksport — har qanday jadval uchun. columns: [sarlavha, qiymat-oluvchi]. */
export function downloadCsv<T>(filename: string, rows: T[], columns: [string, (r: T) => any][]) {
  const esc = (v: any) => {
    const s = v == null ? '' : String(v)
    return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const header = columns.map(c => esc(c[0])).join(';')
  const body = rows.map(r => columns.map(c => esc(c[1](r))).join(';')).join('\n')
  const blob = new Blob(['﻿' + header + '\n' + body], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

export function SearchInput({
  value, onChange, placeholder = 'Qidirish…', className = '',
}: { value: string; onChange: (v: string) => void; placeholder?: string; className?: string }) {
  return (
    <div className={`relative ${className}`}>
      <Search size={15} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full border border-slate-200 rounded-lg pl-8 pr-8 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
      />
      {value && (
        <button onClick={() => onChange('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
          <X size={14} />
        </button>
      )}
    </div>
  )
}

export function FilterSelect({
  label, value, onChange, options,
}: {
  label?: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className={`border rounded-lg px-2.5 py-1.5 text-sm bg-white ${value ? 'border-blue-300 text-slate-800' : 'border-slate-200 text-slate-500'}`}
    >
      {label && <option value="">{label}</option>}
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  )
}

export function FilterBar({
  children, onClear, hasActive,
}: { children: React.ReactNode; onClear?: () => void; hasActive?: boolean }) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {children}
      {hasActive && onClear && (
        <button onClick={onClear} className="text-xs text-slate-500 hover:text-rose-600 flex items-center gap-1">
          <X size={13} /> Tozalash
        </button>
      )}
    </div>
  )
}

/** Jadval ustun saralash holati. headerClick(key) → toggle asc/desc/none. */
export function useColumnSort<T>(rows: T[], accessors: Record<string, (r: T) => any>) {
  const [key, setKey] = useState<string>('')
  const [dir, setDir] = useState<1 | -1>(1)
  const sorted = useMemo(() => {
    if (!key || !accessors[key]) return rows
    const acc = accessors[key]
    return [...rows].sort((a, b) => {
      const av = acc(a), bv = acc(b)
      if (av == null) return 1
      if (bv == null) return -1
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir
      return String(av).localeCompare(String(bv), 'uz') * dir
    })
  }, [rows, key, dir, accessors])
  const onSort = (k: string) => {
    if (key === k) setDir(d => (d === 1 ? -1 : 1))
    else { setKey(k); setDir(1) }
  }
  return { sorted, sortKey: key, sortDir: dir, onSort }
}

/** Saralash mumkin bo'lgan jadval sarlavhasi. */
export function SortableTh({
  label, sortKey, activeKey, dir, onSort, align = 'left',
}: {
  label: string; sortKey: string; activeKey: string; dir: 1 | -1
  onSort: (k: string) => void; align?: 'left' | 'right'
}) {
  const active = activeKey === sortKey
  return (
    <th
      onClick={() => onSort(sortKey)}
      className={`px-3 py-2 cursor-pointer select-none hover:text-slate-700 ${align === 'right' ? 'text-right' : 'text-left'}`}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {active ? (dir === 1 ? <ArrowUp size={12} /> : <ArrowDown size={12} />) : <ArrowUpDown size={12} className="opacity-30" />}
      </span>
    </th>
  )
}
