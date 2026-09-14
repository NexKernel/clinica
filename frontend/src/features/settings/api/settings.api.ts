import { http } from '@/services/http'
import type { ClinicSettings, ClinicSettingsPayload, PublicBranding } from '@/types'

export const settingsApi = {
  branding: async (): Promise<PublicBranding> => {
    const { data } = await http.get<PublicBranding>('/settings/public')
    return data
  },
  get: async (): Promise<ClinicSettings> => {
    const { data } = await http.get<ClinicSettings>('/settings')
    return data
  },
  update: async (payload: ClinicSettingsPayload): Promise<ClinicSettings> => {
    const { data } = await http.put<ClinicSettings>('/settings', payload)
    return data
  },
  uploadLogo: async (file: File): Promise<ClinicSettings> => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await http.post<ClinicSettings>('/settings/logo', form)
    return data
  },
  deleteLogo: async (): Promise<ClinicSettings> => {
    const { data } = await http.delete<ClinicSettings>('/settings/logo')
    return data
  },
}
