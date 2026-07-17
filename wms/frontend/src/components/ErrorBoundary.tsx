import { Component, type ReactNode } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'

type Props = { children: ReactNode }
type State = { error: Error | null }

/**
 * Global xato chegarasi — biror sahifa render paytida crash bo'lsa, butun ilova
 * oq ekranga aylanmaydi. Foydalanuvchiga tushunarli xabar + qayta urinish tugmasi
 * ko'rsatiladi. (Avval hech qanday fallback yo'q edi — crash = oq ekran.)
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: unknown) {
    // Kelajakda bu yerda Sentry.captureException(error) chaqiriladi.
    console.error('UI crash:', error, info)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="min-h-[60vh] flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-card p-8">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-red-50 dark:bg-red-500/10 flex items-center justify-center mb-4">
            <AlertTriangle className="text-red-500" size={26} />
          </div>
          <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">Nimadir noto'g'ri ketdi</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1.5">
            Sahifani ko'rsatishda kutilmagan xatolik yuz berdi. Qayta urinib ko'ring.
          </p>
          <pre className="mt-3 text-[11px] text-left text-slate-400 bg-slate-50 dark:bg-slate-900/50 rounded-lg p-2.5 overflow-x-auto max-h-24">
            {this.state.error.message}
          </pre>
          <div className="flex gap-2 justify-center mt-5">
            <button
              onClick={() => this.setState({ error: null })}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition">
              <RotateCcw size={15} /> Qayta urinish
            </button>
            <button
              onClick={() => { window.location.href = '/' }}
              className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-600 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition">
              Bosh sahifa
            </button>
          </div>
        </div>
      </div>
    )
  }
}
