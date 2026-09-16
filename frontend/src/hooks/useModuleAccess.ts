import { useQuery } from '@tanstack/react-query'

import { adminApi } from '@/features/admin/api/admin.api'
import { useAuthStore } from '@/store/auth.store'

/**
 * Módulos de la matriz de permisos del servidor (backend app/core/permissions.py).
 * El servidor sigue siendo la fuente de verdad: esto solo evita ofrecer
 * acciones que la API va a rechazar con 403.
 */
export type ModuleCode =
  | 'PATIENTS'
  | 'APPOINTMENTS'
  | 'ENCOUNTERS'
  | 'MEDICAL_RECORDS'
  | 'STUDIES'
  | 'DOCUMENTS'
  | 'REMINDERS'
  | 'PHARMACY'
  | 'PURCHASES'
  | 'SALES'
  | 'BILLING'
  | 'REPORTS'
  | 'CATALOG'
  | 'USERS'
  | 'SETTINGS'
  | 'AUDIT'

/** Permisos del usuario en sesión, para mostrar u ocultar acciones. */
export function useModuleAccess() {
  const token = useAuthStore((state) => state.token)
  const query = useQuery({
    queryKey: ['permissions', 'me'],
    queryFn: adminApi.myPermissions,
    staleTime: 30 * 60 * 1000,
    enabled: Boolean(token),
  })

  const access = (code: ModuleCode) => query.data?.modules.find((item) => item.code === code)

  return {
    isLoading: query.isLoading,
    canView: (code: ModuleCode) => access(code)?.can_view ?? false,
    // Mientras no llega la respuesta se asume que no puede: es preferible un
    // botón que aparece un instante después a uno que promete una acción y da 403.
    canManage: (code: ModuleCode) => access(code)?.can_manage ?? false,
  }
}
