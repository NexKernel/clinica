import { AlertCircle, AlertTriangle, CheckCircle2, Info, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type AlertVariant = 'success' | 'warning' | 'danger' | 'info'

const variantStyles: Record<AlertVariant, { box: string; icon: LucideIcon }> = {
  success: { box: 'border-primary/30 bg-primary/10 text-primary-dark', icon: CheckCircle2 },
  warning: { box: 'border-warning/30 bg-warning/10 text-warning-dark', icon: AlertTriangle },
  danger: { box: 'border-danger/30 bg-danger/10 text-danger', icon: AlertCircle },
  info: { box: 'border-info/30 bg-info/10 text-info', icon: Info },
}

interface AlertProps {
  variant?: AlertVariant
  children: ReactNode
  className?: string
}

export function Alert({ variant = 'info', children, className }: AlertProps) {
  const { box, icon: Icon } = variantStyles[variant]

  return (
    <div
      role={variant === 'danger' ? 'alert' : 'status'}
      className={cn(
        'flex items-start gap-2.5 rounded-xl border px-4 py-3 text-sm animate-fade-in',
        box,
        className,
      )}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <span className="min-w-0">{children}</span>
    </div>
  )
}
