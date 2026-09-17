import { useState } from 'react'
import { CalendarPlus, Printer, Syringe, Trash2 } from 'lucide-react'

import { Alert, Badge, Button, EmptyState, LoadingState } from '@/components/ui'
import { CredEntryModal } from '@/features/cred/components/CredEntryModal'
import { CredSheetModal } from '@/features/cred/components/CredSheetModal'
import { useCredActions, useCredCard } from '@/features/cred/hooks/useCred'
import { useModuleAccess } from '@/hooks/useModuleAccess'
import { cn } from '@/lib/utils'
import { formatDate } from '@/lib/datetime'
import type { CredSlot, CredStatus } from '@/types'

/** Color de cada estado. El atraso es lo que hay que ver de un vistazo. */
const STATUS_STYLE: Record<CredStatus, { chip: string; badge: 'success' | 'warning' | 'danger' | 'neutral' }> = {
  APLICADA: { chip: 'border-emerald-300 bg-emerald-50 text-emerald-900', badge: 'success' },
  ATRASADA: { chip: 'border-rose-300 bg-rose-50 text-rose-900', badge: 'danger' },
  PENDIENTE: { chip: 'border-amber-300 bg-amber-50 text-amber-900', badge: 'warning' },
  FUTURA: { chip: 'border-border bg-background text-muted', badge: 'neutral' },
}

/** Agrupa las casillas por su rótulo, que es como se leen en el carné de papel. */
function byGroup(slots: CredSlot[]): [string, CredSlot[]][] {
  const grupos = new Map<string, CredSlot[]>()
  for (const slot of slots) {
    const actual = grupos.get(slot.group)
    if (actual) actual.push(slot)
    else grupos.set(slot.group, [slot])
  }
  return [...grupos.entries()]
}

interface CredCardPanelProps {
  patientId: number | null
}

export function CredCardPanel({ patientId }: CredCardPanelProps) {
  const { card, isLoading, error } = useCredCard(patientId)
  const { remove } = useCredActions(patientId)
  const { canManage } = useModuleAccess()
  const canWrite = canManage('CRED')

  const [registrando, setRegistrando] = useState(false)
  const [imprimiendo, setImprimiendo] = useState(false)
  const [abierta, setAbierta] = useState<string | null>(null)

  if (isLoading) return <LoadingState label="Cargando el carné" />
  if (error) return <Alert variant="danger">{error}</Alert>
  if (!card) return null

  const sinFecha = card.age_months === null

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="neutral">{card.age_label}</Badge>
          <Badge variant="success">{card.applied} aplicadas</Badge>
          {card.overdue > 0 && <Badge variant="danger">{card.overdue} atrasadas</Badge>}
          {card.pending > 0 && <Badge variant="warning">{card.pending} le tocan</Badge>}
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="ghost"
            leftIcon={<Printer className="h-4 w-4" />}
            onClick={() => setImprimiendo(true)}
          >
            Imprimir carné
          </Button>
          {canWrite && (
            <Button
              size="sm"
              leftIcon={<CalendarPlus className="h-4 w-4" />}
              onClick={() => setRegistrando(true)}
            >
              Registrar prestación
            </Button>
          )}
        </div>
      </div>

      {sinFecha && (
        <Alert variant="warning">
          La ficha no tiene fecha de nacimiento, así que no se puede saber qué prestación le
          toca ni cuál está vencida. Regístrela en el perfil del paciente.
        </Alert>
      )}
      {!sinFecha && !card.in_program && (
        <Alert variant="info">
          El paciente ya superó los diez años: el carné queda como constancia de lo aplicado.
        </Alert>
      )}

      {card.sections.map((section) => (
        <section key={section.kind} className="rounded-xl border border-border">
          <header className="flex items-center justify-between border-b border-border px-4 py-2.5">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Syringe className="h-4 w-4 text-muted" />
              {section.label}
            </h3>
            <span className="text-xs text-muted">
              {section.applied} de {section.slots.length}
              {section.overdue > 0 && ` · ${section.overdue} atrasadas`}
            </span>
          </header>

          <div className="space-y-3 p-4">
            {byGroup(section.slots).map(([grupo, slots]) => (
              <div key={grupo} className="grid gap-2 sm:grid-cols-[11rem_1fr] sm:items-start">
                <p className="pt-1 text-xs font-medium uppercase tracking-wide text-muted">
                  {grupo}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {slots.map((slot) => {
                    const estilo = STATUS_STYLE[slot.status]
                    const registro = slot.entries[0]
                    const abierto = abierta === slot.item_code
                    return (
                      <button
                        key={slot.item_code}
                        type="button"
                        onClick={() => setAbierta(abierto ? null : slot.item_code)}
                        title={`${slot.label} · ${slot.status_label}`}
                        className={cn(
                          'rounded-lg border px-2.5 py-1.5 text-left text-xs transition',
                          estilo.chip,
                          abierto && 'ring-2 ring-primary/40',
                        )}
                      >
                        <span className="block font-semibold">{slot.dose || slot.label}</span>
                        <span className="block text-[11px] opacity-80">
                          {registro ? formatDate(registro.performed_on) : slot.status_label}
                        </span>
                        {slot.entries.length > 1 && (
                          <span className="block text-[11px] opacity-70">
                            {slot.entries.length} entregas
                          </span>
                        )}
                      </button>
                    )
                  })}
                </div>

                {slots
                  .filter((slot) => abierta === slot.item_code && slot.entries.length > 0)
                  .map((slot) => (
                    <div
                      key={`${slot.item_code}-detalle`}
                      className="rounded-lg bg-background/60 p-3 text-xs sm:col-span-2"
                    >
                      <p className="mb-1.5 font-semibold text-foreground">{slot.label}</p>
                      <ul className="space-y-1">
                        {slot.entries.map((entry) => (
                          <li key={entry.id} className="flex items-center justify-between gap-3">
                            <span className="text-muted">
                              {formatDate(entry.performed_on)}
                              {entry.result && ` · ${entry.result}`}
                              {entry.practitioner_name && ` · ${entry.practitioner_name}`}
                              {entry.notes && ` · ${entry.notes}`}
                            </span>
                            {canWrite && (
                              <Button
                                size="sm"
                                variant="ghost"
                                leftIcon={<Trash2 className="h-3.5 w-3.5" />}
                                isLoading={remove.isPending}
                                onClick={() => remove.mutate(entry.id)}
                              >
                                Quitar
                              </Button>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
              </div>
            ))}

            {section.slots.length === 0 && (
              <EmptyState title="Sin prestaciones en esta sección" description="" />
            )}
          </div>
        </section>
      ))}

      {patientId !== null && (
        <CredEntryModal
          open={registrando}
          patientId={patientId}
          onClose={() => setRegistrando(false)}
        />
      )}
      <CredSheetModal
        open={imprimiendo}
        patientId={patientId}
        onClose={() => setImprimiendo(false)}
      />
    </div>
  )
}
