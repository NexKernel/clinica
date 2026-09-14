import { useId, useState, type ReactNode } from 'react'
import { BarChart3, TableProperties } from 'lucide-react'

import { Card, CardBody, CardHeader } from '@/components/ui'
import { cn } from '@/lib/utils'

export interface ChartLegendItem {
  label: string
  /** Clase de fondo del punto de color (token de gráfico). */
  colorClass: string
  value?: string
}

export interface ChartTableData {
  headers: string[]
  rows: (string | number)[][]
}

interface ChartCardProps {
  title: string
  description?: string
  legend?: ChartLegendItem[]
  table: ChartTableData
  /** Altura del área de trazado, con espacio para el eje X. */
  height?: string
  className?: string
  children: ReactNode
}

/**
 * Contenedor de gráfico: leyenda propia con tokens de texto, alternativa en
 * tabla (misma información sin depender del color) y superficie de marca.
 */
export function ChartCard({
  title,
  description,
  legend,
  table,
  height = 'h-64',
  className,
  children,
}: ChartCardProps) {
  const [showTable, setShowTable] = useState(false)
  const regionId = useId()

  return (
    <Card className={className}>
      <CardHeader
        title={title}
        description={description}
        action={
          <button
            type="button"
            aria-pressed={showTable}
            aria-controls={regionId}
            onClick={() => setShowTable((value) => !value)}
            className="inline-flex items-center gap-1.5 rounded-xl px-2.5 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-primary/10 hover:text-primary-dark"
          >
            {showTable ? (
              <>
                <BarChart3 className="h-3.5 w-3.5" />
                Ver gráfico
              </>
            ) : (
              <>
                <TableProperties className="h-3.5 w-3.5" />
                Ver datos
              </>
            )}
          </button>
        }
      />

      <CardBody className="space-y-4">
        {legend && legend.length > 0 && (
          <ul className="flex flex-wrap items-center gap-x-5 gap-y-2">
            {legend.map((item) => (
              <li key={item.label} className="flex items-center gap-2 text-xs text-muted">
                <span className={cn('h-2.5 w-2.5 shrink-0 rounded-full', item.colorClass)} />
                <span className="font-medium text-foreground">{item.label}</span>
                {item.value && <span className="tabular-nums">{item.value}</span>}
              </li>
            ))}
          </ul>
        )}

        <div id={regionId}>
          {showTable ? (
            <div className="overflow-x-auto scrollbar-thin">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-border">
                    {table.headers.map((header, index) => (
                      <th
                        key={header}
                        scope="col"
                        className={cn(
                          'px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted',
                          index === 0 ? 'text-left' : 'text-right',
                        )}
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.rows.map((row) => (
                    <tr key={String(row[0])} className="border-b border-border/70 last:border-0">
                      {row.map((cell, index) => (
                        <td
                          key={`${String(row[0])}-${index}`}
                          className={cn(
                            'px-3 py-2.5',
                            index === 0
                              ? 'font-medium text-foreground'
                              : 'text-right tabular-nums text-muted',
                          )}
                        >
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className={cn('relative w-full', height)}>{children}</div>
          )}
        </div>
      </CardBody>
    </Card>
  )
}
