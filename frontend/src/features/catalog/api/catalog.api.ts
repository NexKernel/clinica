import { http } from '@/services/http'
import type {
  MedicalService,
  MedicalServicePayload,
  Page,
  Practitioner,
  PractitionerPayload,
  PractitionerSummary,
  Specialty,
  SpecialtyPayload,
} from '@/types'

export const catalogApi = {
  specialties: async (onlyActive = false): Promise<Specialty[]> => {
    const { data } = await http.get<Specialty[]>('/catalog/specialties', {
      params: { only_active: onlyActive },
    })
    return data
  },
  createSpecialty: async (payload: SpecialtyPayload): Promise<Specialty> => {
    const { data } = await http.post<Specialty>('/catalog/specialties', payload)
    return data
  },
  updateSpecialty: async (id: number, payload: SpecialtyPayload): Promise<Specialty> => {
    const { data } = await http.put<Specialty>(`/catalog/specialties/${id}`, payload)
    return data
  },
  services: async (params: {
    page: number
    page_size: number
    search?: string
    kind?: string
    specialty_id?: number
    is_active?: boolean
  }): Promise<Page<MedicalService>> => {
    const { data } = await http.get<Page<MedicalService>>('/catalog/services', { params })
    return data
  },
  activeServices: async (): Promise<MedicalService[]> => {
    const { data } = await http.get<MedicalService[]>('/catalog/services/active')
    return data
  },
  createService: async (payload: MedicalServicePayload): Promise<MedicalService> => {
    const { data } = await http.post<MedicalService>('/catalog/services', payload)
    return data
  },
  updateService: async (id: number, payload: MedicalServicePayload): Promise<MedicalService> => {
    const { data } = await http.put<MedicalService>(`/catalog/services/${id}`, payload)
    return data
  },
}

export const practitionersApi = {
  list: async (params: {
    page: number
    page_size: number
    search?: string
    specialty_id?: number
    is_active?: boolean
  }): Promise<Page<Practitioner>> => {
    const { data } = await http.get<Page<Practitioner>>('/practitioners', { params })
    return data
  },
  active: async (): Promise<PractitionerSummary[]> => {
    const { data } = await http.get<PractitionerSummary[]>('/practitioners/active')
    return data
  },
  get: async (id: number): Promise<Practitioner> => {
    const { data } = await http.get<Practitioner>(`/practitioners/${id}`)
    return data
  },
  create: async (payload: PractitionerPayload): Promise<Practitioner> => {
    const { data } = await http.post<Practitioner>('/practitioners', payload)
    return data
  },
  update: async (id: number, payload: PractitionerPayload): Promise<Practitioner> => {
    const { data } = await http.put<Practitioner>(`/practitioners/${id}`, payload)
    return data
  },
  setStatus: async (id: number, isActive: boolean): Promise<Practitioner> => {
    const { data } = await http.patch<Practitioner>(`/practitioners/${id}/status`, {
      is_active: isActive,
    })
    return data
  },
}
