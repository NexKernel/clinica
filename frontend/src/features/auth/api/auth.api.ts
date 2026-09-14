import { http } from '@/services/http'
import type { LoginPayload, LoginResponse, User } from '@/types'

export const authApi = {
  login: async (payload: LoginPayload): Promise<LoginResponse> => {
    const { data } = await http.post<LoginResponse>('/auth/login', payload)
    return data
  },
  me: async (): Promise<User> => {
    const { data } = await http.get<User>('/auth/me')
    return data
  },
}
