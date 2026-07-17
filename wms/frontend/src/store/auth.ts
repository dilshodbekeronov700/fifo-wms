import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  full_name: string
  tenant_id: string | null
  is_superadmin: boolean
  roles: string[]
}

interface AuthState {
  user: User | null
  selectedWarehouseId: string | null
  setUser: (u: User | null) => void
  setWarehouse: (id: string | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    set => ({
      user: null,
      selectedWarehouseId: null,
      setUser: user => set({ user }),
      setWarehouse: id => set({ selectedWarehouseId: id }),
      logout: () => {
        localStorage.clear()
        set({ user: null, selectedWarehouseId: null })
      },
    }),
    { name: 'wms-auth', partialize: s => ({ selectedWarehouseId: s.selectedWarehouseId }) }
  )
)

export const hasRole = (user: User | null, ...roles: string[]) => {
  if (!user) return false
  if (user.is_superadmin) return true
  return roles.some(r => user.roles.includes(r))
}
