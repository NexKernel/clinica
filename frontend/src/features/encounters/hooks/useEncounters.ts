import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { encountersApi } from '@/features/encounters/api/encounters.api'
import { getErrorMessage } from '@/services/http'
import type {
  EncounterCreatePayload,
  EncounterFilters,
  EncounterUpdatePayload,
} from '@/types'

const ENCOUNTERS_KEY = 'encounters'

export function useEncountersList(filters: EncounterFilters) {
  const query = useQuery({
    queryKey: [ENCOUNTERS_KEY, 'list', filters],
    queryFn: () => encountersApi.list(filters),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar las atenciones') : null,
  }
}

export function useEncounter(encounterId: number | null) {
  const query = useQuery({
    queryKey: [ENCOUNTERS_KEY, 'detail', encounterId],
    queryFn: () => encountersApi.get(encounterId as number),
    enabled: encounterId !== null,
  })

  return {
    encounter: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar la atención') : null,
  }
}

/** Últimas atenciones del paciente, para vincularlas desde otros módulos.
 *  `enabled` evita la consulta cuando el perfil no puede ver atenciones. */
export function usePatientEncounters(patientId: number | null, enabled = true) {
  const filters: EncounterFilters = { page: 1, page_size: 20, patient_id: patientId ?? undefined }

  const query = useQuery({
    queryKey: [ENCOUNTERS_KEY, 'list', filters],
    queryFn: () => encountersApi.list(filters),
    enabled: enabled && patientId !== null,
  })

  return { encounters: query.data?.items ?? [], isLoading: query.isLoading }
}

export function useMedicalRecord(patientId: number | null) {
  const query = useQuery({
    queryKey: [ENCOUNTERS_KEY, 'record', patientId],
    queryFn: () => encountersApi.record(patientId as number),
    enabled: patientId !== null,
  })

  return {
    record: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error
      ? getErrorMessage(query.error, 'No se pudo cargar la historia clínica')
      : null,
  }
}

export function useEncounterActions() {
  const queryClient = useQueryClient()
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: [ENCOUNTERS_KEY] })
    void queryClient.invalidateQueries({ queryKey: ['appointments'] })
  }

  const create = useMutation({
    mutationFn: (payload: EncounterCreatePayload) => encountersApi.create(payload),
    onSuccess: invalidate,
  })

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: EncounterUpdatePayload }) =>
      encountersApi.update(id, payload),
    onSuccess: invalidate,
  })

  const finish = useMutation({
    mutationFn: (id: number) => encountersApi.finish(id),
    onSuccess: invalidate,
  })

  const cancel = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      encountersApi.cancel(id, reason),
    onSuccess: invalidate,
  })

  return { create, update, finish, cancel }
}
