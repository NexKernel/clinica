import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { usersApi } from '@/features/users/api/users.api'
import { getErrorMessage } from '@/services/http'
import type { UserCreatePayload, UserFilters, UserUpdatePayload } from '@/types'

const USERS_KEY = 'users'
const ROLES_KEY = ['roles'] as const

export function useRoles() {
  const query = useQuery({
    queryKey: ROLES_KEY,
    queryFn: usersApi.roles,
    staleTime: 10 * 60 * 1000,
  })

  return { roles: query.data ?? [], isLoading: query.isLoading }
}

export function useUsersList(filters: UserFilters) {
  const query = useQuery({
    queryKey: [USERS_KEY, filters],
    queryFn: () => usersApi.list(filters),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar los usuarios') : null,
    refetch: query.refetch,
  }
}

/** Mutaciones de gestión; refrescan el listado al completarse. */
export function useUserActions() {
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: [USERS_KEY] })

  const create = useMutation({
    mutationFn: (payload: UserCreatePayload) => usersApi.create(payload),
    onSuccess: invalidate,
  })

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: UserUpdatePayload }) =>
      usersApi.update(id, payload),
    onSuccess: invalidate,
  })

  const setStatus = useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) =>
      usersApi.setStatus(id, isActive),
    onSuccess: invalidate,
  })

  const resetPassword = useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) =>
      usersApi.resetPassword(id, password),
  })

  return { create, update, setStatus, resetPassword }
}
