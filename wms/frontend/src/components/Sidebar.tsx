import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Package, BarChart3,
  Settings, LogOut, Layers,
  ArrowDownToLine, X, Route,
  Map, ArrowLeftRight, Sun, Moon, ClipboardList, Thermometer,
  PanelLeftClose, PanelLeftOpen, Cloud, LayoutGrid,
} from 'lucide-react'
import { useAuthStore, hasRole } from '../store/auth'
import { useTheme } from '../lib/theme'
import { useI18n, allLocales } from '../lib/i18n'
import WarehouseSelector from './WarehouseSelector'
import clsx from 'clsx'

type Item = { to: string; icon: any; key: string; roles: string[] }
type Group = { title: string | null; items: Item[] }

const groups: Group[] = [
  {
    title: null,
    items: [{ to: '/', icon: LayoutDashboard, key: 'nav.dashboard', roles: [] }],
  },
  {
    title: 'group.warehouse',
    items: [
      { to: '/sklad', icon: Map, key: 'nav.sklad', roles: [] },
      { to: '/zones', icon: LayoutGrid, key: 'nav.zones', roles: ['manager', 'admin'] },
      { to: '/products', icon: Package, key: 'nav.products', roles: [] },
    ],
  },
  {
    title: 'group.operations',
    items: [
      { to: '/receipt', icon: ArrowDownToLine, key: 'nav.receipt', roles: ['manager', 'admin', 'storekeeper'] },
      { to: '/shipment', icon: Route, key: 'nav.shipment', roles: ['manager', 'admin', 'storekeeper'] },
      { to: '/operations', icon: ArrowLeftRight, key: 'nav.move', roles: ['manager', 'admin', 'storekeeper'] },
      { to: '/tasks', icon: ClipboardList, key: 'nav.tasks', roles: [] },
    ],
  },
  {
    title: 'group.analysis',
    items: [
      { to: '/analytics', icon: BarChart3, key: 'nav.analytics', roles: ['manager', 'admin'] },
      { to: '/monitoring', icon: Thermometer, key: 'nav.monitoring', roles: [] },
      { to: '/stock', icon: Layers, key: 'nav.stock', roles: [] },
      { to: '/smartup', icon: Cloud, key: 'nav.smartup', roles: [] },
    ],
  },
  {
    title: 'group.system',
    items: [
      { to: '/settings', icon: Settings, key: 'nav.settings', roles: ['admin'] },
    ],
  },
]

interface Props {
  open: boolean
  onClose: () => void
}

export default function Sidebar({ open, onClose }: Props) {
  const { user, logout } = useAuthStore()
  const { theme, toggle } = useTheme()
  const { t, locale, setLocale } = useI18n()
  const navigate = useNavigate()
  const cycleLocale = () => {
    const i = allLocales.indexOf(locale)
    setLocale(allLocales[(i + 1) % allLocales.length])
  }

  // Desktop yig'ish (collapse) holati — localStorage'da saqlanadi.
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem('sidebar-collapsed') === '1'
  )
  const toggleCollapsed = () => {
    setCollapsed(v => {
      const nv = !v
      localStorage.setItem('sidebar-collapsed', nv ? '1' : '0')
      return nv
    })
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const can = (item: Item) => item.roles.length === 0 || hasRole(user, ...item.roles)
  const visibleGroups = groups
    .map(g => ({ ...g, items: g.items.filter(can) }))
    .filter(g => g.items.length > 0)

  return (
    <>
      {open && (
        <div className="fixed inset-0 bg-black/50 z-20 lg:hidden" onClick={onClose} />
      )}

      <aside className={clsx(
        'sidebar-shell bg-slate-900 text-slate-300 flex flex-col h-full shrink-0 z-30',
        'transition-[width,transform] duration-200 ease-in-out',
        'fixed lg:static inset-y-0 left-0',
        // Mobil: har doim to'liq drawer; Desktop: collapse holatiga qarab
        'w-60',
        collapsed ? 'lg:w-[72px]' : 'lg:w-60',
        open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      )}>
        {/* Logo + collapse toggle */}
        <div className={clsx(
          'py-4 flex items-center border-b border-slate-800',
          collapsed ? 'lg:px-0 lg:justify-center px-5 justify-between' : 'px-5 justify-between'
        )}>
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm shrink-0 shadow-lg shadow-blue-500/20">W</div>
            <div className={clsx('leading-tight', collapsed && 'lg:hidden')}>
              <div className="font-semibold text-white text-sm whitespace-nowrap">WMS Platform</div>
              <div className="text-[10px] text-slate-500 whitespace-nowrap">Green White</div>
            </div>
          </div>
          {/* Desktop collapse tugmasi */}
          <button
            onClick={toggleCollapsed}
            title={collapsed ? 'Panelni ochish' : 'Panelni yig\'ish'}
            className={clsx(
              'hidden lg:flex items-center justify-center p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition',
              collapsed && 'lg:hidden'
            )}
          >
            <PanelLeftClose size={16} />
          </button>
          {/* Mobil yopish */}
          <button onClick={onClose} className="lg:hidden text-slate-400 hover:text-white p-1">
            <X size={16} />
          </button>
        </div>

        {/* Collapsed holatda ochish tugmasi (alohida qator) */}
        {collapsed && (
          <button
            onClick={toggleCollapsed}
            title="Panelni ochish"
            className="hidden lg:flex items-center justify-center py-2 border-b border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <PanelLeftOpen size={16} />
          </button>
        )}

        {/* Warehouse selector — yig'ilganda yashiriladi */}
        <div className={clsx('px-3 py-3 border-b border-slate-800', collapsed && 'lg:hidden')}>
          <WarehouseSelector />
        </div>

        {/* Grouped nav */}
        <nav className={clsx('flex-1 py-3 overflow-y-auto overflow-x-hidden',
          collapsed ? 'lg:px-2 px-3 space-y-2' : 'px-3 space-y-4')}>
          {visibleGroups.map((g, gi) => (
            <div key={gi} className="space-y-0.5">
              {g.title && (
                collapsed
                  ? <div className="hidden lg:block mx-2 my-1 border-t border-slate-800" />
                  : <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      {t(g.title)}
                    </div>
              )}
              {/* Collapsed'da guruh sarlavhasi mobil drawer'da ko'rinadi */}
              {g.title && collapsed && (
                <div className="lg:hidden px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  {t(g.title)}
                </div>
              )}
              {g.items.map(({ to, icon: Icon, key }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  onClick={onClose}
                  title={collapsed ? t(key) : undefined}
                  className={({ isActive }) =>
                    clsx(
                      'group flex items-center rounded-lg text-sm transition relative',
                      collapsed ? 'lg:justify-center lg:px-0 gap-3 px-3 py-2.5' : 'gap-3 px-3 py-2',
                      isActive
                        ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                        : 'hover:bg-slate-800 text-slate-400 hover:text-white'
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      {isActive && !collapsed && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-blue-300 rounded-r" />}
                      <Icon size={16} className="shrink-0" />
                      <span className={clsx('whitespace-nowrap', collapsed && 'lg:hidden')}>{t(key)}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {/* User */}
        <div className={clsx('py-4 border-t border-slate-800',
          collapsed ? 'lg:px-2 px-4' : 'px-4')}>
          <div className={clsx(collapsed && 'lg:hidden')}>
            <div className="text-xs text-slate-500 mb-0.5 truncate">{user?.email}</div>
            <div className="text-xs text-slate-400 mb-3">
              {user?.is_superadmin ? 'Super Admin' : (user?.roles[0] ?? t('common.user'))}
            </div>
          </div>
          <div className={clsx('flex items-center',
            collapsed ? 'lg:flex-col lg:gap-2 justify-between' : 'justify-between')}>
            <button
              onClick={handleLogout}
              title={t('common.logout')}
              className={clsx(
                'flex items-center gap-2 text-slate-400 hover:text-red-400 text-sm transition',
                collapsed && 'lg:justify-center'
              )}
            >
              <LogOut size={14} />
              <span className={clsx(collapsed && 'lg:hidden')}>{t('common.logout')}</span>
            </button>
            <div className="flex items-center gap-1">
              <button
                onClick={cycleLocale}
                title={t('common.language')}
                className="px-2 py-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition text-xs font-semibold uppercase"
              >
                {locale}
              </button>
              <button
                onClick={toggle}
                title={theme === 'dark' ? t('theme.light') : t('theme.dark')}
                className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}
