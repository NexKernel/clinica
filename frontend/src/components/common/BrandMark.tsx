import { cn } from '@/lib/utils'

interface BrandMarkProps {
  className?: string
  iconClassName?: string
  /** Logo cargado desde Configuración; si no existe se usa el isotipo por defecto. */
  src?: string | null
  alt?: string
}

/** Isotipo Estabridis: pulso clínico sobre el color primario de marca. */
export function BrandMark({ className, iconClassName, src, alt = 'Logotipo' }: BrandMarkProps) {
  if (src) {
    return (
      <span
        className={cn(
          'inline-flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl bg-surface',
          className,
        )}
      >
        <img src={src} alt={alt} className="h-full w-full object-contain" />
      </span>
    )
  }

  return (
    <span
      className={cn(
        'inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white',
        className,
      )}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
        className={cn('h-5 w-5', iconClassName)}
      >
        <path
          d="M3 12.5h3.2l1.9-4.6L11.6 18l2.2-5.5H21"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  )
}
