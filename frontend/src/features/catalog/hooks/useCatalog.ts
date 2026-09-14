import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { catalogApi, practitionersApi } from '@/features/catalog/api/catalog.api'
import { getErrorMessage } from '@/services/http'
import type {
  MedicalServicePayload,
  PractitionerPayload,
  SpecialtyPayload,
} from '@/types'

const CATALOG_KEY = 'catalog'
const PRACTITIONERS_KEY = 'practitioners'
const LONG_CACHE = 10 * 60 * 1000

export function useSpecialties(onlyActive = false) {
  const query = useQuery({
    queryKey: [CATALOG_KEY, 'specialties', onlyActive],
    queryFn: () => catalogApi.specialties(onlyActive),
    staleTime: LONG_CACHE,
  })
  return { specialties: query.data ?? [], isLoading: query.isLoading }
}

export function useActiveServices() {
  const query = useQuery({
    queryKey: [CATALOG_KEY, 'services', 'active'],
    queryFn: catalogApi.activeServices,
    staleTime: LONG_CACHE,
  })
  return { services: query.data ?? [], isLoading: query.isLoading }
}

export function useServicesList(params: {
  page: number
  page_size: number
  search?: string
  kind?: string
  specialty_id?: number
  is_active?: boolean
}) {
  const query = useQuery({
    queryKey: [CATALOG_KEY, 'services', params],
    queryFn: () => catalogApi.services(params),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar el tarifario') : null,
  }
}

export function useActivePractitioners() {
  const query = useQuery({
    queryKey: [PRACTITIONERS_KEY, 'active'],
    queryFn: practitionersApi.active,
    staleTime: LONG_CACHE,
  })
  return { practitioners: query.data ?? [], isLoading: query.isLoading }
}

export function usePractitionersList(params: {
  page: number
  page_size: number
  search?: string
  specialty_id?: number
  is_active?: boolean
}) {
  const query = useQuery({
    queryKey: [PRACTITIONERS_KEY, params],
    queryFn: () => practitionersApi.list(params),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar los profesionales') : null,
  }
}

export function useCatalogActions() {
  const queryClient = useQueryClient()
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: [CATALOG_KEY] })
    void queryClient.invalidateQueries({ queryKey: [PRACTITIONERS_KEY] })
  }

  const createSpecialty = useMutation({
    mutationFn: (payload: SpecialtyPayload) => catalogApi.createSpecialty(payload),
    onSuccess: invalidate,
  })
  const updateSpecialty = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: SpecialtyPayload }) =>
      catalogApi.updateSpecialty(id, payload),
    onSuccess: invalidate,
  })
  const createService = useMutation({
    mutationFn: (payload: MedicalServicePayload) => catalogApi.createService(payload),
    onSuccess: invalidate,
  })
  const updateService = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: MedicalServicePayload }) =>
      catalogApi.updateService(id, payload),
    onSuccess: invalidate,
  })
  const createPractitioner = useMutation({
    mutationFn: (payload: PractitionerPayload) => practitionersApi.create(payload),
    onSuccess: invalidate,
  })
  const updatePractitioner = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: PractitionerPayload }) =>
      practitionersApi.update(id, payload),
    onSuccess: invalidate,
  })
  const setPractitionerStatus = useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) =>
      practitionersApi.setStatus(id, isActive),
    onSuccess: invalidate,
  })

  return {
    createSpecialty,
    updateSpecialty,
    createService,
    updateService,
    createPractitioner,
    updatePractitioner,
    setPractitionerStatus,
  }
}
