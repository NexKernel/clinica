import { useCallback, useEffect, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'

import { authApi } from '@/features/auth/api/auth.api'
import { getErrorMessage } from '@/services/http'
import { useAuthStore } from '@/store/auth.store'
import type { LoginPayload } from '@/types'

export function useAuth() {
  const user = useAuthStore((state) => state.user)
  const token = useAuthStore((state) => state.token)
  const status = useAuthStore((state) => state.status)
  const clearSession = useAuthStore((state) => state.clearSession)

  return {
    user,
    token,
    status,
    isAuthenticated: status === 'authenticated' && Boolean(token),
    logout: clearSession,
  }
}

export function useLogin() {
  const setSession = useAuthStore((state) => state.setSession)

  const mutation = useMutation({
    mutationFn: (payload: LoginPayload) => authApi.login(payload),
    onSuccess: (data) => setSession(data.access_token, data.user),
  })

  return {
    login: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error ? getErrorMessage(mutation.error, 'No se pudo iniciar sesión') : null,
    reset: mutation.reset,
  }
}

/** Restaura la sesión al recargar la página validando el token contra el backend. */
export function useSessionBootstrap(): boolean {
  const token = useAuthStore((state) => state.token)
  const status = useAuthStore((state) => state.status)
  const setUser = useAuthStore((state) => state.setUser)
  const setStatus = useAuthStore((state) => state.setStatus)
  const clearSession = useAuthStore((state) => state.clearSession)
  const started = useRef(false)

  const bootstrap = useCallback(async () => {
    if (!token) {
      setStatus('unauthenticated')
      return
    }
    setStatus('loading')
    try {
      const user = await authApi.me()
      setUser(user)
    } catch {
      clearSession()
    }
  }, [token, setStatus, setUser, clearSession])

  useEffect(() => {
    if (started.current) return
    started.current = true
    void bootstrap()
  }, [bootstrap])

  return status === 'idle' || status === 'loading'
}
