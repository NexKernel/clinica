import { useQuery } from '@tanstack/react-query'

import { adminApi } from '@/features/admin/api/admin.api'
import { getErrorMessage } from '@/services/http'
import type { AuditFilters } from '@/types'

const ADMIN_KEY = 'admin'

export function useAuditLogs(filters: AuditFilters, enabled = true) {
  const query = useQuery({
    queryKey: [ADMIN_KEY, 'audit', filters],
    queryFn: () => adminApi.auditLogs(filters),
    placeholderData: (previous) => previous,
    enabled,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar la bitácora') : null,
  }
}

export function useAuditModules(enabled = true) {
  const query = useQuery({
    queryKey: [ADMIN_KEY, 'audit', 'modules'],
    queryFn: adminApi.auditModules,
    staleTime: 10 * 60 * 1000,
    enabled,
  })
  return { modules: query.data ?? [] }
}

export function usePermissionMatrix(enabled = true) {
  const query = useQuery({
    queryKey: [ADMIN_KEY, 'permissions'],
    queryFn: adminApi.permissionMatrix,
    staleTime: 30 * 60 * 1000,
    enabled,
  })
  return { matrix: query.data ?? [], isLoading: query.isLoading }
}
