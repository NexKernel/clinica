import { NavLink } from 'react-router-dom'

import { cn } from '@/lib/utils'
import type { NavItem } from '@/routes/navigation'

interface NavTileProps {
  item: NavItem
  size?: 'compact' | 'regular'
  onNavigate?: () => void
  className?: string
}

/** Elemento de navegación con ICONO ARRIBA + TEXTO DEBAJO. */
export function NavTile({ item, size = 'regular', onNavigate, className }: NavTileProps) {
  const Icon = item.icon

  return (
    <NavLink
      to={item.path}
      onClick={onNavigate}
      title={item.comingSoon ? `${item.label} · Próximamente` : item.label}
      className={({ isActive }) =>
        cn(
          'group relative flex w-full flex-col items-center justify-center gap-1.5 rounded-xl transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60',
          size === 'compact' ? 'px-0.5 py-2.5' : 'px-2 py-3',
          isActive
            ? 'bg-primary/10 text-primary-dark'
            : 'text-muted hover:bg-primary/5 hover:text-primary-dark',
          className,
        )
      }
    >
      {({ isActive }) => (
        <>
          <span
            className={cn(
              'absolute left-0 top-1/2 h-7 w-1 -translate-y-1/2 rounded-r-full bg-primary transition-opacity',
              isActive ? 'opacity-100' : 'opacity-0',
            )}
            aria-hidden="true"
          />
          <Icon
            className={cn(
              'shrink-0 transition-transform group-hover:scale-105',
              size === 'compact' ? 'h-5 w-5' : 'h-[22px] w-[22px]',
              isActive ? 'text-primary' : 'text-current',
            )}
            strokeWidth={isActive ? 2.2 : 1.8}
          />
          <span
            className={cn(
              'w-full truncate text-center font-medium leading-tight',
              size === 'compact' ? 'text-[10px]' : 'text-[11px]',
              item.comingSoon && !isActive && 'opacity-80',
            )}
          >
            {item.label}
          </span>
        </>
      )}
    </NavLink>
  )
}
