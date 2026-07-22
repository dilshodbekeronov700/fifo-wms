/**
 * ─────────────────────────────────────────────────────────────────
 *  Sklad GP — haqiqiy layout (2026-07 yangilangan qo'l chizma asosida)
 * ─────────────────────────────────────────────────────────────────
 *  6 harfli qator: A (yuqori), B+C (yuqori juft), D+E (quyi juft),
 *  F (pastki split). Har qatorda kataklar o'ngdan chapga raqamlanadi
 *  (o'ng chekka = 1). Ba'zi qatorlar markaziy yo'lak / o'chirilgan
 *  kataklar (eski "NO") tufayli bo'lakларga ajraladi:
 *
 *    A : 14–17 (chap) | [o'chirilgan tirqish] | 1–13 (o'ng)       = 17 katak
 *    B : 9–17 (chap)  | markaziy yo'lak       | 1–8 (o'ng)         = 17 katak
 *    C : 9–17 (chap)  | markaziy yo'lak       | 1–8 (o'ng)         = 17 katak
 *    D : 9–17 (chap)  | markaziy yo'lak       | 1–8 (o'ng)         = 17 katak
 *    E : 9–17 (chap)  | markaziy yo'lak       | 1–8 (o'ng)         = 17 katak
 *    F : 16 (chap) | 9–15 (o'rta) | 1–8 (o'ng)                     = 16 katak
 *
 *  Har katak ichida 2 pallet × 3 etaj = 6 joy. Jami 101 katak = 606 joy.
 *
 *  Mahsulot (19L / 0.5L) segmentga QAT'IY biriktirilmaydi — zona/mahsulot
 *  taqsimoti inson tomonidan qo'lda boshqariladi.
 *
 *  Kontekst: o'ng-yuqori burchak = ofis; o'ng chekka = 19L tara maydoni +
 *  3 darvozadan truck yuklash (dok); pastki-markaz strelka = mahsulotlar
 *  ishlab chiqarish zonasidan skladga kirish nuqtasi.
 *
 *  2D (SVG) va 3D (three) ikkalasi shu konfiguratsiyadan render qiladi.
 *  Katak sonlarini moslash kerak bo'lsa — shu yerda `nums`ni o'zgartiring.
 * ─────────────────────────────────────────────────────────────────
 */

export const BUILDING = { w: 54, h: 16 }   // metr

export const CELL_W = 1.95   // katak kengligi (uzunlik bo'ylab), m
export const ROW_D  = 1.15   // bir qator chuqurligi, m
export const TIERS  = 3
export const POSITIONS = 2   // katakdagi pallet soni

export type RackSegment = {
  id: string         // unikal segment id, masalan 'A-R'
  row: string        // qator harfi (A..F) — DB row + yorliq
  block: string      // cellId prefiksi (= qator harfi)
  x: number          // chap chekka (m)
  y: number          // yuqori chekka (m)
  cols: number       // uzunlik bo'yicha katak soni (= nums.length)
  deep: 1 | 2        // barcha qatorlar endi single-deep (1)
  nums: number[]     // katak raqamlari, chapdan o'ngga tartibda
  label?: boolean    // qator yorlig'ini shu segmentda ko'rsatish (chap chekka)
}

// Katak kengligi × raqam bo'yicha o'ng-anchor helper qulayligi uchun
// koordinatalar to'g'ridan-to'g'ri hisoblab qo'yilgan (o'ng chekka R≈40m,
// markaziy/tirqish yo'lak ≈3m). Kataklar o'ngdan chapga raqamlanadi.
export const RACK_SEGMENTS: RackSegment[] = [
  // ── A qatori (single, yuqori) ──────────────────────────────────
  { id: 'A-L', row: 'A', block: 'A', x: 3.85,  y: 1.0,  cols: 4,  deep: 1, nums: [17, 16, 15, 14], label: true },
  { id: 'A-R', row: 'A', block: 'A', x: 14.65, y: 1.0,  cols: 13, deep: 1, nums: [13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1] },

  // ── B qatori (yuqori juftning old qatori) ──────────────────────
  { id: 'B-L', row: 'B', block: 'B', x: 3.85, y: 4.5,  cols: 9, deep: 1, nums: [17, 16, 15, 14, 13, 12, 11, 10, 9], label: true },
  { id: 'B-R', row: 'B', block: 'B', x: 24.4, y: 4.5,  cols: 8, deep: 1, nums: [8, 7, 6, 5, 4, 3, 2, 1] },

  // ── C qatori (yuqori juftning orqa qatori) ─────────────────────
  { id: 'C-L', row: 'C', block: 'C', x: 3.85, y: 7.0,  cols: 9, deep: 1, nums: [17, 16, 15, 14, 13, 12, 11, 10, 9], label: true },
  { id: 'C-R', row: 'C', block: 'C', x: 24.4, y: 7.0,  cols: 8, deep: 1, nums: [8, 7, 6, 5, 4, 3, 2, 1] },

  // ── D qatori (quyi juftning old qatori) ────────────────────────
  { id: 'D-L', row: 'D', block: 'D', x: 3.85, y: 10.5, cols: 9, deep: 1, nums: [17, 16, 15, 14, 13, 12, 11, 10, 9], label: true },
  { id: 'D-R', row: 'D', block: 'D', x: 24.4, y: 10.5, cols: 8, deep: 1, nums: [8, 7, 6, 5, 4, 3, 2, 1] },

  // ── E qatori (quyi juftning orqa qatori) ───────────────────────
  { id: 'E-L', row: 'E', block: 'E', x: 3.85, y: 13.0, cols: 9, deep: 1, nums: [17, 16, 15, 14, 13, 12, 11, 10, 9], label: true },
  { id: 'E-R', row: 'E', block: 'E', x: 24.4, y: 13.0, cols: 8, deep: 1, nums: [8, 7, 6, 5, 4, 3, 2, 1] },

  // ── F qatori (pastki split: 16 | 9–15 | 1–8) ───────────────────
  { id: 'F-L', row: 'F', block: 'F', x: 3.85, y: 16.5, cols: 1, deep: 1, nums: [16], label: true },
  { id: 'F-M', row: 'F', block: 'F', x: 7.75, y: 16.5, cols: 7, deep: 1, nums: [15, 14, 13, 12, 11, 10, 9] },
  { id: 'F-R', row: 'F', block: 'F', x: 24.4, y: 16.5, cols: 8, deep: 1, nums: [8, 7, 6, 5, 4, 3, 2, 1] },
]

// Kontekst zonalari (rack emas — vizual mos kelishi uchun)
export const CONTEXT_ZONES = [
  { id: 'dock',   label: '19L tara · Dok (3 darvoza)', x: 41,  y: 0.6,  w: 12.5, h: 14.8, kind: 'dock'  as const },
  { id: 'office', label: 'Ofis',                        x: 46,  y: 0.6,  w: 7,    h: 3.0,  kind: 'office' as const },
  { id: 'entry',  label: 'Ishlab chiqarishdan kirish',  x: 24,  y: 15.0, w: 4,    h: 1.0,  kind: 'entry'  as const },
]

export type CellRef = {
  segId: string
  row: string
  block: string
  rIdx: number   // segment ichidagi qator (endi doim 0)
  col: number    // 0..cols-1
  num: number    // real katak raqami (rack labelidagi)
  x: number      // katak chap chekka (m)
  y: number      // katak yuqori chekka (m)
  cellId: string // o'qiladigan ID = `${block}-NN`
}

/** Barcha kataklarni ro'yxatlash */
export function enumerateCells(): CellRef[] {
  const out: CellRef[] = []
  for (const seg of RACK_SEGMENTS) {
    for (let c = 0; c < seg.cols; c++) {
      const num = seg.nums[c]
      out.push({
        segId: seg.id,
        row: seg.row,
        block: seg.block,
        rIdx: 0,
        col: c,
        num,
        x: seg.x + c * CELL_W,
        y: seg.y,
        cellId: `${seg.block}-${String(num).padStart(2, '0')}`,
      })
    }
  }
  return out
}

/** Umumiy katak va joy soni */
export function totals() {
  const cells = RACK_SEGMENTS.reduce((s, seg) => s + seg.cols, 0)
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
