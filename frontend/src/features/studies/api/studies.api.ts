import { http } from '@/services/http'
import type {
  Attachment,
  Page,
  ShareLink,
  SharedStudy,
  Study,
  StudyFilters,
  StudyListItem,
  StudyPayload,
  StudyResultPayload,
  StudyStatus,
} from '@/types'

export const studiesApi = {
  list: async (filters: StudyFilters): Promise<Page<StudyListItem>> => {
    const { data } = await http.get<Page<StudyListItem>>('/studies', { params: filters })
    return data
  },
  forPatient: async (patientId: number): Promise<StudyListItem[]> => {
    const { data } = await http.get<StudyListItem[]>(`/studies/patient/${patientId}`)
    return data
  },
  get: async (id: number): Promise<Study> => {
    const { data } = await http.get<Study>(`/studies/${id}`)
    return data
  },
  create: async (payload: StudyPayload): Promise<Study> => {
    const { data } = await http.post<Study>('/studies', payload)
    return data
  },
  update: async (id: number, payload: StudyPayload): Promise<Study> => {
    const { data } = await http.put<Study>(`/studies/${id}`, payload)
    return data
  },
  registerResult: async (id: number, payload: StudyResultPayload): Promise<Study> => {
    const { data } = await http.post<Study>(`/studies/${id}/result`, payload)
    return data
  },
  changeStatus: async (id: number, status: StudyStatus): Promise<Study> => {
    const { data } = await http.patch<Study>(`/studies/${id}/status`, { status })
    return data
  },
  uploadAttachment: async (
    id: number,
    file: File,
    description?: string,
  ): Promise<Attachment> => {
    const form = new FormData()
    form.append('file', file)
    if (description) form.append('description', description)
    const { data } = await http.post<Attachment>(`/studies/${id}/attachments`, form)
    return data
  },
  deleteAttachment: async (attachmentId: number): Promise<void> => {
    await http.delete(`/studies/attachments/${attachmentId}`)
  },
  downloadAttachment: async (attachmentId: number): Promise<Blob> => {
    const { data } = await http.get<Blob>(`/studies/attachments/${attachmentId}/download`, {
      responseType: 'blob',
    })
    return data
  },
  share: async (id: number): Promise<ShareLink> => {
    const { data } = await http.post<ShareLink>(`/studies/${id}/share`)
    return data
  },
  revokeShare: async (id: number): Promise<Study> => {
    const { data } = await http.delete<Study>(`/studies/${id}/share`)
    return data
  },
  shared: async (token: string): Promise<SharedStudy> => {
    const { data } = await http.get<SharedStudy>(`/studies/shared/${token}`)
    return data
  },
}
