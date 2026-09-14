import { useState, type ReactNode } from 'react'
import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

import { NOTIFICATIONS_KEY } from '@/features/notifications/hooks/useNotifications'
import { configureHttp } from '@/services/http'
import { clearAuthSession, getAuthToken } from '@/store/auth.store'

configureHttp({ getToken: getAuthToken, onUnauthorized: clearAuthSession })

function createQueryClient(): QueryClient {
  /* Los avisos de la campanita se calculan sobre el estado del sistema, así
     que cualquier registro puede resolver uno: atender una cita, enviar un
     recordatorio, cargar un resultado, reponer stock. En vez de invalidarlos
     desde cada mutación, se recalculan cuando alguna termina bien. */
  const client: QueryClient = new QueryClient({
    mutationCache: new MutationCache({
      onSuccess: () => {
        void client.invalidateQueries({ queryKey: [NOTIFICATIONS_KEY] })
      },
    }),
    defaultOptions: {
      queries: {
        retry: 1,
        refetchOnWindowFocus: false,
        staleTime: 30_000,
      },
      mutations: { retry: 0 },
    },
  })
  return client
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient)

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}
