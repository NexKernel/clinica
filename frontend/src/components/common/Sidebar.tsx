import { BrandMark } from '@/components/common/BrandMark'
import { NavTile } from '@/components/common/NavTile'
import { useClinicIdentity } from '@/features/settings/hooks/useClinicIdentity'
import type { NavItem } from '@/routes/navigation'

interface SidebarProps {
  items: NavItem[]
}

export function Sidebar({ items }: SidebarProps) {
  const clinic = useClinicIdentity()

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-20 flex-col border-r border-border bg-surface md:flex lg:w-28">
      <div className="flex flex-col items-center gap-2 px-2 py-4 lg:py-5">
        <BrandMark
          className="h-9 w-9 lg:h-10 lg:w-10"
          src={clinic.logoUrl}
          alt={clinic.name}
        />
        <span className="text-center text-[10px] font-bold tracking-[0.14em] text-primary-dark lg:text-[11px]">
          {clinic.shortName}
        </span>
      </div>

      <div className="mx-3 h-px bg-border" />

      <nav
        aria-label="Navegación principal"
        className="scrollbar-thin flex-1 space-y-1 overflow-y-auto px-2 py-3 lg:px-3"
      >
        {items.map((item) => (
          <NavTile key={item.key} item={item} size="compact" className="lg:px-2 lg:py-3" />
        ))}
      </nav>

      <div className="px-2 pb-4 pt-2 text-center">
        <p className="text-[9px] leading-tight text-muted lg:text-[10px]">{clinic.location}</p>
      </div>
    </aside>
  )
}
