import { CalendarClock, Stethoscope } from 'lucide-react'

import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Table,
  type BadgeVariant,
  type Column,
} from '@/components/ui'
import { useAgenda } from '@/features/appointments/hooks/useAppointments'
import { periodLabel } from '@/lib/calendar'
import { formatTime } from '@/lib/datetime'
import { cn } from '@/lib/utils'
import type { Appointment, AppointmentStatus } from '@/types'

const STATUS_VARIANT: Record<AppointmentStatus, BadgeVariant> = {
  PROGRAMADA: 'warning',
  CONFIRMADA: 'info',
  EN_ATENCION: 'primary',
  ATENDIDA: 'success',
  CANCELADA: 'danger',
  NO_ASISTIO: 'neutral',
}

/** Citas que todavía esperan al profesional; el resto ya está resuelto. */
const isPending = (appointment: Appointment): boolean =>
  appointment.status === 'PROGRAMADA' || appointment.status === 'CONFIRMADA'

interface PractitionerAgendaCardProps {
  practitionerId: number
  day: string
  /** Solo quien registra la historia puede abrir la atención desde la cita. */
  canWrite: boolean
  onStart: (appointment: Appointment) => void
}

/**
 * Agenda propia del profesional dentro del módulo de atenciones.
 *
 * El médico entra a atender, no a buscar: sus citas del día se le muestran
 * donde va a trabajar, y cada una abre la atención con el paciente y la cita
 * ya enlazados, de modo que al finalizarla la cita quede como atendida.
 */
export function PractitionerAgendaCard({
  practitionerId,
  day,
  canWrite,
  onStart,
}: PractitionerAgendaCardProps) {
  const { appointments, isLoading, isFetching, error } = useAgenda(day, practitionerId)

  const pending = appointments.filter(isPending).length

  const columns: Column<Appointment>[] = [
    {
      key: 'time',
      header: 'Hora',
      className: 'w-20 font-semibold text-foreground',
      render: (row) => formatTime(row.scheduled_at),
    },
    {
      key: 'patient',
      header: 'Paciente',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.patient_name}</p>
          <p className="truncate text-xs text-muted">{row.reason ?? 'Sin motivo registrado'}</p>
        </div>
      ),
    },
    {
      key: 'service',
      header: 'Servicio',
      className: 'text-muted',
      render: (row) => row.service_name ?? row.specialty_name ?? '—',
    },
    {
      key: 'status',
      header: 'Estado',
      className: 'w-32',
      render: (row) => (
        <Badge variant={STATUS_VARIANT[row.status]} dot>
          {row.status_label}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'w-40 text-right',
      render: (row) =>
        canWrite && isPending(row) ? (
          <Button
            size="sm"
            variant="outline"
            leftIcon={<Stethoscope className="h-4 w-4" />}
            onClick={() => onStart(row)}
          >
            Atender
          </Button>
        ) : null,
    },
  ]

  return (
    <Card>
      <CardHeader
        title="Mis citas del día"
        description={periodLabel('day', day)}
        action={
          <Badge variant={pending > 0 ? 'warning' : 'success'} dot>
            {pending > 0 ? `${pending} por atender` : 'Sin pendientes'}
          </Badge>
        }
      />

      {error && (
        <div className="px-5 pt-4">
          <Alert variant="danger">{error}</Alert>
        </div>
      )}

      <Table
        columns={columns}
        data={appointments}
        keyExtractor={(row) => row.id}
        isLoading={isLoading}
        className={cn(isFetching && !isLoading && 'opacity-60 transition-opacity')}
        emptyState={
          <EmptyState
            icon={CalendarClock}
            title="Sin citas para esta fecha"
            description="No tiene citas programadas en su agenda para el día seleccionado."
          />
        }
      />
    </Card>
  )
}
