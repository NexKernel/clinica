export const ROLES = [
  'ADMIN',
  'RECEPCION',
  'MEDICO',
  'ENFERMERIA',
  'CAJA',
  'ALMACEN',
  'LABORATORIO',
  'OPTOMETRIA',
] as const

export type Role = (typeof ROLES)[number]

export interface User {
  id: number
  username: string
  email: string
  full_name: string
  role: Role
  role_name: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LoginPayload {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}
