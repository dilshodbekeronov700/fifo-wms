import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { getMe } from './lib/api'
import { LanguageProvider } from './lib/i18n'
import { useAuthStore } from './store/auth'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'

import Products from './pages/Products'
import StockCenter from './pages/StockCenter'
import Smartup from './pages/Smartup'
import Insights from './pages/Insights'
import Alerts from './pages/Alerts'
import Settings from './pages/Settings'
import Receipt from './pages/Receipt'
import TsdReceive from './pages/TsdReceive'
import Shipment from './pages/Shipment'
import Operations from './pages/Operations'
import Tasks from './pages/Tasks'
import SkladHub from './pages/SkladHub'
import Zones from './pages/Zones'
import Monitoring from './pages/Monitoring'
import Signup from './pages/Signup'
import AdminCenter from './pages/AdminCenter'
import NotFound from './pages/NotFound'
import ErrorBoundary from './components/ErrorBoundary'

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

function AuthLoader({ children }: { children: React.ReactNode }) {
  const setUser = useAuthStore(s => s.setUser)
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      getMe().then(setUser).catch(() => { localStorage.clear(); setUser(null) })
    }
  }, [])
  return <>{children}</>
}

export default function App() {
  return (
    <LanguageProvider>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AuthLoader>
          <ErrorBoundary>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/warehouses" element={<Navigate to="/sklad" replace />} />
              <Route path="/stock" element={<StockCenter />} />
              <Route path="/smartup" element={<Smartup />} />
              {/* "Qoldiq batafsil" endi Qoldiqlar ichidagi tab */}
              <Route path="/stock-view" element={<Navigate to="/stock" replace />} />
              <Route path="/products" element={<Products />} />
              <Route path="/tasks" element={<Tasks />} />
              <Route
                path="/receipt"
                element={
                  <ProtectedRoute roles={['manager', 'admin', 'storekeeper']}>
                    <Receipt />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/tsd-receive"
                element={
                  <ProtectedRoute roles={['manager', 'admin', 'storekeeper']}>
                    <TsdReceive />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/shipment"
                element={
                  <ProtectedRoute roles={['manager', 'admin', 'storekeeper']}>
                    <Shipment />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/operations"
                element={
                  <ProtectedRoute roles={['manager', 'admin', 'storekeeper']}>
                    <Operations />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/analytics"
                element={
                  <ProtectedRoute roles={['manager', 'admin']}>
                    <Insights />
                  </ProtectedRoute>
                }
              />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/sklad" element={<SkladHub />} />
              <Route path="/zones" element={<Zones />} />
              <Route path="/monitoring" element={<Monitoring />} />
              {/* "Hisobotlar" endi Analitika ichidagi tab */}
              <Route path="/reports" element={<Navigate to="/analytics" replace />} />
              {/* Eski yo'llar — birlashtirilgan hub'ga yo'naltiriladi */}
              <Route path="/twin3d" element={<Navigate to="/sklad" replace />} />
              <Route path="/map" element={<Navigate to="/sklad" replace />} />
              <Route path="/labels" element={<Navigate to="/" replace />} />
              <Route
                path="/admin"
                element={
                  <ProtectedRoute roles={['admin', 'manager']}>
                    <AdminCenter />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/settings"
                element={
                  <ProtectedRoute roles={['admin']}>
                    <Settings />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<NotFound />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
          </ErrorBoundary>
        </AuthLoader>
      </BrowserRouter>
      <Toaster position="top-right" toastOptions={{ duration: 3000 }} />
    </QueryClientProvider>
    </LanguageProvider>
  )
}
