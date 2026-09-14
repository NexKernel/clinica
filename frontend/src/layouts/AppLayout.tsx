import { Outlet, useLocation } from 'react-router-dom'

import { MobileNavigation } from '@/components/common/MobileNavigation'
import { Sidebar } from '@/components/common/Sidebar'
import { Topbar } from '@/components/common/Topbar'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { findNavItemByPath, getNavItemsForRole } from '@/routes/navigation'

export function AppLayout() {
  const { user } = useAuth()
  const location = useLocation()

  const items = getNavItemsForRole(user?.role)
  const current = findNavItemByPath(location.pathname)

  return (
    <div className="min-h-screen bg-background">
      <Sidebar items={items} />

      <div className="md:pl-20 lg:pl-28">
        <Topbar sectionTitle={current?.label ?? 'Dashboard'} />
        <main className="mx-auto w-full max-w-7xl px-4 pb-28 pt-5 sm:px-6 sm:pt-6 md:pb-10">
          <Outlet />
        </main>
      </div>

      <MobileNavigation items={items} />
    </div>
  )
}
