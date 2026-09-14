import { useEffect, useMemo, useState } from 'react'
import { CalendarPlus, ChevronLeft, ChevronRight } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'

import {
  Alert,
  Button,
  Card,
  ConfirmDialog,
  PageHeader,
  Select,
  type SelectOption,
} from '@/components/ui'
import { AppointmentFormModal } from '@/features/appointments/components/AppointmentFormModal'
import { AppointmentPeekModal } from '@/features/appointments/components/AppointmentPeekModal'
import { CalendarMonthGrid } from '@/features/appointments/components/CalendarMonthGrid'
import { CalendarTimeGrid } from '@/features/appointments/components/CalendarTimeGrid'
import {
  useAgendaRange,
  useAppointmentActions,
} from '@/features/appointments/hooks/useAppointments'
import { useActivePractitioners } from '@/features/catalog/hooks/useCatalog'
import { patientsApi } from '@/features/patients/api/patients.api'
import { useReminderActions } from '@/features/reminders/hooks/useReminders'
import {
  addDays,
  addMonths,
  hueColor,
  monthGrid,
  periodLabel,
  weekDays,
} from '@/lib/calendar'
import { formatTime, toDateInput } from '@/lib/datetime'
import { cn } from '@/lib/utils'
import { getErrorMessage } from '@/services/http'
import type { Appointment, AppointmentStatus, PatientSummary } from '@/types'

type CalendarView = 'day' | 'week' | 'month'

const VIEWS: { key: CalendarView; label: string }[] = [
  { key: 'day', label: 'Día' },
  { key: 'week', label: 'Semana' },
  { key: 'month', label: 'Mes' },
]

export function AppointmentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [view, setView] = useState<CalendarView>('week')
  const [day, setDay] = useState(() => toDateInput())
  const [practitionerFilter, setPractitionerFilter] = useState('')

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Appointment | null>(null)
  const [peeked, setPeeked] = useState<Appointment | null>(null)
  const [cancelTarget, setCancelTarget] = useState<Appointment | null>(null)
  const [initialPatient, setInitialPatient] = useState<PatientSummary | null>(null)
  const [initialTime, setInitialTime] = useState<string>()
  const [feedback, setFeedback] = useState<{ tone: 'success' | 'danger'; text: string } | null>(null)

  const { practitioners } = useActivePractitioners()
  const practitionerId = practitionerFilter ? Number(practitionerFilter) : undefined

  // Días que pinta la vista actual; el rango que se pide es el mismo.
  const days = useMemo(() => {
    if (view === 'day') return [day]
    return view === 'week' ? weekDays(day) : monthGrid(day)
  }, [view, day])

  const { appointments, isLoading, isFetching, error } = useAgendaRange(
    days[0] as string,
    days[days.length - 1] as string,
    practitionerId,
  )

  // Permite abrir la programación con el paciente ya elegido desde su ficha.
  useEffect(() => {
    const patientRef = searchParams.get('patient')
    if (!patientRef) return
    let cancelled = false
    patientsApi.get(patientRef).then((patient) => {
      if (cancelled) return
      setInitialPatient({
        id: patient.id,
        public_id: patient.public_id,
        history_number: patient.history_number,
        full_name: patient.full_name,
        document_type: patient.document_type,
        document_number: patient.document_number,
        age: patient.age,
        sex: patient.sex,
        phone: patient.phone,
        whatsapp: patient.whatsapp,
        has_alerts: patient.has_alerts,
      })
      setEditing(null)
      setInitialTime(undefined)
      setFormOpen(true)
      setSearchParams({}, { replace: true })
    })
    return () => {
      cancelled = true
    }
  }, [searchParams, setSearchParams])

  const { changeStatus } = useAppointmentActions()
  const { fromAppointment } = useReminderActions()

  // Resumen del período que se está viendo, calculado sobre lo ya cargado:
  // así siempre coincide con lo que hay en pantalla y no cuesta una consulta.
  const counters = useMemo(() => {
    const count = (predicate: (item: Appointment) => boolean) =>
      appointments.filter(predicate).length
    return [
      { key: 'total', label: 'citas', value: appointments.length, dot: 'bg-muted/40' },
      {
        key: 'pending',
        label: 'por atender',
        value: count((item) => item.status === 'PROGRAMADA' || item.status === 'CONFIRMADA'),
        dot: 'bg-warning',
      },
      {
        key: 'attended',
        label: 'atendidas',
        value: count((item) => item.status === 'ATENDIDA'),
        dot: 'bg-success',
      },
      {
        key: 'lost',
        label: 'canceladas o sin asistencia',
        value: count((item) => item.status === 'CANCELADA' || item.status === 'NO_ASISTIO'),
        dot: 'bg-danger',
      },
    ]
  }, [appointments])

  const practitionerOptions: SelectOption[] = practitioners.map((item) => ({
    value: String(item.id),
    label: item.full_name,
  }))

  const step = (direction: -1 | 1) => {
    if (view === 'month') return setDay(addMonths(day, direction))
    setDay(addDays(day, direction * (view === 'week' ? 7 : 1)))
  }

  const openCreate = (atDay = day, atTime?: string) => {
    setEditing(null)
    setInitialPatient(null)
    setInitialTime(atTime)
    setDay(atDay)
    setFeedback(null)
    setFormOpen(true)
  }

  const openEdit = (appointment: Appointment) => {
    setPeeked(null)
    setEditing(appointment)
    setInitialPatient(null)
    setInitialTime(undefined)
    setFeedback(null)
    setFormOpen(true)
  }

  const applyStatus = async (appointment: Appointment, status: AppointmentStatus) => {
    setFeedback(null)
    try {
      await changeStatus.mutateAsync({ id: appointment.id, status })
      setPeeked(null)
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo cambiar el estado') })
    }
  }

  const confirmCancel = async (reason: string) => {
    if (!cancelTarget) return
    try {
      await changeStatus.mutateAsync({
        id: cancelTarget.id,
        status: 'CANCELADA',
        cancelReason: reason,
      })
      setCancelTarget(null)
      setPeeked(null)
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo cancelar la cita') })
    }
  }

  const scheduleReminder = async (appointment: Appointment) => {
    setFeedback(null)
    try {
      await fromAppointment.mutateAsync({
        appointmentId: appointment.id,
        hoursBefore: 24,
        channel: 'WHATSAPP',
      })
      setPeeked(null)
      setFeedback({
        tone: 'success',
        text: `Recordatorio programado para ${appointment.patient_name}, 24 horas antes de la cita.`,
      })
    } catch (err) {
      setFeedback({
        tone: 'danger',
        text: getErrorMessage(err, 'No se pudo programar el recordatorio'),
      })
    }
  }

  // Solo los profesionales con cita en el período: la leyenda explica los
  // colores que se están viendo, no el catálogo completo.
  const legend = useMemo(() => {
    const seen = new Map<number, string>()
    for (const appointment of appointments) {
      if (!seen.has(appointment.practitioner_id)) {
        seen.set(appointment.practitioner_id, appointment.practitioner_name)
      }
    }
    return [...seen.entries()]
  }, [appointments])

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Atención"
        title="Agenda de citas"
        subtitle="Vista de calendario por día, semana o mes"
        actions={
          <Button size="sm" leftIcon={<CalendarPlus className="h-4 w-4" />} onClick={() => openCreate()}>
            Nueva cita
          </Button>
        }
      />

      {feedback && <Alert variant={feedback.tone}>{feedback.text}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}

      <Card>
        <div className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-3">
          <div className="flex items-center gap-1">
            <Button variant="outline" size="sm" onClick={() => setDay(toDateInput())}>
              Hoy
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Período anterior"
              onClick={() => step(-1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Período siguiente"
              onClick={() => step(1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          <h2 className="flex-1 truncate text-base font-semibold text-foreground">
            {periodLabel(view, day)}
          </h2>

          <Select
            options={practitionerOptions}
            placeholder="Todos los profesionales"
            value={practitionerFilter}
            containerClassName="w-full sm:w-56"
            onChange={(event) => setPractitionerFilter(event.target.value)}
          />

          <div
            role="group"
            aria-label="Vista del calendario"
            className="flex rounded-xl border border-border p-0.5"
          >
            {VIEWS.map((item) => (
              <button
                key={item.key}
                type="button"
                aria-pressed={view === item.key}
                onClick={() => setView(item.key)}
                className={cn(
                  'rounded-[10px] px-3 py-1.5 text-sm font-medium transition-colors',
                  view === item.key
                    ? 'bg-primary text-white'
                    : 'text-muted hover:bg-primary/10 hover:text-primary-dark',
                )}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-1.5 border-b border-border px-4 py-2">
          {counters.map((counter) => (
            <span key={counter.key} className="flex items-baseline gap-1.5 text-sm">
              <span
                className={cn('mb-px inline-block h-2 w-2 self-center rounded-full', counter.dot)}
              />
              <span className="font-semibold tabular-nums text-foreground">{counter.value}</span>
              <span className="text-muted">{counter.label}</span>
            </span>
          ))}
        </div>

        <div className={cn(isFetching && !isLoading && 'opacity-60 transition-opacity')}>
          {view === 'month' ? (
            <CalendarMonthGrid
              days={days}
              reference={day}
              appointments={appointments}
              onSelectDay={(selected) => {
                setDay(selected)
                setView('day')
              }}
              onSelectAppointment={setPeeked}
            />
          ) : (
            <CalendarTimeGrid
              days={days}
              appointments={appointments}
              onSelectSlot={(selectedDay, time) => openCreate(selectedDay, time)}
              onSelectAppointment={setPeeked}
            />
          )}
        </div>

        {legend.length > 0 && (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-border px-4 py-2.5">
            {legend.map(([id, name]) => (
              <span key={id} className="flex items-center gap-1.5 text-xs text-muted">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: hueColor(id) }}
                />
                {name}
              </span>
            ))}
          </div>
        )}
      </Card>

      <AppointmentPeekModal
        appointment={peeked}
        isBusy={changeStatus.isPending || fromAppointment.isPending}
        onClose={() => setPeeked(null)}
        onEdit={openEdit}
        onConfirm={(appointment) => void applyStatus(appointment, 'CONFIRMADA')}
        onNoShow={(appointment) => void applyStatus(appointment, 'NO_ASISTIO')}
        onCancel={(appointment) => {
          setPeeked(null)
          setCancelTarget(appointment)
        }}
        onRemind={(appointment) => void scheduleReminder(appointment)}
      />

      <AppointmentFormModal
        open={formOpen}
        appointment={editing}
        initialPatient={initialPatient}
        initialDay={day}
        initialTime={initialTime}
        onClose={() => setFormOpen(false)}
      />

      <ConfirmDialog
        open={cancelTarget !== null}
        title="Cancelar cita"
        description={
          cancelTarget
            ? `${cancelTarget.patient_name} · ${formatTime(cancelTarget.scheduled_at)}`
            : undefined
        }
        reasonLabel="Motivo de la cancelación"
        confirmLabel="Cancelar cita"
        variant="danger"
        isLoading={changeStatus.isPending}
        onClose={() => setCancelTarget(null)}
        onConfirm={confirmCancel}
      />
    </div>
  )
}
