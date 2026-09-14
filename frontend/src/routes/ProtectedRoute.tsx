import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { EmptyState } from '@/components/ui'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { ROUTES } from '@/routes/paths'
import { hasRole } from '@/store/auth.store'
import type { Role } from '@/types'
import { ShieldAlert } from 'lucide-react'

interface ProtectedRouteProps {
  roles?: Role[]
}

export function ProtectedRoute({ roles }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.login} state={{ from: location.pathname }} replace />
  }

  if (!hasRole(user, roles)) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="Acceso restringido"
        description="Su perfil no cuenta con permisos para acceder a este módulo."
      />
    )
  }

  return <Outlet />
}

export function PublicOnlyRoute() {
  const { isAuthenticated } = useAuth()
  if (isAuthenticated) return <Navigate to={ROUTES.dashboard} replace />
  return <Outlet />
}
