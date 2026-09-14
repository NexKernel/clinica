import { http } from '@/services/http'
import type {
  ClinicalDocument,
  DocumentCreatePayload,
  DocumentFilters,
  DocumentListItem,
  DocumentPayload,
  DocumentSheet,
  DocumentTemplateSummary,
  Page,
} from '@/types'

export const documentsApi = {
  templates: async (): Promise<DocumentTemplateSummary[]> => {
    const { data } = await http.get<DocumentTemplateSummary[]>('/documents/templates')
    return data
  },
  list: async (filters: DocumentFilters): Promise<Page<DocumentListItem>> => {
    const { data } = await http.get<Page<DocumentListItem>>('/documents', { params: filters })
    return data
  },
  forPatient: async (patientId: number): Promise<DocumentListItem[]> => {
    const { data } = await http.get<DocumentListItem[]>(`/documents/patient/${patientId}`)
    return data
  },
  get: async (id: number): Promise<ClinicalDocument> => {
    const { data } = await http.get<ClinicalDocument>(`/documents/${id}`)
    return data
  },
  create: async (payload: DocumentCreatePayload): Promise<ClinicalDocument> => {
    const { data } = await http.post<ClinicalDocument>('/documents', payload)
    return data
  },
  update: async (id: number, payload: DocumentPayload): Promise<ClinicalDocument> => {
    const { data } = await http.put<ClinicalDocument>(`/documents/${id}`, payload)
    return data
  },
  preview: async (id: number): Promise<DocumentSheet> => {
    const { data } = await http.get<DocumentSheet>(`/documents/${id}/preview`)
    return data
  },
  issue: async (id: number): Promise<ClinicalDocument> => {
    const { data } = await http.post<ClinicalDocument>(`/documents/${id}/issue`)
    return data
  },
  void: async (id: number, reason: string): Promise<ClinicalDocument> => {
    const { data } = await http.post<ClinicalDocument>(`/documents/${id}/void`, { reason })
    return data
  },
  remove: async (id: number): Promise<void> => {
    await http.delete(`/documents/${id}`)
  },
}
