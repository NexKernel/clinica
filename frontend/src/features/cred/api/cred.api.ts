import { http } from '@/services/http'
import type {
  CredCard,
  CredCatalogItem,
  CredEntry,
  CredEntryCreatePayload,
  CredEntryPayload,
  CredSheet,
} from '@/types'

export const credApi = {
  card: async (patientId: number): Promise<CredCard> => {
    const { data } = await http.get<CredCard>(`/cred/${patientId}`)
    return data
  },
  catalog: async (patientId: number): Promise<CredCatalogItem[]> => {
    const { data } = await http.get<CredCatalogItem[]>('/cred/catalog', {
      params: { patient_id: patientId },
    })
    return data
  },
  sheet: async (patientId: number): Promise<CredSheet> => {
    const { data } = await http.get<CredSheet>(`/cred/${patientId}/sheet`)
    return data
  },
  create: async (payload: CredEntryCreatePayload): Promise<CredEntry> => {
    const { data } = await http.post<CredEntry>('/cred', payload)
    return data
  },
  update: async (id: number, payload: CredEntryPayload): Promise<CredEntry> => {
    const { data } = await http.put<CredEntry>(`/cred/${id}`, payload)
    return data
  },
  remove: async (id: number): Promise<void> => {
    await http.delete(`/cred/${id}`)
  },
}
