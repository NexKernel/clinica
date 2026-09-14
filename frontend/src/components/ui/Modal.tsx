import { useCallback, useEffect, useId, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'

import { cn } from '@/lib/utils'

type ModalSize = 'sm' | 'md' | 'lg' | 'xl'

const sizeStyles: Record<ModalSize, string> = {
  sm: 'sm:max-w-sm',
  md: 'sm:max-w-lg',
  lg: 'sm:max-w-2xl',
  xl: 'sm:max-w-4xl',
}

/* Bloqueo del scroll de fondo: se cuentan los modales abiertos para que al
   cerrar uno no se libere el scroll mientras otro sigue visible. */
let openModals = 0
let previousOverflow = ''

function lockBodyScroll(): void {
  if (openModals === 0) {
    previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  }
  openModals += 1
}

function unlockBodyScroll(): void {
  openModals = Math.max(0, openModals - 1)
  if (openModals === 0) {
    document.body.style.overflow = previousOverflow
  }
}

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'

interface ModalProps {
  open: boolean
  onClose: () => void
  title?: string
  description?: string
  size?: ModalSize
  /** Acciones fijas al pie: permanecen visibles aunque el contenido se desplace. */
  footer?: ReactNode
  children: ReactNode
}

export function Modal({
  open,
  onClose,
  title,
  description,
  size = 'md',
  footer,
  children,
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  // Un arrastre iniciado dentro del panel no debe cerrar el modal al soltarlo
  // sobre el fondo (por ejemplo, al seleccionar texto de un campo).
  const pressedBackdrop = useRef(false)
  const titleId = useId()

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
        return
      }
      if (event.key !== 'Tab') return

      const panel = panelRef.current
      if (!panel) return
      const focusable = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (element) => element.offsetParent !== null,
      )
      if (focusable.length === 0) return

      const first = focusable[0] as HTMLElement
      const last = focusable[focusable.length - 1] as HTMLElement
      const active = document.activeElement

      // El foco circula dentro del diálogo mientras está abierto.
      if (event.shiftKey && (active === first || !panel.contains(active))) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
    },
    [onClose],
  )

  useEffect(() => {
    if (!open) return

    lockBodyScroll()
    document.addEventListener('keydown', handleKeyDown)

    const previouslyFocused = document.activeElement as HTMLElement | null
    panelRef.current?.focus({ preventScroll: true })

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      unlockBodyScroll()
      previouslyFocused?.focus?.({ preventScroll: true })
    }
  }, [open, handleKeyDown])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4">
      <div
        className="absolute inset-0 bg-foreground/25 backdrop-blur-[2px]"
        aria-hidden="true"
        onMouseDown={() => {
          pressedBackdrop.current = true
        }}
        onMouseUp={() => {
          if (pressedBackdrop.current) onClose()
          pressedBackdrop.current = false
        }}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        aria-label={title ? undefined : 'Diálogo'}
        tabIndex={-1}
        onMouseDown={() => {
          pressedBackdrop.current = false
        }}
        className={cn(
          'relative z-10 flex w-full flex-col overflow-hidden animate-fade-in',
          'rounded-t-2xl border border-border bg-surface shadow-popover outline-none sm:rounded-2xl',
          // El panel nunca excede la pantalla: el contenido se desplaza dentro.
          'modal-panel',
          sizeStyles[size],
        )}
      >
        {(title || description) && (
          <div className="flex shrink-0 items-start justify-between gap-4 border-b border-border px-5 py-4">
            <div className="min-w-0">
              {title && (
                <h2 id={titleId} className="text-base font-semibold text-foreground">
                  {title}
                </h2>
              )}
              {description && <p className="mt-0.5 text-sm text-muted">{description}</p>}
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Cerrar"
              className="shrink-0 rounded-lg p-1.5 text-muted transition-colors hover:bg-primary/10 hover:text-primary-dark"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        <div className="scrollbar-thin flex-1 overflow-y-auto overscroll-contain px-5 py-4">
          {children}
        </div>

        {footer && (
          <div className="flex shrink-0 flex-wrap justify-end gap-2 border-t border-border px-5 py-3.5">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}
