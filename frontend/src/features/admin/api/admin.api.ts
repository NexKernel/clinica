import { http } from '@/services/http'
import type { AuditFilters, AuditLog, Page, RolePermissions } from '@/types'

export const adminApi = {
  auditLogs: async (filters: AuditFilters): Promise<Page<AuditLog>> => {
    const { data } = await http.get<Page<AuditLog>>('/audit', { params: filters })
    return data
  },
  auditModules: async (): Promise<string[]> => {
    const { data } = await http.get<string[]>('/audit/modules')
    return data
  },
  permissionMatrix: async (): Promise<RolePermissions[]> => {
    const { data } = await http.get<RolePermissions[]>('/permissions')
    return data
  },
  myPermissions: async (): Promise<RolePermissions> => {
    const { data } = await http.get<RolePermissions>('/permissions/me')
    return data
  },
}
