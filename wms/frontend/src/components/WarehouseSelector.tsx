import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getWarehouses } from '../lib/api'
import { useAuthStore } from '../store/auth'
import { Warehouse } from 'lucide-react'

export default function WarehouseSelector() {
  const { selectedWarehouseId, setWarehouse } = useAuthStore()
  const { data } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses })
  const warehouses: any[] = (data as any[]) ?? []

  useEffect(() => {
    if (!selectedWarehouseId && warehouses.length > 0) setWarehouse(warehouses[0].id)
  }, [warehouses, selectedWarehouseId, setWarehouse])

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-lg">
      <Warehouse size={14} className="text-slate-400 shrink-0" />
      <select
        value={selectedWarehouseId ?? ''}
        onChange={e => setWarehouse(e.target.value || null)}
        className="bg-transparent text-slate-200 text-xs outline-none cursor-pointer min-w-0 max-w-[140px] truncate"
      >
        {warehouses.length === 0 && <option value="">Sklad yo'q</option>}
        {warehouses.map((wh: any) => (
          <option key={wh.id} value={wh.id} className="bg-slate-800 text-slate-200">
            {wh.name}
          </option>
        ))}
      </select>
    </div>
  )
}
