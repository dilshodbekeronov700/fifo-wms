/**
 * ─────────────────────────────────────────────────────────────────
 *  Sklad GP — haqiqiy layout (PDF: 02_Планировка 14)
 * ─────────────────────────────────────────────────────────────────
 *  Bino ~54m × 16m (9 span × 6000mm).
 *  Rack joylashuvi PDF reja asosida (bir xil grid EMAS):
 *    1-qator  : yuqori uzun row (single-deep)
 *    2-3 qator: juft (double-deep), chap segment + o'ng segment (markaziy yo'lak)
 *    4-5 qator: xuddi shunday juft
 *    6-qator  : pastki split row
 *  Har katak ichida 2 pallet, 3 etaj = 6 joy.
 *
 *  2D (SVG) va 3D (three) ikkalasi shu konfiguratsiyadan render qiladi.
 *  Katak sonlarini moslash kerak bo'lsa — shu yerda o'zgartiring.
 * ─────────────────────────────────────────────────────────────────
 */

export const BUILDING = { w: 54, h: 16 }   // metr

export const CELL_W = 1.95   // katak kengligi (uzunlik bo'ylab), m
export const ROW_D  = 1.15   // bir qator chuqurligi, m
export const TIERS  = 3
export const POSITIONS = 2   // katakdagi pallet soni

export type RackSegment = {
  id: string
  row: string        // qator yorlig'i (Q-1..Q-6) — juft segmentlar bir xil row
  block: string      // blok nomi (A/B/C/D)
  x: number          // chap chekka (m)
  y: number          // yuqori chekka / chuqurlik boshlanishi (m)
  cols: number       // uzunlik bo'yicha katak soni
  deep: 1 | 2        // single yoki orqama-orqa juft row
  product: string    // saqlanadigan mahsulot
}

// PDF rejaga mos rack segmentlari (taxminiy katak sonlari — moslash mumkin)
export const RACK_SEGMENTS: RackSegment[] = [
  // 1-qator: yuqori uzun row (19L), butun bo'ylab
  { id: 'A',  row: 'Q-1', block: 'A', x: 0.5, y: 0.4,  cols: 16, deep: 1, product: '19L' },

  // 2-3 qator: juft (double-deep), chap + o'ng
  { id: 'B-L', row: 'Q-2', block: 'B', x: 0.5,  y: 3.7, cols: 9, deep: 2, product: '0.5L' },
  { id: 'B-R', row: 'Q-2', block: 'B', x: 21.0, y: 3.7, cols: 6, deep: 2, product: '0.5L' },

  // 4-5 qator: juft (double-deep), chap + o'ng
  { id: 'C-L', row: 'Q-4', block: 'C', x: 0.5,  y: 8.4, cols: 9, deep: 2, product: '0.5L' },
  { id: 'C-R', row: 'Q-4', block: 'C', x: 21.0, y: 8.4, cols: 6, deep: 2, product: '0.5L' },

  // 6-qator: pastki split row (19L)
  { id: 'D-L', row: 'Q-6', block: 'D', x: 3.0,  y: 13.4, cols: 7, deep: 1, product: '19L' },
  { id: 'D-R', row: 'Q-6', block: 'D', x: 22.0, y: 13.4, cols: 7, deep: 1, product: '19L' },
]

// Kontekst zonalari (rack emas — vizual mos kelishi uchun)
export const CONTEXT_ZONES = [
  { id: 'dock',   label: 'Yükleme / Dok', x: 47, y: 0.4, w: 6.5, h: 15.2, kind: 'dock' as const },
  { id: 'office', label: 'Ofis',          x: 47, y: 0.4, w: 6.5, h: 3.0,  kind: 'office' as const },
]

export type CellRef = {
  segId: string
  row: string
  block: string
  product: string
  rIdx: number   // segment ichidagi qator (0..deep-1)
  col: number    // 0..cols-1
  x: number      // katak chap chekka (m)
  y: number      // katak yuqori chekka (m)
  cellId: string // o'qiladigan ID
}

/** Barcha kataklarni (segment × deep × cols) ro'yxatlash */
export function enumerateCells(): CellRef[] {
  const out: CellRef[] = []
  for (const seg of RACK_SEGMENTS) {
    for (let r = 0; r < seg.deep; r++) {
      for (let c = 0; c < seg.cols; c++) {
        out.push({
          segId: seg.id,
          row: seg.row,
          block: seg.block,
          product: seg.product,
          rIdx: r,
          col: c,
          x: seg.x + c * CELL_W,
          y: seg.y + r * ROW_D,
          cellId: `${seg.id}-${String(c + 1).padStart(2, '0')}${seg.deep === 2 ? `-${r + 1}` : ''}`,
        })
      }
    }
  }
  return out
}

/** Umumiy katak va joy soni */
export function totals() {
  const cells = RACK_SEGMENTS.reduce((s, seg) => s + seg.deep * seg.cols, 0)
  return { cells, spots: cells * TIERS * POSITIONS }
}

/** Deterministik demo holati (real location yo'q bo'lganda) */
export function demoStatus(segId: string, r: number, c: number, t: number, p: number): string {
  let h = 2166136261
  const str = `${segId}:${r}:${c}:${t}:${p}`
  for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619) }
  const v = (h >>> 0) % 1000 / 1000
  if (v > 0.62) return 'empty'
  if (v > 0.57) return 'partial'
  if (v > 0.55) return 'blocked'
  return 'occupied'
}

export const STATUS_FILL: Record<string, string> = {
  occupied: '#16a34a',
  partial : '#d97706',
  blocked : '#dc2626',
  empty   : '#e2e8f0',
}
export const STATUS_BORDER: Record<string, string> = {
  occupied: '#15803d',
  partial : '#b45309',
  blocked : '#b91c1c',
  empty   : '#cbd5e1',
}
export const STATUS_LABEL: Record<string, string> = {
  occupied: 'Band', partial: 'Qisman', blocked: 'Bloklangan', empty: "Bo'sh",
}
