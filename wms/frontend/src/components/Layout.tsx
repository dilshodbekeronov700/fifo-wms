import { useState } from 'react'
import { Outlet, Navigate, useLocation } from 'react-router-dom'
import { Menu } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from './Sidebar'
import GlobalSearch from './GlobalSearch'
import LiveIndicator from './LiveIndicator'
import { useAuthStore } from '../store/auth'
import { fadeInUp } from '../lib/motion'
import { useRealtime } from '../lib/realtime'

export default function Layout() {
  const user = useAuthStore(s => s.user)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const rt = useRealtime()

  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="flex h-screen overflow-hidden bg-slate-100 dark:bg-slate-950">
      <GlobalSearch />
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="relative flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile topbar */}
        <div className="lg:hidden flex items-center gap-3 px-4 py-3 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white p-1"
          >
            <Menu size={20} />
          </button>
          <span className="font-semibold text-slate-800 dark:text-slate-100 text-sm">WMS Platform</span>
          <div className="ml-auto"><LiveIndicator status={rt.status} lastEventAt={rt.lastEventAt} /></div>
        </div>

        {/* Desktop uchun jonli indikator — o'ng yuqori burchak */}
        <div className="hidden lg:block absolute top-3 right-5 z-30">
          <LiveIndicator status={rt.status} lastEventAt={rt.lastEventAt} />
        </div>

        {/* Sahifa o'tish animatsiyasi */}
        <main className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={location.pathname}
              variants={fadeInUp}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
