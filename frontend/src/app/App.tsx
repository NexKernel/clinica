import { FullScreenLoader } from '@/components/ui'
import { useSessionBootstrap } from '@/features/auth/hooks/useAuth'
import { AppRoutes } from '@/routes'

export function App() {
  const isRestoringSession = useSessionBootstrap()

  if (isRestoringSession) return <FullScreenLoader />

  return <AppRoutes />
}
