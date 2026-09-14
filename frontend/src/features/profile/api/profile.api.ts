import { http } from '@/services/http'
import type { PasswordChangePayload, ProfileUpdatePayload, User } from '@/types'

export const profileApi = {
  get: async (): Promise<User> => {
    const { data } = await http.get<User>('/users/me')
    return data
  },
  update: async (payload: ProfileUpdatePayload): Promise<User> => {
    const { data } = await http.patch<User>('/users/me', payload)
    return data
  },
  changePassword: async (payload: PasswordChangePayload): Promise<User> => {
    const { data } = await http.post<User>('/users/me/password', payload)
    return data
  },
}
