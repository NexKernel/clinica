import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { documentsApi } from '@/features/documents/api/documents.api'
import { getErrorMessage } from '@/services/http'
import type { DocumentCreatePayload, DocumentFilters, DocumentPayload } from '@/types'

const DOCUMENTS_KEY = 'documents'
/* El catálogo cambia sólo al sembrar plantillas nuevas: se cachea aparte y no
   se invalida junto con los documentos. */
const TEMPLATES_KEY = 'document-templates'

export function useDocumentTemplates() {
  const query = useQuery({
    queryKey: [TEMPLATES_KEY, 'list'],
    queryFn: () => documentsApi.templates(),
    staleTime: 10 * 60 * 1000,
  })

  return {
    templates: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar el catálogo') : null,
  }
}

export function useDocumentsList(filters: DocumentFilters) {
  const query = useQuery({
    queryKey: [DOCUMENTS_KEY, 'list', filters],
    queryFn: () => documentsApi.list(filters),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar los documentos') : null,
  }
}

export function useDocument(documentId: number | null) {
  const query = useQuery({
    queryKey: [DOCUMENTS_KEY, 'detail', documentId],
    queryFn: () => documentsApi.get(documentId as number),
    enabled: documentId !== null,
  })

  return {
    document: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar el documento') : null,
  }
}

export function usePatientDocuments(patientId: number | null) {
  const query = useQuery({
    queryKey: [DOCUMENTS_KEY, 'patient', patientId],
    queryFn: () => documentsApi.forPatient(patientId as number),
    enabled: patientId !== null,
  })
  return { documents: query.data ?? [], isLoading: query.isLoading }
}

/** Hoja renderizada. El borrador se rearma en el servidor en cada consulta. */
export function useDocumentSheet(documentId: number | null) {
  const query = useQuery({
    queryKey: [DOCUMENTS_KEY, 'sheet', documentId],
    queryFn: () => documentsApi.preview(documentId as number),
    enabled: documentId !== null,
  })

  return {
    sheet: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo generar la vista previa') : null,
  }
}

export function useDocumentActions() {
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: [DOCUMENTS_KEY] })
  /* Emitir un informe completa el estudio vinculado; el listado de estudios
     queda obsoleto y debe recargarse. */
  const invalidateAll = () => {
    invalidate()
    queryClient.invalidateQueries({ queryKey: ['studies'] })
  }

  const create = useMutation({
    mutationFn: (payload: DocumentCreatePayload) => documentsApi.create(payload),
    onSuccess: invalidate,
  })

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: DocumentPayload }) =>
      documentsApi.update(id, payload),
    onSuccess: invalidate,
  })

  const issue = useMutation({
    mutationFn: (id: number) => documentsApi.issue(id),
    onSuccess: invalidateAll,
  })

  const voidDocument = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => documentsApi.void(id, reason),
    onSuccess: invalidate,
  })

  const remove = useMutation({
    mutationFn: (id: number) => documentsApi.remove(id),
    onSuccess: invalidate,
  })

  return { create, update, issue, voidDocument, remove }
}
