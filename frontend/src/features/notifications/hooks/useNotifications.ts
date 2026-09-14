import { useQuery } from '@tanstack/react-query'

import { notificationsApi } from '@/features/notifications/api/notifications.api'
import { getErrorMessage } from '@/services/http'

export const NOTIFICATIONS_KEY = 'notifications'
/* Los avisos se recalculan en cada consulta sobre los datos reales, así que
   basta con refrescarlos cada minuto; una cita atendida o un stock repuesto
   desaparecen solos de la campanita. */
const REFRESH_MS = 60 * 1000

export function useNotifications() {
  const query = useQuery({
    queryKey: [NOTIFICATIONS_KEY],
    queryFn: notificationsApi.feed,
    refetchInterval: REFRESH_MS,
    refetchOnWindowFocus: true,
    staleTime: REFRESH_MS / 2,
  })

  return {
    items: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar los avisos') : null,
  }
}
