import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { credApi } from '@/features/cred/api/cred.api'
import { getErrorMessage } from '@/services/http'
import type { CredEntryCreatePayload, CredEntryPayload } from '@/types'

const CRED_KEY = 'cred'

export function useCredCard(patientId: number | null) {
  const query = useQuery({
    queryKey: [CRED_KEY, 'card', patientId],
    queryFn: () => credApi.card(patientId as number),
    enabled: patientId !== null,
  })

  return {
    card: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar el carné') : null,
  }
}

export function useCredCatalog(patientId: number | null, enabled: boolean) {
  const query = useQuery({
    queryKey: [CRED_KEY, 'catalog', patientId],
    queryFn: () => credApi.catalog(patientId as number),
    enabled: patientId !== null && enabled,
  })
  return { items: query.data ?? [], isLoading: query.isLoading }
}

export function useCredSheet(patientId: number | null) {
  const query = useQuery({
    queryKey: [CRED_KEY, 'sheet', patientId],
    queryFn: () => credApi.sheet(patientId as number),
    enabled: patientId !== null,
  })
  return {
    sheet: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo armar el carné') : null,
  }
}

export function useCredActions(patientId: number | null) {
  const client = useQueryClient()
  /* El carné se recompone entero en el servidor —el estado de una casilla
     depende de la edad y del calendario, no solo de lo que se acaba de
     anotar—, así que tras escribir se invalida y se vuelve a pedir. */
  const refresh = () => {
    void client.invalidateQueries({ queryKey: [CRED_KEY, 'card', patientId] })
    void client.invalidateQueries({ queryKey: [CRED_KEY, 'catalog', patientId] })
  }

  return {
    create: useMutation({
      mutationFn: (payload: CredEntryCreatePayload) => credApi.create(payload),
      onSuccess: refresh,
    }),
    update: useMutation({
      mutationFn: ({ id, payload }: { id: number; payload: CredEntryPayload }) =>
        credApi.update(id, payload),
      onSuccess: refresh,
    }),
    remove: useMutation({
      mutationFn: (id: number) => credApi.remove(id),
      onSuccess: refresh,
    }),
  }
}
