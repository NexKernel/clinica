import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { createPortal } from 'react-dom'
import { Check, Search, X } from 'lucide-react'

import { Input, Spinner } from '@/components/ui'
import { getErrorMessage } from '@/services/http'
import { cn } from '@/lib/utils'

const MENU_OFFSET = 4
const MENU_MAX_HEIGHT = 256

interface MenuPosition {
  top: number
  left: number
  width: number
  /** El desplegable se abre hacia arriba cuando no cabe debajo del campo. */
  flipped: boolean
}

interface EntityPickerProps<T> {
  label?: string
  placeholder?: string
  value: T | null
  onChange: (item: T | null) => void
  /** Consulta al servidor; se invoca con el término ya normalizado. */
  search: (term: string) => Promise<T[]>
  getKey: (item: T) => number
  getLabel: (item: T) => string
  renderItem?: (item: T) => ReactNode
  minLength?: number
  disabled?: boolean
  error?: string | null
  hint?: string
  emptyLabel?: string
  containerClassName?: string
}

/**
 * Selector con búsqueda incremental contra la API (pacientes, productos).
 *
 * La lista de resultados se dibuja en un portal con posición fija: así no la
 * recorta el contenedor con scroll de los modales donde se usa.
 */
export function EntityPicker<T>({
  label,
  placeholder = 'Escriba para buscar',
  value,
  onChange,
  search,
  getKey,
  getLabel,
  renderItem,
  minLength = 2,
  disabled = false,
  error,
  hint,
  emptyLabel = 'Sin resultados',
  containerClassName,
}: EntityPickerProps<T>) {
  const [term, setTerm] = useState('')
  const [results, setResults] = useState<T[]>([])
  const [open, setOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [position, setPosition] = useState<MenuPosition | null>(null)

  const fieldRef = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  const showMenu = open && term.trim().length >= minLength

  const updatePosition = useCallback(() => {
    const rect = fieldRef.current?.getBoundingClientRect()
    if (!rect) return
    const spaceBelow = window.innerHeight - rect.bottom
    const flipped = spaceBelow < MENU_MAX_HEIGHT && rect.top > spaceBelow
    setPosition({
      top: flipped ? rect.top - MENU_OFFSET : rect.bottom + MENU_OFFSET,
      left: rect.left,
      width: rect.width,
      flipped,
    })
  }, [])

  useLayoutEffect(() => {
    if (!showMenu) return
    updatePosition()
    window.addEventListener('resize', updatePosition)
    // El tercer argumento captura también el scroll del cuerpo del modal.
    window.addEventListener('scroll', updatePosition, true)
    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [showMenu, updatePosition])

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node
      if (fieldRef.current?.contains(target) || menuRef.current?.contains(target)) return
      setOpen(false)
    }
    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [])

  useEffect(() => {
    const cleaned = term.trim()
    if (cleaned.length < minLength) {
      setResults([])
      setSearchError(null)
      return
    }

    let cancelled = false
    setIsLoading(true)
    const timer = setTimeout(() => {
      search(cleaned)
        .then((items) => {
          if (cancelled) return
          setResults(items)
          setSearchError(null)
        })
        .catch((err) => {
          if (!cancelled) setSearchError(getErrorMessage(err, 'No se pudo buscar'))
        })
        .finally(() => {
          if (!cancelled) setIsLoading(false)
        })
    }, 320)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [term, minLength, search])

  const select = (item: T) => {
    onChange(item)
    setTerm('')
    setResults([])
    setOpen(false)
  }

  if (value) {
    return (
      <div className={cn('w-full space-y-1.5', containerClassName)}>
        {label && <span className="block text-sm font-medium text-foreground">{label}</span>}
        <div className="flex items-center gap-2 rounded-xl border border-primary/40 bg-primary/5 px-4 py-3">
          <Check className="h-4 w-4 shrink-0 text-primary-dark" />
          <div className="min-w-0 flex-1 text-sm text-foreground">
            {renderItem ? renderItem(value) : getLabel(value)}
          </div>
          {!disabled && (
            <button
              type="button"
              aria-label="Quitar selección"
              onClick={() => onChange(null)}
              className="rounded-lg p-1 text-muted transition-colors hover:bg-primary/10 hover:text-primary-dark"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        {error && <p className="text-xs font-medium text-danger">{error}</p>}
      </div>
    )
  }

  return (
    <div ref={fieldRef} className={cn('w-full', containerClassName)}>
      <Input
        label={label}
        placeholder={placeholder}
        icon={<Search className="h-[18px] w-[18px]" />}
        trailing={isLoading ? <Spinner /> : undefined}
        value={term}
        disabled={disabled}
        error={error ?? searchError}
        hint={hint}
        autoComplete="off"
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          setTerm(event.target.value)
          setOpen(true)
        }}
      />

      {showMenu &&
        !isLoading &&
        position &&
        createPortal(
          <div
            ref={menuRef}
            role="listbox"
            style={{
              top: position.top,
              left: position.left,
              width: position.width,
              maxHeight: MENU_MAX_HEIGHT,
              transform: position.flipped ? 'translateY(-100%)' : undefined,
            }}
            className="scrollbar-thin fixed z-[60] overflow-y-auto overscroll-contain rounded-xl border border-border bg-surface py-1 shadow-popover animate-fade-in"
          >
            {results.length === 0 ? (
              <p className="px-4 py-3 text-sm text-muted">{emptyLabel}</p>
            ) : (
              results.map((item) => (
                <button
                  key={getKey(item)}
                  type="button"
                  role="option"
                  onClick={() => select(item)}
                  className="block w-full px-4 py-2.5 text-left text-sm text-foreground transition-colors hover:bg-primary/10"
                >
                  {renderItem ? renderItem(item) : getLabel(item)}
                </button>
              ))
            )}
          </div>,
          document.body,
        )}
    </div>
  )
}
