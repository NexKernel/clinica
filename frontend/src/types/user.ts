import type { Role, User } from './auth'

export interface RoleOption {
  id: number
  code: Role
  name: string
  description: string | null
  is_active: boolean
}

export interface UserFilters {
  search?: string
  role?: string
  is_active?: boolean
  page: number
  page_size: number
}

export interface UserListResponse {
  items: User[]
  total: number
  page: number
  page_size: number
}

export interface UserCreatePayload {
  username: string
  email: string
  full_name: string
  role: string
  password: string
  is_active: boolean
}

export interface UserUpdatePayload {
  username: string
  email: string
  full_name: string
  role: string
  is_active: boolean
}
