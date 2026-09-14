import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface DataItem {
  label: string
  value: ReactNode
  span?: boolean
}

interface DataSummaryProps {
  items: DataItem[]
  columns?: 2 | 3 | 4
  className?: string
}

const columnStyles: Record<2 | 3 | 4, string> = {
  2: 'sm:grid-cols-2',
  3: 'sm:grid-cols-2 lg:grid-cols-3',
  4: 'sm:grid-cols-2 lg:grid-cols-4',
}

/** Rejilla de datos etiquetados; usada en fichas y detalles de documento. */
export function DataSummary({ items, columns = 3, className }: DataSummaryProps) {
  return (
    <dl className={cn('grid grid-cols-1 gap-x-6 gap-y-4', columnStyles[columns], className)}>
      {items.map(({ label, value, span }) => (
        <div key={label} className={cn('min-w-0', span && 'sm:col-span-full')}>
          <dt className="caption uppercase tracking-wide">{label}</dt>
          <dd className="mt-0.5 whitespace-pre-line break-words text-sm text-foreground">
            {value === null || value === undefined || value === '' ? (
              <span className="text-muted">—</span>
            ) : (
              value
            )}
          </dd>
        </div>
      ))}
    </dl>
  )
}
