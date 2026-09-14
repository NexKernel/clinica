import { useMutation } from '@tanstack/react-query'

import { profileApi } from '@/features/profile/api/profile.api'
import { getErrorMessage } from '@/services/http'
import { useAuthStore } from '@/store/auth.store'
import type { PasswordChangePayload, ProfileUpdatePayload } from '@/types'

export function useUpdateProfile() {
  const setUser = useAuthStore((state) => state.setUser)

  const mutation = useMutation({
    mutationFn: (payload: ProfileUpdatePayload) => profileApi.update(payload),
    onSuccess: (user) => setUser(user),
  })

  return {
    updateProfile: mutation.mutateAsync,
    isLoading: mutation.isPending,
    isSuccess: mutation.isSuccess,
    error: mutation.error ? getErrorMessage(mutation.error, 'No se pudo guardar el perfil') : null,
    reset: mutation.reset,
  }
}

export function useChangePassword() {
  const setUser = useAuthStore((state) => state.setUser)

  const mutation = useMutation({
    mutationFn: (payload: PasswordChangePayload) => profileApi.changePassword(payload),
    onSuccess: (user) => setUser(user),
  })

  return {
    changePassword: mutation.mutateAsync,
    isLoading: mutation.isPending,
    isSuccess: mutation.isSuccess,
    error: mutation.error
      ? getErrorMessage(mutation.error, 'No se pudo actualizar la contraseña')
      : null,
    reset: mutation.reset,
  }
}
