import { ChevronLeft, ChevronRight } from 'lucide-react'

import { Button } from '@/components/ui/Button'

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  /** Sustantivo del recurso, en singular y plural: ["cita", "citas"]. */
  labels: [string, string]
  onChange: (page: number) => void
}

export function Pagination({ page, pageSize, total, labels, onChange }: PaginationProps) {
  if (total === 0) return null

  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const [singular, plural] = labels

  return (
    <div className="flex flex-col items-center justify-between gap-3 border-t border-border px-5 py-3.5 sm:flex-row">
      <p className="text-xs text-muted">
        {total} {total === 1 ? singular : plural} · página {page} de {totalPages}
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          leftIcon={<ChevronLeft className="h-4 w-4" />}
          onClick={() => onChange(Math.max(1, page - 1))}
        >
          Anterior
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          rightIcon={<ChevronRight className="h-4 w-4" />}
          onClick={() => onChange(Math.min(totalPages, page + 1))}
        >
          Siguiente
        </Button>
      </div>
    </div>
  )
}
