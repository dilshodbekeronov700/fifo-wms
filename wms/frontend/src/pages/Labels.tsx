import { useState } from 'react'
import { Tag, Copy, Printer, MapPin, Box } from 'lucide-react'
import toast from 'react-hot-toast'
import { getLocationLabel, getPalletLabel } from '../lib/api'

type Mode = 'location' | 'pallet'

export default function Labels({ embedded }: { embedded?: boolean }) {
  const [mode, setMode] = useState<Mode>('location')
  const [value, setValue] = useState<string>('')
  const [zpl, setZpl] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)

  const fetchLabel = async () => {
    const v = value.trim()
    if (!v) {
      toast.error(mode === 'location' ? 'Yacheyka ID kiriting' : 'Pallet kodini kiriting')
      return
    }
    setLoading(true)
    try {
      const res = mode === 'location' ? await getLocationLabel(v) : await getPalletLabel(v)
      // Backend may return raw ZPL string or { zpl: "..." }
      const text = typeof res === 'string' ? res : res?.zpl ?? res?.data ?? ''
      if (!text) {
        toast.error('ZPL topilmadi')
        setZpl('')
      } else {
        setZpl(text)
        toast.success('Yorliq tayyor')
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Yorliq olishda xatolik')
      setZpl('')
    } finally {
      setLoading(false)
    }
  }

  const copyZpl = async () => {
    if (!zpl) return
    try {
      await navigator.clipboard.writeText(zpl)
      toast.success('Nusxa olindi')
    } catch {
      toast.error('Nusxa olishda xatolik')
    }
  }

  const printZpl = () => {
    if (!zpl) return
    const w = window.open('', '_blank', 'width=600,height=700')
    if (!w) {
      toast.error('Pop-up bloklangan — ruxsat bering')
      return
    }
    // Raw ZPL cannot be rendered visually by a browser. We send the ZPL text to
    // the print dialog; on a Zebra/ZPL-enabled printer it prints the label,
    // otherwise it shows the raw code with a note.
    w.document.write(`
      <html>
        <head>
          <title>ZPL yorlig'i</title>
          <style>
            body { font-family: monospace; padding: 16px; color: #1e293b; }
            .note { font-family: sans-serif; background: #fef9c3; border: 1px solid #fde047;
                    padding: 10px 12px; border-radius: 8px; font-size: 13px; margin-bottom: 14px; }
            pre { white-space: pre-wrap; word-break: break-all; font-size: 12px; }
          </style>
        </head>
        <body>
          <div class="note">
            Bu xom ZPL kodi. To'g'ridan-to'g'ri chop etish uchun Zebra (ZPL) printer yoki
            ZPL viewer kerak. Brauzer faqat matnni ko'rsatadi.
          </div>
          <pre>${zpl.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
          <script>window.onload = function(){ window.print(); }<\/script>
        </body>
      </html>
    `)
    w.document.close()
  }

  return (
    <div className={embedded ? 'p-4 space-y-5' : 'p-6 space-y-5'}>
      <div>
        <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <Tag size={20} className="text-blue-500" />
          Yorliqlar
        </h1>
        <p className="text-slate-400 text-sm mt-0.5">Yacheyka yoki pallet uchun ZPL yorlig'i</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-5 space-y-4">
        {/* Mode toggle */}
        <div className="inline-flex rounded-lg border border-slate-200 overflow-hidden text-sm">
          <button
            className={`px-4 py-2 flex items-center gap-1.5 ${
              mode === 'location' ? 'bg-blue-500 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'
            }`}
            onClick={() => { setMode('location'); setZpl('') }}
          >
            <MapPin size={15} /> Yacheyka
          </button>
          <button
            className={`px-4 py-2 flex items-center gap-1.5 border-l border-slate-200 ${
              mode === 'pallet' ? 'bg-blue-500 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'
            }`}
            onClick={() => { setMode('pallet'); setZpl('') }}
          >
            <Box size={15} /> Pallet
          </button>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1 flex-1 min-w-[240px]">
            <label className="text-xs text-slate-400">
              {mode === 'location' ? 'Yacheyka ID' : 'Pallet marking kodi'}
            </label>
            <input
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 bg-white"
              placeholder={mode === 'location' ? 'location id' : 'pallet marking code'}
              value={value}
              onChange={e => setValue(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') fetchLabel() }}
            />
          </div>
          <button
            className="px-4 py-2 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 disabled:opacity-50"
            onClick={fetchLabel}
            disabled={loading}
          >
            {loading ? 'Yuklanmoqda...' : 'Yorliq olish'}
          </button>
        </div>
      </div>

      {/* ZPL output */}
      {zpl && (
        <div className="bg-white rounded-xl shadow-sm p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">ZPL kodi</h2>
            <div className="flex gap-2">
              <button
                className="px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 text-sm flex items-center gap-1.5 hover:bg-slate-50"
                onClick={copyZpl}
              >
                <Copy size={14} /> Nusxa
              </button>
              <button
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-white text-sm flex items-center gap-1.5 hover:bg-slate-900"
                onClick={printZpl}
              >
                <Printer size={14} /> Chop etish
              </button>
            </div>
          </div>
          <pre className="bg-slate-50 border border-slate-100 rounded-lg p-4 text-xs text-slate-700 overflow-auto whitespace-pre-wrap break-all max-h-[420px]">
{zpl}
          </pre>
          <p className="text-xs text-slate-400">
            Eslatma: bu xom ZPL kodi. To'g'ridan-to'g'ri chop etish uchun Zebra (ZPL) printer yoki ZPL viewer kerak.
          </p>
        </div>
      )}
    </div>
  )
}
