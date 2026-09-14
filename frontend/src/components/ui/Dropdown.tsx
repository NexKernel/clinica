import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { cn } from '@/lib/utils'

const MENU_OFFSET = 8
const ESTIMATED_MENU_HEIGHT = 220

interface Position {
  top: number
  left: number
  flipped: boolean
}

interface DropdownProps {
  trigger: (props: { open: boolean; toggle: () => void }) => ReactNode
  children: (props: { close: () => void }) => ReactNode
  align?: 'left' | 'right'
  className?: string
  menuClassName?: string
}

/**
 * El menú se renderiza en un portal para no quedar recortado por contenedores
 * con overflow (tablas con scroll horizontal, tarjetas, etc.).
 */
export function Dropdown({
  trigger,
  children,
  align = 'right',
  className,
  menuClassName,
}: DropdownProps) {
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState<Position | null>(null)
  const triggerRef = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    if (!open) return

    const updatePosition = () => {
      const rect = triggerRef.current?.getBoundingClientRect()
      if (!rect) return
      const flipped = rect.bottom + ESTIMATED_MENU_HEIGHT > window.innerHeight && rect.top > ESTIMATED_MENU_HEIGHT
      setPosition({
        top: flipped ? rect.top - MENU_OFFSET : rect.bottom + MENU_OFFSET,
        left: align === 'right' ? rect.right : rect.left,
        flipped,
      })
    }

    updatePosition()
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [open, align])

  useEffect(() => {
    if (!open) return

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) return
      setOpen(false)
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  return (
    <div ref={triggerRef} className={cn('relative inline-flex', className)}>
      {trigger({ open, toggle: () => setOpen((value) => !value) })}

      {open &&
        position &&
        createPortal(
          <div
            ref={menuRef}
            role="menu"
            style={{
              top: position.top,
              left: position.left,
              transform: `translate(${align === 'right' ? '-100%' : '0'}, ${
                position.flipped ? '-100%' : '0'
              })`,
            }}
            className={cn(
              'fixed z-50 min-w-[13rem] animate-fade-in overflow-hidden rounded-2xl border border-border bg-surface p-1.5 shadow-popover',
              menuClassName,
            )}
          >
            {children({ close: () => setOpen(false) })}
          </div>,
          document.body,
        )}
    </div>
  )
}

interface DropdownItemProps {
  onClick?: () => void
  icon?: ReactNode
  children: ReactNode
  variant?: 'default' | 'danger'
}

export function DropdownItem({ onClick, icon, children, variant = 'default' }: DropdownItemProps) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
        variant === 'danger'
          ? 'text-danger hover:bg-danger/10'
          : 'text-foreground hover:bg-primary/10 hover:text-primary-dark',
      )}
    >
      {icon}
      {children}
    </button>
  )
}
