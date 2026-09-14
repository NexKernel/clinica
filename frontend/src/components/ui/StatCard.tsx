import type { LucideIcon } from 'lucide-react'
import { TrendingDown, TrendingUp } from 'lucide-react'

import { Card } from '@/components/ui/Card'
import { cn } from '@/lib/utils'

export type StatTone = 'primary' | 'info' | 'warning' | 'danger'

const toneStyles: Record<StatTone, string> = {
  primary: 'bg-primary/10 text-primary-dark',
  info: 'bg-info/10 text-info',
  warning: 'bg-warning/15 text-warning-dark',
  danger: 'bg-danger/10 text-danger',
}

interface StatCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  tone?: StatTone
  trend?: { value: string; direction: 'up' | 'down' }
  hint?: string
  isLoading?: boolean
}

export function StatCard({
  label,
  value,
  icon: Icon,
  tone = 'primary',
  trend,
  hint,
  isLoading = false,
}: StatCardProps) {
  const TrendIcon = trend?.direction === 'down' ? TrendingDown : TrendingUp

  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-muted">{label}</p>
        <span
          className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl',
            toneStyles[tone],
          )}
        >
          <Icon className="h-4 w-4" />
        </span>
      </div>

      {isLoading ? (
        <div className="mt-4 h-8 w-20 animate-pulse rounded-lg bg-border/70" />
      ) : (
        <p className="mt-3 text-2xl font-semibold tracking-tight text-foreground sm:text-[1.75rem]">
          {value}
        </p>
      )}

      <div className="mt-2 flex items-center gap-2">
        {trend && (
          <span
            className={cn(
              'inline-flex items-center gap-1 text-xs font-semibold',
              trend.direction === 'down' ? 'text-danger' : 'text-primary-dark',
            )}
          >
            <TrendIcon className="h-3.5 w-3.5" />
            {trend.value}
          </span>
        )}
        {hint && <span className="truncate text-xs text-muted">{hint}</span>}
      </div>
    </Card>
  )
}
