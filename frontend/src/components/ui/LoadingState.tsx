import { Spinner } from '@/components/ui/Spinner'
import { cn } from '@/lib/utils'

interface LoadingStateProps {
  label?: string
  className?: string
}

export function LoadingState({ label = 'Cargando…', className }: LoadingStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 px-6 py-12 text-muted',
        className,
      )}
    >
      <Spinner className="h-6 w-6 text-primary" />
      <p className="text-sm">{label}</p>
    </div>
  )
}

export function FullScreenLoader({ label = 'Cargando sistema…' }: LoadingStateProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <LoadingState label={label} />
    </div>
  )
}
