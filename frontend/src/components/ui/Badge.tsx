import type { HTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

export type BadgeVariant = 'neutral' | 'primary' | 'success' | 'warning' | 'danger' | 'info'

const variantStyles: Record<BadgeVariant, string> = {
  neutral: 'bg-muted/10 text-muted',
  primary: 'bg-primary/10 text-primary-dark',
  success: 'bg-success/15 text-primary-dark',
  warning: 'bg-warning/15 text-warning-dark',
  danger: 'bg-danger/10 text-danger',
  info: 'bg-info/10 text-info',
}

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
  dot?: boolean
}

export function Badge({ variant = 'neutral', dot = false, className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        variantStyles[variant],
        className,
      )}
      {...props}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}
