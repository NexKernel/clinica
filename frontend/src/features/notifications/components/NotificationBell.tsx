import {
  AlertTriangle,
  Bell,
  BellRing,
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  FlaskConical,
  PackageX,
  ShoppingCart,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Dropdown } from '@/components/ui'
import { useNotifications } from '@/features/notifications/hooks/useNotifications'
import { cn } from '@/lib/utils'
import { ROUTES } from '@/routes/paths'
import type { AppNotification, NotificationSeverity } from '@/types'
import type { LucideIcon } from 'lucide-react'

/* El módulo que devuelve el servidor decide a dónde lleva el aviso; la
   campanita no necesita conocer cada código, solo el módulo que lo origina. */
const MODULE_ROUTES: Record<string, string> = {
  APPOINTMENTS: ROUTES.appointments,
  REMINDERS: ROUTES.reminders,
  STUDIES: ROUTES.studies,
  PHARMACY: ROUTES.pharmacy,
  PURCHASES: ROUTES.purchases,
}

const ICONS: Record<string, LucideIcon> = {
  pending_appointments: CalendarClock,
  overdue_reminders: BellRing,
  pending_studies: FlaskConical,
  expired_products: PackageX,
  low_stock: PackageX,
  expiring_products: AlertTriangle,
  draft_purchases: ShoppingCart,
}

const SEVERITY_STYLES: Record<NotificationSeverity, { icon: string; dot: string }> = {
  info: { icon: 'bg-info/10 text-info', dot: 'bg-info' },
  warning: { icon: 'bg-warning/15 text-warning-dark', dot: 'bg-warning' },
  danger: { icon: 'bg-danger/10 text-danger', dot: 'bg-danger' },
}

/** Tope de la burbuja: más allá de 99 el número deja de caber y deja de importar. */
const BADGE_MAX = 99

export function NotificationBell() {
  const navigate = useNavigate()
  const { items, total, isLoading, error } = useNotifications()

  const open = (notification: AppNotification, close: () => void) => {
    const target = MODULE_ROUTES[notification.module]
    close()
    if (target) navigate(target)
  }

  return (
    <Dropdown
      menuClassName="w-[21rem] max-w-[calc(100vw-1.5rem)] p-0"
      trigger={({ toggle }) => (
        <button
          type="button"
          onClick={toggle}
          aria-label={total > 0 ? `Notificaciones: ${total} pendientes` : 'Notificaciones'}
          className="relative inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted transition-colors hover:bg-primary/10 hover:text-primary-dark"
        >
          <Bell className="h-[18px] w-[18px]" />
          {total > 0 && (
            <span className="absolute -right-0.5 -top-0.5 inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full border-2 border-surface bg-danger px-1 text-[10px] font-bold leading-none text-white">
              {total > BADGE_MAX ? `${BADGE_MAX}+` : total}
            </span>
          )}
        </button>
      )}
    >
      {({ close }) => (
        <div>
          <div className="flex items-baseline justify-between border-b border-border px-4 py-3">
            <p className="text-sm font-semibold text-foreground">Avisos</p>
            {items.length > 0 && (
              <span className="text-xs text-muted">
                {items.length} {items.length === 1 ? 'asunto' : 'asuntos'}
              </span>
            )}
          </div>

          <div className="max-h-[22rem] overflow-y-auto p-1.5">
            {isLoading && <p className="px-2.5 py-6 text-center text-sm text-muted">Cargando…</p>}

            {!isLoading && error && (
              <p className="px-2.5 py-6 text-center text-sm text-danger">{error}</p>
            )}

            {!isLoading && !error && items.length === 0 && (
              <div className="flex flex-col items-center gap-2 px-2.5 py-7 text-center">
                <CheckCircle2 className="h-7 w-7 text-success" />
                <p className="text-sm font-medium text-foreground">Todo al día</p>
                <p className="text-xs text-muted">No hay pendientes que atender por ahora.</p>
              </div>
            )}

            {!isLoading &&
              !error &&
              items.map((item) => {
                const Icon = ICONS[item.code] ?? Bell
                const styles = SEVERITY_STYLES[item.severity]
                const target = MODULE_ROUTES[item.module]

                return (
                  <button
                    key={item.code}
                    type="button"
                    onClick={() => open(item, close)}
                    disabled={!target}
                    className="group flex w-full items-start gap-3 rounded-xl px-2.5 py-2.5 text-left transition-colors hover:bg-primary/10 disabled:cursor-default disabled:hover:bg-transparent"
                  >
                    <span
                      className={cn(
                        'mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
                        styles.icon,
                      )}
                    >
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium text-foreground">
                          {item.title}
                        </span>
                        <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', styles.dot)} />
                      </span>
                      <span className="mt-0.5 block text-xs leading-snug text-muted">
                        {item.description}
                      </span>
                    </span>
                    {target && (
                      <ChevronRight className="mt-2 h-4 w-4 shrink-0 text-muted transition-colors group-hover:text-primary-dark" />
                    )}
                  </button>
                )
              })}
          </div>
        </div>
      )}
    </Dropdown>
  )
}
