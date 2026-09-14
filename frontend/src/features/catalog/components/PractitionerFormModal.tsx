import { useEffect, useState, type FormEvent } from 'react'
import { Plus, Save, Trash2 } from 'lucide-react'

import {
  Alert,
  Button,
  Input,
  Modal,
  Select,
  Switch,
  type SelectOption,
} from '@/components/ui'
import { useCatalogActions, useSpecialties } from '@/features/catalog/hooks/useCatalog'
import { getErrorMessage } from '@/services/http'
import { WEEKDAYS, type Practitioner, type SchedulePayload } from '@/types'

const WEEKDAY_OPTIONS: SelectOption[] = WEEKDAYS.map((label, index) => ({
  value: String(index),
  label,
}))

const emptyBlock = (): SchedulePayload => ({
  weekday: 0,
  start_time: '08:00',
  end_time: '13:00',
  is_active: true,
})

/** El backend devuelve "08:00:00"; los inputs usan "08:00". */
const toTimeInput = (value: string): string => value.slice(0, 5)

interface PractitionerFormModalProps {
  open: boolean
  practitioner: Practitioner | null
  onClose: () => void
}

export function PractitionerFormModal({
  open,
  practitioner,
  onClose,
}: PractitionerFormModalProps) {
  const isEdit = practitioner !== null
  const { specialties } = useSpecialties()
  const { createPractitioner, updatePractitioner } = useCatalogActions()
  const isLoading = createPractitioner.isPending || updatePractitioner.isPending

  const [fullName, setFullName] = useState('')
  const [specialtyId, setSpecialtyId] = useState('')
  const [license, setLicense] = useState('')
  const [document, setDocument] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [slotMinutes, setSlotMinutes] = useState('20')
  const [isActive, setIsActive] = useState(true)
  const [schedules, setSchedules] = useState<SchedulePayload[]>([])
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setFormError(null)

    if (practitioner) {
      setFullName(practitioner.full_name)
      setSpecialtyId(practitioner.specialty_id ? String(practitioner.specialty_id) : '')
      setLicense(practitioner.license_number ?? '')
      setDocument(practitioner.document_number ?? '')
      setPhone(practitioner.phone ?? '')
      setEmail(practitioner.email ?? '')
      setSlotMinutes(String(practitioner.slot_minutes))
      setIsActive(practitioner.is_active)
      setSchedules(
        practitioner.schedules.map((block) => ({
          weekday: block.weekday,
          start_time: toTimeInput(block.start_time),
          end_time: toTimeInput(block.end_time),
          is_active: block.is_active,
        })),
      )
      return
    }

    setFullName('')
    setSpecialtyId('')
    setLicense('')
    setDocument('')
    setPhone('')
    setEmail('')
    setSlotMinutes('20')
    setIsActive(true)
    setSchedules([emptyBlock()])
  }, [open, practitioner])

  const updateBlock = (index: number, patch: Partial<SchedulePayload>) =>
    setSchedules((prev) => prev.map((block, i) => (i === index ? { ...block, ...patch } : block)))

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    if (fullName.trim().length < 5) return setFormError('Ingrese el nombre completo')
    if (schedules.some((block) => block.start_time >= block.end_time)) {
      return setFormError('La hora de inicio debe ser anterior a la hora de fin')
    }

    const clean = (value: string) => (value.trim() === '' ? null : value.trim())

    const payload = {
      full_name: fullName.trim(),
      specialty_id: specialtyId ? Number(specialtyId) : null,
      user_id: practitioner?.user_id ?? null,
      license_number: clean(license),
      document_number: clean(document),
      phone: clean(phone),
      email: clean(email),
      slot_minutes: Number(slotMinutes) || 20,
      is_active: isActive,
      schedules: schedules.map((block) => ({
        ...block,
        start_time: `${block.start_time}:00`,
        end_time: `${block.end_time}:00`,
      })),
    }

    try {
      if (practitioner) {
        await updatePractitioner.mutateAsync({ id: practitioner.id, payload })
      } else {
        await createPractitioner.mutateAsync(payload)
      }
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo guardar el profesional'))
    }
  }

  const specialtyOptions: SelectOption[] = specialties.map((item) => ({
    value: String(item.id),
    label: item.name,
  }))

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Editar profesional' : 'Nuevo profesional'}
      description="Los bloques horarios definen la disponibilidad en la agenda de citas"
      size="lg"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="practitioner-form"
            size="sm"
            isLoading={isLoading}
            leftIcon={<Save className="h-4 w-4" />}
          >
            {isEdit ? 'Guardar cambios' : 'Registrar profesional'}
          </Button>
        </>
      }
    >
      <form id="practitioner-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        <Input
          label="Nombre completo"
          placeholder="Dr. Luis Estabridis Ramos"
          value={fullName}
          disabled={isLoading}
          onChange={(event) => setFullName(event.target.value)}
        />

        <div className="grid gap-4 sm:grid-cols-3">
          <Select
            label="Especialidad"
            options={specialtyOptions}
            placeholder="Sin especialidad"
            value={specialtyId}
            disabled={isLoading}
            onChange={(event) => setSpecialtyId(event.target.value)}
          />
          <Input
            label="Colegiatura"
            placeholder="CMP 45123"
            value={license}
            disabled={isLoading}
            onChange={(event) => setLicense(event.target.value)}
          />
          <Input
            label="Documento"
            value={document}
            disabled={isLoading}
            onChange={(event) => setDocument(event.target.value)}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <Input
            label="Teléfono"
            value={phone}
            disabled={isLoading}
            onChange={(event) => setPhone(event.target.value)}
          />
          <Input
            label="Correo"
            type="email"
            value={email}
            disabled={isLoading}
            onChange={(event) => setEmail(event.target.value)}
          />
          <Input
            label="Duración de cita"
            type="number"
            hint="minutos por espacio"
            value={slotMinutes}
            disabled={isLoading}
            onChange={(event) => setSlotMinutes(event.target.value)}
          />
        </div>

        <div className="space-y-3">
          <p className="caption uppercase tracking-wide">Horario de atención</p>

          {schedules.map((block, index) => (
            <div
              key={index}
              className="grid gap-3 rounded-xl border border-border p-3 sm:grid-cols-[1fr_1fr_1fr_auto]"
            >
              <Select
                options={WEEKDAY_OPTIONS}
                value={String(block.weekday)}
                disabled={isLoading}
                onChange={(event) => updateBlock(index, { weekday: Number(event.target.value) })}
              />
              <Input
                type="time"
                value={block.start_time}
                disabled={isLoading}
                onChange={(event) => updateBlock(index, { start_time: event.target.value })}
              />
              <Input
                type="time"
                value={block.end_time}
                disabled={isLoading}
                onChange={(event) => updateBlock(index, { end_time: event.target.value })}
              />
              <Button
                variant="ghost"
                size="icon"
                aria-label="Quitar bloque horario"
                disabled={isLoading}
                onClick={() => setSchedules((prev) => prev.filter((_, i) => i !== index))}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}

          <Button
            variant="outline"
            size="sm"
            leftIcon={<Plus className="h-4 w-4" />}
            disabled={isLoading}
            onClick={() => setSchedules((prev) => [...prev, emptyBlock()])}
          >
            Agregar bloque
          </Button>
        </div>

        <Switch
          label="Profesional activo"
          description="Los profesionales inactivos no aparecen en la agenda"
          checked={isActive}
          disabled={isLoading}
          onChange={setIsActive}
        />
      </form>
    </Modal>
  )
}
