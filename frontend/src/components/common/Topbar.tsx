import { LogOut, Search, Settings, User as UserIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { BrandMark } from '@/components/common/BrandMark'
import { Avatar, Dropdown, DropdownItem } from '@/components/ui'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { NotificationBell } from '@/features/notifications/components/NotificationBell'
import { useClinicIdentity } from '@/features/settings/hooks/useClinicIdentity'
import { ROUTES } from '@/routes/paths'

interface TopbarProps {
  sectionTitle: string
}

export function Topbar({ sectionTitle }: TopbarProps) {
  const { user, logout } = useAuth()
  const clinic = useClinicIdentity()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate(ROUTES.login, { replace: true })
  }

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface/90 backdrop-blur">
      <div className="flex h-16 items-center gap-3 px-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <BrandMark className="h-9 w-9 md:hidden" src={clinic.logoUrl} alt={clinic.name} />
          <div className="min-w-0">
            <p className="caption hidden truncate sm:block">{clinic.name}</p>
            <h2 className="truncate text-[15px] font-semibold sm:text-base">{sectionTitle}</h2>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <button
            type="button"
            aria-label="Buscar"
            className="hidden h-10 w-10 items-center justify-center rounded-xl text-muted transition-colors hover:bg-primary/10 hover:text-primary-dark sm:inline-flex"
          >
            <Search className="h-[18px] w-[18px]" />
          </button>

          <NotificationBell />

          <Dropdown
            trigger={({ toggle }) => (
              <button
                type="button"
                onClick={toggle}
                className="flex items-center gap-2.5 rounded-xl py-1 pl-1 pr-1.5 transition-colors hover:bg-primary/10 sm:pr-3"
              >
                <Avatar name={user?.full_name ?? 'Usuario'} size="sm" />
                <span className="hidden text-left sm:block">
                  <span className="block max-w-[10rem] truncate text-sm font-medium text-foreground">
                    {user?.full_name}
                  </span>
                  <span className="block text-[11px] text-muted">{user?.role_name}</span>
                </span>
              </button>
            )}
          >
            {({ close }) => (
              <>
                <div className="border-b border-border px-3 pb-3 pt-2">
                  <p className="truncate text-sm font-semibold text-foreground">
                    {user?.full_name}
                  </p>
                  <p className="truncate text-xs text-muted">{user?.email}</p>
                </div>
                <div className="pt-1.5">
                  <DropdownItem
                    icon={<UserIcon className="h-4 w-4" />}
                    onClick={() => {
                      close()
                      navigate(ROUTES.profile)
                    }}
                  >
                    Mi perfil
                  </DropdownItem>
                  <DropdownItem
                    icon={<Settings className="h-4 w-4" />}
                    onClick={() => {
                      close()
                      navigate(ROUTES.settings)
                    }}
                  >
                    Configuración
                  </DropdownItem>
                  <DropdownItem
                    icon={<LogOut className="h-4 w-4" />}
                    variant="danger"
                    onClick={handleLogout}
                  >
                    Cerrar sesión
                  </DropdownItem>
                </div>
              </>
            )}
          </Dropdown>
        </div>
      </div>
    </header>
  )
}
