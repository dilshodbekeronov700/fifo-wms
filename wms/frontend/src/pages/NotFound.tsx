import { Link } from 'react-router-dom'
import { Compass, ArrowLeft } from 'lucide-react'

/** 404 — noma'lum yo'l. Avval barcha noma'lum yo'llar jimgina "/"ga tashlanardi. */
export default function NotFound() {
  return (
    <div className="min-h-[70vh] flex items-center justify-center p-6">
      <div className="text-center">
        <div className="text-[110px] leading-none font-black bg-gradient-to-br from-blue-500 to-indigo-600 bg-clip-text text-transparent select-none">
          404
        </div>
        <div className="w-12 h-12 mx-auto -mt-2 rounded-2xl bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center mb-3">
          <Compass className="text-blue-500" size={24} />
        </div>
        <h1 className="text-lg font-bold text-slate-800 dark:text-slate-100">Sahifa topilmadi</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Bu manzil mavjud emas yoki ko'chirilgan.
        </p>
        <Link to="/"
          className="inline-flex items-center gap-1.5 mt-5 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition">
          <ArrowLeft size={15} /> Bosh sahifaga
        </Link>
      </div>
    </div>
  )
}
