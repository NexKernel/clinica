import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { Role, User } from '@/types'

const STORAGE_KEY = 'estabridis.auth'

interface AuthState {
  token: string | null
  user: User | null
  status: 'idle' | 'loading' | 'authenticated' | 'unauthenticated'
  setSession: (token: string, user: User) => void
  setUser: (user: User) => void
  setStatus: (status: AuthState['status']) => void
  clearSession: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      status: 'idle',
      setSession: (token, user) => set({ token, user, status: 'authenticated' }),
      setUser: (user) => set({ user, status: 'authenticated' }),
      setStatus: (status) => set({ status }),
      clearSession: () => set({ token: null, user: null, status: 'unauthenticated' }),
    }),
    {
      name: STORAGE_KEY,
      partialize: (state) => ({ token: state.token, user: state.user }),
    },
  ),
)

export const getAuthToken = (): string | null => useAuthStore.getState().token
export const clearAuthSession = (): void => useAuthStore.getState().clearSession()

export function hasRole(user: User | null, roles?: Role[]): boolean {
  if (!roles || roles.length === 0) return true
  if (!user) return false
  return roles.includes(user.role)
}
