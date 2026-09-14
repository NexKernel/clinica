import { http } from '@/services/http'
import type {
  Page,
  Patient,
  PatientFilters,
  PatientPayload,
  PatientStats,
  PatientSummary,
} from '@/types'

export const patientsApi = {
  list: async (filters: PatientFilters): Promise<Page<Patient>> => {
    const { data } = await http.get<Page<Patient>>('/patients', {
      params: {
        page: filters.page,
        page_size: filters.page_size,
        ...(filters.search ? { search: filters.search } : {}),
        ...(filters.is_active === undefined ? {} : { is_active: filters.is_active }),
      },
    })
    return data
  },
  search: async (term: string): Promise<PatientSummary[]> => {
    const { data } = await http.get<PatientSummary[]>('/patients/search', { params: { term } })
    return data
  },
  stats: async (): Promise<PatientStats> => {
    const { data } = await http.get<PatientStats>('/patients/stats')
    return data
  },
  get: async (publicId: string): Promise<Patient> => {
    const { data } = await http.get<Patient>(`/patients/${publicId}`)
    return data
  },
  findByDocument: async (
    documentType: string,
    documentNumber: string,
  ): Promise<Patient | null> => {
    const { data } = await http.get<Patient | null>('/patients/by-document', {
      params: { document_type: documentType, document_number: documentNumber },
    })
    return data
  },
  create: async (payload: PatientPayload): Promise<Patient> => {
    const { data } = await http.post<Patient>('/patients', payload)
    return data
  },
  update: async (publicId: string, payload: PatientPayload): Promise<Patient> => {
    const { data } = await http.put<Patient>(`/patients/${publicId}`, payload)
    return data
  },
  setStatus: async (publicId: string, isActive: boolean): Promise<Patient> => {
    const { data } = await http.patch<Patient>(`/patients/${publicId}/status`, {
      is_active: isActive,
    })
    return data
  },
}
