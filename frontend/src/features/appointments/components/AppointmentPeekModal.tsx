import { BellRing, CalendarX, Check, Pencil, Stethoscope, UserX } from 'lucide-react'

import { Alert, Badge, Button, Modal, type BadgeVariant } from '@/components/ui'
import { hueColor } from '@/lib/calendar'
import { formatDateTime, formatTime } from '@/lib/datetime'
import type { Appointment, AppointmentStatus } from '@/types'

const STATUS_VARIANT: Record<AppointmentStatus, BadgeVariant> = {
  PROGRAMADA: 'warning',
  CONFIRMADA: 'info',
  EN_ATENCION: 'primary',
  ATENDIDA: 'success',
  CANCELADA: 'danger',
  NO_ASISTIO: 'neutral',
}

interface AppointmentPeekModalProps {
  appointment: Appointment | null
  isBusy: boolean
  onClose: () => void
  onEdit: (appointment: Appointment) => void
  onConfirm: (appointment: Appointment) => void
  onNoShow: (appointment: Appointment) => void
  onCancel: (appointment: Appointment) => void
  onRemind: (appointment: Appointment) => void
}

export function AppointmentPeekModal({
  appointment,
  isBusy,
  onClose,
  onEdit,
  onConfirm,
  onNoShow,
  onCancel,
  onRemind,
}: AppointmentPeekModalProps) {
  if (!appointment) return null

  const end = new Date(
    new Date(appointment.scheduled_at).getTime() + appointment.duration_minutes * 60_000,
  ).toISOString()

  return (
    <Modal
      open
      onClose={onClose}
      title={appointment.patient_name}
      description={`${formatDateTime(appointment.scheduled_at)} – ${formatTime(end)}`}
      size="sm"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cerrar
          </Button>
          {!appointment.is_closed && (
            <Button
              size="sm"
              disabled={isBusy}
              leftIcon={<Pencil className="h-4 w-4" />}
              onClick={() => onEdit(appointment)}
            >
              Reprogramar
            </Button>
          )}
        </>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={STATUS_VARIANT[appointment.status]} dot>
            {appointment.status_label}
          </Badge>
          <span
            className="inline-flex items-center gap-1.5 text-xs text-muted"
            title="Color del profesional en la agenda"
          >
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: hueColor(appointment.practitioner_id) }}
            />
            {appointment.practitioner_name}
          </span>
        </div>

        {appointment.status === 'CANCELADA' && appointment.cancel_reason && (
          <Alert variant="danger">Cancelada: {appointment.cancel_reason}</Alert>
        )}

        <dl className="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
          <Detail label="Historia" value={appointment.patient.history_number} />
          <Detail
            label="Documento"
            value={
              appointment.patient.document_number
                ? `${appointment.patient.document_type} ${appointment.patient.document_number}`
                : null
            }
          />
          <Detail label="Teléfono" value={appointment.patient.phone} />
          <Detail label="Duración" value={`${appointment.duration_minutes} minutos`} />
          <Detail
            label="Especialidad"
            value={appointment.specialty_name ?? appointment.service_name}
          />
          <Detail label="Motivo" value={appointment.reason} />
        </dl>

        {appointment.notes && (
          <p className="rounded-xl bg-background/70 px-4 py-3 text-sm text-foreground">
            <span className="caption block uppercase tracking-wide">Notas</span>
            {appointment.notes}
          </p>
        )}

        {!appointment.is_closed && (
          <div className="flex flex-wrap gap-2 border-t border-border pt-4">
            {appointment.status === 'PROGRAMADA' && (
              <Button
                variant="outline"
                size="sm"
                disabled={isBusy}
                leftIcon={<Check className="h-4 w-4" />}
                onClick={() => onConfirm(appointment)}
              >
                Confirmar
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              disabled={isBusy}
              leftIcon={<BellRing className="h-4 w-4" />}
              onClick={() => onRemind(appointment)}
            >
              Recordatorio
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={isBusy}
              leftIcon={<UserX className="h-4 w-4" />}
              onClick={() => onNoShow(appointment)}
            >
              No asistió
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={isBusy}
              leftIcon={<CalendarX className="h-4 w-4" />}
              onClick={() => onCancel(appointment)}
            >
              Cancelar cita
            </Button>
          </div>
        )}

        {appointment.is_closed && (
          <p className="flex items-center gap-2 border-t border-border pt-4 text-xs text-muted">
            <Stethoscope className="h-3.5 w-3.5" />
            La cita ya está cerrada: {appointment.status_label.toLowerCase()}.
          </p>
        )}
      </div>
    </Modal>
  )
}

function Detail({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="min-w-0">
      <dt className="caption uppercase tracking-wide">{label}</dt>
      <dd className="truncate text-foreground">{value || '—'}</dd>
    </div>
  )
}
