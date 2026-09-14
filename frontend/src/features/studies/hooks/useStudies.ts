import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { studiesApi } from '@/features/studies/api/studies.api'
import { getErrorMessage } from '@/services/http'
import type { StudyFilters, StudyPayload, StudyResultPayload, StudyStatus } from '@/types'

const STUDIES_KEY = 'studies'

export function useStudiesList(filters: StudyFilters) {
  const query = useQuery({
    queryKey: [STUDIES_KEY, 'list', filters],
    queryFn: () => studiesApi.list(filters),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar los estudios') : null,
  }
}

export function useStudy(studyId: number | null) {
  const query = useQuery({
    queryKey: [STUDIES_KEY, 'detail', studyId],
    queryFn: () => studiesApi.get(studyId as number),
    enabled: studyId !== null,
  })

  return {
    study: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar el estudio') : null,
  }
}

export function usePatientStudies(patientId: number | null) {
  const query = useQuery({
    queryKey: [STUDIES_KEY, 'patient', patientId],
    queryFn: () => studiesApi.forPatient(patientId as number),
    enabled: patientId !== null,
  })
  return { studies: query.data ?? [], isLoading: query.isLoading }
}

export function useStudyActions() {
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: [STUDIES_KEY] })

  const create = useMutation({
    mutationFn: (payload: StudyPayload) => studiesApi.create(payload),
    onSuccess: invalidate,
  })

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: StudyPayload }) =>
      studiesApi.update(id, payload),
    onSuccess: invalidate,
  })

  const registerResult = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: StudyResultPayload }) =>
      studiesApi.registerResult(id, payload),
    onSuccess: invalidate,
  })

  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: StudyStatus }) =>
      studiesApi.changeStatus(id, status),
    onSuccess: invalidate,
  })

  const upload = useMutation({
    mutationFn: ({ id, file, description }: { id: number; file: File; description?: string }) =>
      studiesApi.uploadAttachment(id, file, description),
    onSuccess: invalidate,
  })

  const removeAttachment = useMutation({
    mutationFn: (attachmentId: number) => studiesApi.deleteAttachment(attachmentId),
    onSuccess: invalidate,
  })

  const share = useMutation({
    mutationFn: (id: number) => studiesApi.share(id),
    onSuccess: invalidate,
  })

  const revokeShare = useMutation({
    mutationFn: (id: number) => studiesApi.revokeShare(id),
    onSuccess: invalidate,
  })

  return { create, update, registerResult, changeStatus, upload, removeAttachment, share, revokeShare }
}

export function useSharedStudy(token: string | undefined) {
  const query = useQuery({
    queryKey: [STUDIES_KEY, 'shared', token],
    queryFn: () => studiesApi.shared(token as string),
    enabled: Boolean(token),
    retry: false,
  })

  return {
    study: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'El enlace no es válido') : null,
  }
}
