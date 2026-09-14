import { useState } from 'react'
import { LayoutGrid } from 'lucide-react'

import { NavTile } from '@/components/common/NavTile'
import { Modal } from '@/components/ui'
import { cn } from '@/lib/utils'
import type { NavItem } from '@/routes/navigation'

interface MobileNavigationProps {
  items: NavItem[]
}

/** Barra inferior para mobile: ICONO ARRIBA + TEXTO DEBAJO. */
export function MobileNavigation({ items }: MobileNavigationProps) {
  const [menuOpen, setMenuOpen] = useState(false)

  const primaryItems = items.filter((item) => item.primary).slice(0, 4)
  const hasMore = items.length > primaryItems.length

  return (
    <>
      <nav
        aria-label="Navegación principal"
        className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-surface/95 backdrop-blur md:hidden"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <div
          className={cn(
            'mx-auto grid max-w-lg gap-0 px-1 py-1.5',
            hasMore ? 'grid-cols-5' : 'grid-cols-4',
          )}
        >
          {primaryItems.map((item) => (
            <NavTile key={item.key} item={item} size="compact" />
          ))}
          {hasMore && (
            <button
              type="button"
              onClick={() => setMenuOpen(true)}
              className="flex flex-col items-center justify-center gap-1.5 rounded-xl px-1 py-2.5 text-muted transition-colors hover:bg-primary/10 hover:text-primary-dark"
            >
              <LayoutGrid className="h-5 w-5" strokeWidth={1.8} />
              <span className="text-[10px] font-medium leading-tight">Más</span>
            </button>
          )}
        </div>
      </nav>

      <Modal open={menuOpen} onClose={() => setMenuOpen(false)} title="Módulos" size="sm">
        <div className="grid grid-cols-3 gap-2">
          {items.map((item) => (
            <NavTile
              key={item.key}
              item={item}
              onNavigate={() => setMenuOpen(false)}
              className="border border-border bg-background py-4"
            />
          ))}
        </div>
      </Modal>
    </>
  )
}
