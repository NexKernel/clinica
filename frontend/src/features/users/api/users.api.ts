import { http } from '@/services/http'
import type {
  RoleOption,
  User,
  UserCreatePayload,
  UserFilters,
  UserListResponse,
  UserUpdatePayload,
} from '@/types'

export const usersApi = {
  roles: async (): Promise<RoleOption[]> => {
    const { data } = await http.get<RoleOption[]>('/roles')
    return data
  },
  list: async (filters: UserFilters): Promise<UserListResponse> => {
    const { data } = await http.get<UserListResponse>('/users', {
      params: {
        page: filters.page,
        page_size: filters.page_size,
        ...(filters.search ? { search: filters.search } : {}),
        ...(filters.role ? { role: filters.role } : {}),
        ...(filters.is_active === undefined ? {} : { is_active: filters.is_active }),
      },
    })
    return data
  },
  create: async (payload: UserCreatePayload): Promise<User> => {
    const { data } = await http.post<User>('/users', payload)
    return data
  },
  update: async (id: number, payload: UserUpdatePayload): Promise<User> => {
    const { data } = await http.patch<User>(`/users/${id}`, payload)
    return data
  },
  setStatus: async (id: number, isActive: boolean): Promise<User> => {
    const { data } = await http.patch<User>(`/users/${id}/status`, { is_active: isActive })
    return data
  },
  resetPassword: async (id: number, newPassword: string): Promise<User> => {
    const { data } = await http.post<User>(`/users/${id}/password`, { new_password: newPassword })
    return data
  },
}
