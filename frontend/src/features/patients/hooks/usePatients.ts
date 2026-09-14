import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { patientsApi } from '@/features/patients/api/patients.api'
import { getErrorMessage } from '@/services/http'
import type { PatientFilters, PatientPayload } from '@/types'

const PATIENTS_KEY = 'patients'

export function usePatientsList(filters: PatientFilters) {
  const query = useQuery({
    queryKey: [PATIENTS_KEY, filters],
    queryFn: () => patientsApi.list(filters),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar los pacientes') : null,
  }
}

export function usePatientStats() {
  const query = useQuery({
    queryKey: [PATIENTS_KEY, 'stats'],
    queryFn: patientsApi.stats,
    staleTime: 60 * 1000,
  })
  return { stats: query.data ?? null, isLoading: query.isLoading }
}

export function usePatient(publicId: string | null) {
  const query = useQuery({
    queryKey: [PATIENTS_KEY, 'detail', publicId],
    queryFn: () => patientsApi.get(publicId as string),
    enabled: publicId !== null,
  })

  return {
    patient: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar el paciente') : null,
  }
}

export function usePatientActions() {
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: [PATIENTS_KEY] })

  const create = useMutation({
    mutationFn: (payload: PatientPayload) => patientsApi.create(payload),
    onSuccess: invalidate,
  })

  const update = useMutation({
    mutationFn: ({ publicId, payload }: { publicId: string; payload: PatientPayload }) =>
      patientsApi.update(publicId, payload),
    onSuccess: invalidate,
  })

  const setStatus = useMutation({
    mutationFn: ({ publicId, isActive }: { publicId: string; isActive: boolean }) =>
      patientsApi.setStatus(publicId, isActive),
    onSuccess: invalidate,
  })

  return { create, update, setStatus }
}
