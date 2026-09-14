import { http } from '@/services/http'
import type {
  Encounter,
  EncounterCreatePayload,
  EncounterFilters,
  EncounterListItem,
  EncounterUpdatePayload,
  MedicalRecord,
  Page,
} from '@/types'

export const encountersApi = {
  list: async (filters: EncounterFilters): Promise<Page<EncounterListItem>> => {
    const { data } = await http.get<Page<EncounterListItem>>('/encounters', { params: filters })
    return data
  },
  record: async (patientId: number): Promise<MedicalRecord> => {
    const { data } = await http.get<MedicalRecord>(`/encounters/record/${patientId}`)
    return data
  },
  get: async (id: number): Promise<Encounter> => {
    const { data } = await http.get<Encounter>(`/encounters/${id}`)
    return data
  },
  create: async (payload: EncounterCreatePayload): Promise<Encounter> => {
    const { data } = await http.post<Encounter>('/encounters', payload)
    return data
  },
  update: async (id: number, payload: EncounterUpdatePayload): Promise<Encounter> => {
    const { data } = await http.put<Encounter>(`/encounters/${id}`, payload)
    return data
  },
  finish: async (id: number): Promise<Encounter> => {
    const { data } = await http.post<Encounter>(`/encounters/${id}/finish`)
    return data
  },
  cancel: async (id: number, reason: string): Promise<Encounter> => {
    const { data } = await http.post<Encounter>(`/encounters/${id}/cancel`, { reason })
    return data
  },
}
