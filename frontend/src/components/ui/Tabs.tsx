import type { LucideIcon } from 'lucide-react'

import { cn } from '@/lib/utils'

export interface TabItem {
  key: string
  label: string
  icon?: LucideIcon
  /** Marca visual cuando la pestaña contiene errores pendientes. */
  hasError?: boolean
}

interface TabsProps {
  items: TabItem[]
  active: string
  onChange: (key: string) => void
  className?: string
}

export function Tabs({ items, active, onChange, className }: TabsProps) {
  return (
    <div
      role="tablist"
      className={cn('scrollbar-thin -mx-1 flex gap-1 overflow-x-auto px-1 pb-1', className)}
    >
      {items.map((item) => {
        const Icon = item.icon
        const isActive = item.key === active

        return (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(item.key)}
            className={cn(
              'inline-flex shrink-0 items-center gap-2 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-colors',
              isActive
                ? 'bg-primary/10 text-primary-dark'
                : 'text-muted hover:bg-primary/5 hover:text-primary-dark',
            )}
          >
            {Icon && <Icon className="h-4 w-4" />}
            {item.label}
            {item.hasError && <span className="h-1.5 w-1.5 rounded-full bg-danger" />}
          </button>
        )
      })}
    </div>
  )
}
