export interface AuditLog {
  id: number
  user_id: number | null
  username: string | null
  role: string | null
  action: string
  module: string
  path: string
  entity_id: string | null
  status_code: number
  succeeded: boolean
  ip_address: string | null
  created_at: string
}

export interface ModuleAccess {
  code: string
  name: string
  can_view: boolean
  can_manage: boolean
}

export interface RolePermissions {
  role: string
  role_name: string
  modules: ModuleAccess[]
}

export interface AuditFilters {
  search?: string
  user_id?: number
  module?: string
  action?: string
  date_from?: string
  date_to?: string
  page: number
  page_size: number
}
