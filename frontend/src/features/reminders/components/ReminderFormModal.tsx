import { useEffect, useState, type FormEvent } from 'react'
import { Save } from 'lucide-react'

import { Alert, Button, Input, Modal, Select, Textarea, type SelectOption } from '@/components/ui'
import { PatientPicker } from '@/features/patients/components/PatientPicker'
import { useReminderActions } from '@/features/reminders/hooks/useReminders'
import { fromDateTimeInput, toDateTimeInput } from '@/lib/datetime'
import { getErrorMessage } from '@/services/http'
import {
  REMINDER_CHANNEL_LABELS,
  REMINDER_CHANNELS,
  REMINDER_KIND_LABELS,
  REMINDER_KINDS,
  type PatientSummary,
  type Reminder,
  type ReminderChannel,
  type ReminderKind,
} from '@/types'

const KIND_OPTIONS: SelectOption[] = REMINDER_KINDS.map((kind) => ({
  value: kind,
  label: REMINDER_KIND_LABELS[kind],
}))

const CHANNEL_OPTIONS: SelectOption[] = REMINDER_CHANNELS.map((channel) => ({
  value: channel,
  label: REMINDER_CHANNEL_LABELS[channel],
}))

interface ReminderFormModalProps {
  open: boolean
  reminder: Reminder | null
  onClose: () => void
}

export function ReminderFormModal({ open, reminder, onClose }: ReminderFormModalProps) {
  const isEdit = reminder !== null
  const { create, update } = useReminderActions()
  const isLoading = create.isPending || update.isPending

  const [patient, setPatient] = useState<PatientSummary | null>(null)
  const [kind, setKind] = useState<ReminderKind>('CONTROL')
  const [channel, setChannel] = useState<ReminderChannel>('WHATSAPP')
  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const [scheduledFor, setScheduledFor] = useState('')
  const [notes, setNotes] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setFormError(null)

    if (reminder) {
      setPatient({
        id: reminder.patient_id,
        // El recordatorio no expone el public_id del paciente; al editar el
        // picker esta deshabilitado y solo se usan id y nombre.
        public_id: '',
        history_number: '',
        full_name: reminder.patient_name,
        document_type: '',
        document_number: null,
        age: null,
        sex: null,
        phone: reminder.patient_phone,
        whatsapp: reminder.patient_phone,
        has_alerts: false,
      })
      setKind(reminder.kind)
      setChannel(reminder.channel)
      setTitle(reminder.title)
      setMessage(reminder.message)
      setScheduledFor(toDateTimeInput(reminder.scheduled_for))
      setNotes(reminder.notes ?? '')
      return
    }

    setPatient(null)
    setKind('CONTROL')
    setChannel('WHATSAPP')
    setTitle('')
    setMessage('')
    setScheduledFor(toDateTimeInput())
    setNotes('')
  }, [open, reminder])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    if (!patient) return setFormError('Seleccione el paciente')
    if (title.trim().length < 3) return setFormError('Indique un título para el recordatorio')
    if (message.trim().length < 3) return setFormError('Escriba el mensaje que recibirá el paciente')
    if (!scheduledFor) return setFormError('Indique la fecha y hora del aviso')

    const payload = {
      patient_id: patient.id,
      kind,
      channel,
      title: title.trim(),
      message: message.trim(),
      scheduled_for: fromDateTimeInput(scheduledFor),
      appointment_id: reminder?.appointment_id ?? null,
      encounter_id: reminder?.encounter_id ?? null,
      prescription_id: reminder?.prescription_id ?? null,
      notes: notes.trim() || null,
    }

    try {
      if (reminder) {
        await update.mutateAsync({ id: reminder.id, payload })
      } else {
        await create.mutateAsync(payload)
      }
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo guardar el recordatorio'))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Editar recordatorio' : 'Nuevo recordatorio'}
      description="El sistema programa el aviso; el envío se realiza desde el canal elegido"
      size="md"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="reminder-form"
            size="sm"
            isLoading={isLoading}
            leftIcon={<Save className="h-4 w-4" />}
          >
            {isEdit ? 'Guardar cambios' : 'Programar recordatorio'}
          </Button>
        </>
      }
    >
      <form id="reminder-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        <PatientPicker value={patient} onChange={setPatient} disabled={isLoading || isEdit} />

        <div className="grid gap-4 sm:grid-cols-2">
          <Select
            label="Tipo"
            options={KIND_OPTIONS}
            value={kind}
            disabled={isLoading}
            onChange={(event) => setKind(event.target.value as ReminderKind)}
          />
          <Select
            label="Canal"
            options={CHANNEL_OPTIONS}
            value={channel}
            disabled={isLoading}
            onChange={(event) => setChannel(event.target.value as ReminderChannel)}
          />
        </div>

        <Input
          label="Título"
          placeholder="Control de presión arterial"
          value={title}
          disabled={isLoading}
          onChange={(event) => setTitle(event.target.value)}
        />

        <Textarea
          label="Mensaje al paciente"
          rows={4}
          value={message}
          disabled={isLoading}
          onChange={(event) => setMessage(event.target.value)}
        />

        <Input
          label="Fecha y hora del aviso"
          type="datetime-local"
          value={scheduledFor}
          disabled={isLoading}
          onChange={(event) => setScheduledFor(event.target.value)}
        />

        <Input
          label="Notas internas"
          value={notes}
          disabled={isLoading}
          onChange={(event) => setNotes(event.target.value)}
        />
      </form>
    </Modal>
  )
}
