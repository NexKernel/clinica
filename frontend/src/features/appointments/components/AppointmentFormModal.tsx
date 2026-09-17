import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { CalendarClock, Save } from 'lucide-react'

import {
  Alert,
  Button,
  Input,
  LoadingState,
  Modal,
  Select,
  Textarea,
  type SelectOption,
} from '@/components/ui'
import {
  useAppointmentActions,
  useAvailability,
} from '@/features/appointments/hooks/useAppointments'
import { ServicePicker } from '@/features/catalog/components/ServicePicker'
import { useActivePractitioners, useActiveServices } from '@/features/catalog/hooks/useCatalog'
import { PatientPicker } from '@/features/patients/components/PatientPicker'
import { useOwnPractitionerId } from '@/hooks/useOwnPractitioner'
import { formatTime, fromDateTimeInput, toDateInput, toDateTimeInput } from '@/lib/datetime'
import { cn } from '@/lib/utils'
import { getErrorMessage } from '@/services/http'
import type {
  Appointment,
  AppointmentPayload,
  MedicalService,
  PatientSummary,
} from '@/types'

interface AppointmentFormModalProps {
  open: boolean
  appointment: Appointment | null
  /** Paciente preseleccionado al llegar desde otro módulo. */
  initialPatient?: PatientSummary | null
  initialDay?: string
  /** Hora preseleccionada al abrir desde un hueco del calendario. */
  initialTime?: string
  onClose: () => void
}

export function AppointmentFormModal({
  open,
  appointment,
  initialPatient = null,
  initialDay,
  initialTime,
  onClose,
}: AppointmentFormModalProps) {
  const isEdit = appointment !== null
  const { practitioners } = useActivePractitioners()
  const ownPractitionerId = useOwnPractitionerId(practitioners)
  const { services } = useActiveServices()
  const { create, update } = useAppointmentActions()
  const isLoading = create.isPending || update.isPending

  const [patient, setPatient] = useState<PatientSummary | null>(null)
  const [practitionerId, setPractitionerId] = useState('')
  const [serviceId, setServiceId] = useState('')
  const [service, setService] = useState<MedicalService | null>(null)
  const [day, setDay] = useState(() => initialDay ?? toDateInput())
  const [time, setTime] = useState('')
  const [reason, setReason] = useState('')
  const [notes, setNotes] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  const { availability, isLoading: loadingSlots } = useAvailability(
    practitionerId ? Number(practitionerId) : null,
    day,
  )

  useEffect(() => {
    if (!open) return
    setFormError(null)

    if (appointment) {
      const local = toDateTimeInput(appointment.scheduled_at)
      setPatient(appointment.patient)
      setPractitionerId(String(appointment.practitioner_id))
      setServiceId(appointment.service_id ? String(appointment.service_id) : '')
      setDay(local.slice(0, 10))
      setTime(local.slice(11, 16))
      setReason(appointment.reason ?? '')
      setNotes(appointment.notes ?? '')
      return
    }

    setPatient(initialPatient)
    setPractitionerId('')
    setServiceId('')
    setDay(initialDay ?? toDateInput())
    setTime(initialTime ?? '')
    setReason('')
    setNotes('')
  }, [open, appointment, initialPatient, initialDay, initialTime])

  /* Ver la nota de EncounterFormModal: el relleno de la ficha propia va en un
     efecto aparte del que reinicia el formulario, y solo sobre un campo vacío.
     Aquí el profesional sigue eligiéndose —recepción programa para toda la
     clínica, y un médico puede citar con un colega—, pero quien atiende ya no
     tiene que buscarse a sí mismo para programar su propia agenda. */
  useEffect(() => {
    if (!open || appointment || !ownPractitionerId) return
    setPractitionerId((actual) => actual || String(ownPractitionerId))
  }, [open, appointment, ownPractitionerId])

  const practitionerOptions: SelectOption[] = useMemo(
    () =>
      practitioners.map((item) => ({
        value: String(item.id),
        label: item.specialty_name ? `${item.full_name} — ${item.specialty_name}` : item.full_name,
      })),
    [practitioners],
  )

  // Al reprogramar, de la cita solo llega el id del servicio: se resuelve
  // contra el tarifario vigente apenas la lista está disponible. Lo que el
  // usuario elige en el buscador ya viene completo y no vuelve a resolverse.
  useEffect(() => {
    if (!serviceId) {
      setService(null)
      return
    }
    if (service && String(service.id) === serviceId) return
    setService(services.find((item) => String(item.id) === serviceId) ?? null)
  }, [serviceId, service, services])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    if (!patient) return setFormError('Seleccione el paciente')
    if (!practitionerId) return setFormError('Seleccione el profesional')
    if (!day || !time) return setFormError('Indique la fecha y hora de la cita')

    const payload: AppointmentPayload = {
      patient_id: patient.id,
      practitioner_id: Number(practitionerId),
      service_id: serviceId ? Number(serviceId) : null,
      scheduled_at: fromDateTimeInput(`${day}T${time}`),
      duration_minutes: null,
      reason: reason.trim() || null,
      notes: notes.trim() || null,
    }

    try {
      if (appointment) {
        await update.mutateAsync({ id: appointment.id, payload })
      } else {
        await create.mutateAsync(payload)
      }
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo guardar la cita'))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Reprogramar cita' : 'Nueva cita'}
      description={
        isEdit
          ? 'Modifique la fecha, el profesional o el motivo de la cita'
          : 'Programe la atención del paciente según la disponibilidad del profesional'
      }
      size="lg"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="appointment-form"
            size="sm"
            isLoading={isLoading}
            leftIcon={<Save className="h-4 w-4" />}
          >
            {isEdit ? 'Guardar cambios' : 'Programar cita'}
          </Button>
        </>
      }
    >
      <form id="appointment-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        <PatientPicker value={patient} onChange={setPatient} disabled={isLoading} />

        <div className="grid gap-4 sm:grid-cols-2">
          <Select
            label="Profesional"
            options={practitionerOptions}
            placeholder="Seleccione el profesional"
            value={practitionerId}
            disabled={isLoading}
            onChange={(event) => setPractitionerId(event.target.value)}
          />
          <ServicePicker
            label="Servicio"
            placeholder="Busque el servicio (opcional)"
            value={service}
            disabled={isLoading}
            onChange={(item) => {
              setService(item)
              setServiceId(item ? String(item.id) : '')
            }}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Fecha"
            type="date"
            value={day}
            disabled={isLoading}
            onChange={(event) => setDay(event.target.value)}
          />
          <Input
            label="Hora"
            type="time"
            value={time}
            disabled={isLoading}
            onChange={(event) => setTime(event.target.value)}
          />
        </div>

        {practitionerId && (
          <div className="rounded-xl border border-border bg-background/60 p-3">
            <p className="caption mb-2 flex items-center gap-1.5 uppercase tracking-wide">
              <CalendarClock className="h-3.5 w-3.5" />
              Disponibilidad del día
            </p>

            {loadingSlots ? (
              <LoadingState label="Consultando agenda" />
            ) : !availability?.working ? (
              <p className="text-sm text-muted">
                El profesional no tiene horario configurado para esta fecha. Puede indicar la hora
                manualmente.
              </p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {availability.slots.map((slot) => {
                  const value = slot.start.slice(11, 16)
                  const isSelected = value === time
                  return (
                    <button
                      key={slot.start}
                      type="button"
                      disabled={!slot.available || isLoading}
                      title={slot.available ? undefined : (slot.patient_name ?? 'Ocupado')}
                      onClick={() => setTime(value)}
                      className={cn(
                        'rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors',
                        isSelected && 'bg-primary text-white',
                        !isSelected && slot.available && 'bg-surface text-foreground hover:bg-primary/10',
                        !slot.available && 'cursor-not-allowed bg-danger/10 text-danger',
                      )}
                    >
                      {formatTime(slot.start)}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )}

        <Input
          label="Motivo"
          placeholder="Control de presión, dolor abdominal…"
          value={reason}
          disabled={isLoading}
          onChange={(event) => setReason(event.target.value)}
        />

        <Textarea
          label="Observaciones"
          value={notes}
          disabled={isLoading}
          onChange={(event) => setNotes(event.target.value)}
        />
      </form>
    </Modal>
  )
}
