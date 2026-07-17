import { Navigate } from 'react-router-dom'
import { useAuthStore, hasRole } from '../store/auth'

interface Props {
  roles?: string[]
  children: React.ReactNode
}

export default function ProtectedRoute({ roles, children }: Props) {
  const user = useAuthStore(s => s.user)
  if (!user) return <Navigate to="/login" replace />
  if (roles && !hasRole(user, ...roles)) return <Navigate to="/" replace />
  return <>{children}</>
}
