import { useQuery } from '@tanstack/react-query'

import { dashboardApi } from '@/features/dashboard/api/dashboard.api'
import { getErrorMessage } from '@/services/http'

export function useDashboardSummary(day?: string) {
  const query = useQuery({
    queryKey: ['dashboard', 'summary', day ?? null],
    queryFn: () => dashboardApi.summary(day),
    staleTime: 60 * 1000,
  })

  return {
    summary: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar el resumen') : null,
  }
}
