import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { Save, type LucideIcon } from 'lucide-react'
import { HeartPulse, IdCard, MapPin, Phone } from 'lucide-react'

import {
  Alert,
  Button,
  Input,
  Modal,
  Select,
  Switch,
  Tabs,
  Textarea,
  type SelectOption,
  type TabItem,
} from '@/components/ui'
import { usePatientActions } from '@/features/patients/hooks/usePatients'
import { getErrorMessage } from '@/services/http'
import { DOCUMENT_TYPE_LABELS, DOCUMENT_TYPES, type Patient, type PatientPayload } from '@/types'

type FieldErrors = Partial<Record<keyof PatientPayload, string>>

const DOCUMENT_OPTIONS: SelectOption[] = DOCUMENT_TYPES.map((code) => ({
  value: code,
  label: DOCUMENT_TYPE_LABELS[code],
}))

const SEX_OPTIONS: SelectOption[] = [
  { value: 'F', label: 'Femenino' },
  { value: 'M', label: 'Masculino' },
]

const BLOOD_OPTIONS: SelectOption[] = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-'].map(
  (value) => ({ value, label: value }),
)

/** Longitud exacta esperada por tipo de documento (igual que en el backend). */
const DOCUMENT_LENGTH: Partial<Record<string, number>> = { DNI: 8, RUC: 11 }

const TABS: (TabItem & { icon: LucideIcon })[] = [
  { key: 'identity', label: 'Identificación', icon: IdCard },
  { key: 'contact', label: 'Contacto', icon: Phone },
  { key: 'clinical', label: 'Antecedentes', icon: HeartPulse },
]

const emptyValues = (): PatientPayload => ({
  document_type: 'DNI',
  document_number: '',
  first_name: '',
  last_name_paternal: '',
  last_name_maternal: '',
  birth_date: '',
  sex: null,
  phone: '',
  whatsapp: '',
  email: '',
  address: '',
  district: '',
  province: '',
  department: '',
  emergency_contact: '',
  emergency_phone: '',
  blood_type: '',
  insurance: '',
  allergies: '',
  personal_history: '',
  family_history: '',
  surgical_history: '',
  current_medication: '',
  notes: '',
  is_active: true,
})

function validate(values: PatientPayload): FieldErrors {
  const errors: FieldErrors = {}

  if (values.first_name.trim().length < 2) errors.first_name = 'Ingrese los nombres'
  if (values.last_name_paternal.trim().length < 2)
    errors.last_name_paternal = 'Ingrese el apellido paterno'

  if (values.document_type !== 'SIN_DOCUMENTO') {
    const value = (values.document_number ?? '').trim()
    const expected = DOCUMENT_LENGTH[values.document_type]
    if (!value) errors.document_number = 'Ingrese el número de documento'
    else if (expected && value.length !== expected)
      errors.document_number = `Debe tener ${expected} dígitos`
    else if (expected && !/^\d+$/.test(value)) errors.document_number = 'Solo dígitos'
  }

  if (values.birth_date && values.birth_date > new Date().toISOString().slice(0, 10)) {
    errors.birth_date = 'La fecha no puede ser futura'
  }

  return errors
}

/** Los campos vacíos viajan como null, tal como los espera la API. */
function toPayload(values: PatientPayload): PatientPayload {
  const clean = (value: string | null) => {
    const trimmed = (value ?? '').trim()
    return trimmed === '' ? null : trimmed
  }

  return {
    ...values,
    document_number:
      values.document_type === 'SIN_DOCUMENTO' ? null : clean(values.document_number),
    first_name: values.first_name.trim(),
    last_name_paternal: values.last_name_paternal.trim(),
    last_name_maternal: clean(values.last_name_maternal),
    birth_date: clean(values.birth_date),
    phone: clean(values.phone),
    whatsapp: clean(values.whatsapp),
    email: clean(values.email),
    address: clean(values.address),
    district: clean(values.district),
    province: clean(values.province),
    department: clean(values.department),
    emergency_contact: clean(values.emergency_contact),
    emergency_phone: clean(values.emergency_phone),
    blood_type: clean(values.blood_type),
    insurance: clean(values.insurance),
    allergies: clean(values.allergies),
    personal_history: clean(values.personal_history),
    family_history: clean(values.family_history),
    surgical_history: clean(values.surgical_history),
    current_medication: clean(values.current_medication),
    notes: clean(values.notes),
  }
}

const fromPatient = (patient: Patient): PatientPayload => ({
  ...emptyValues(),
  ...patient,
  document_number: patient.document_number ?? '',
  last_name_maternal: patient.last_name_maternal ?? '',
  birth_date: patient.birth_date ?? '',
  phone: patient.phone ?? '',
  whatsapp: patient.whatsapp ?? '',
  email: patient.email ?? '',
  address: patient.address ?? '',
  district: patient.district ?? '',
  province: patient.province ?? '',
  department: patient.department ?? '',
  emergency_contact: patient.emergency_contact ?? '',
  emergency_phone: patient.emergency_phone ?? '',
  blood_type: patient.blood_type ?? '',
  insurance: patient.insurance ?? '',
  allergies: patient.allergies ?? '',
  personal_history: patient.personal_history ?? '',
  family_history: patient.family_history ?? '',
  surgical_history: patient.surgical_history ?? '',
  current_medication: patient.current_medication ?? '',
  notes: patient.notes ?? '',
})

interface PatientFormModalProps {
  open: boolean
  patient: Patient | null
  onClose: () => void
  onSaved?: (patient: Patient) => void
}

export function PatientFormModal({ open, patient, onClose, onSaved }: PatientFormModalProps) {
  const isEdit = patient !== null
  const [values, setValues] = useState<PatientPayload>(emptyValues)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [tab, setTab] = useState('identity')

  const { create, update } = usePatientActions()
  const isLoading = create.isPending || update.isPending

  useEffect(() => {
    if (!open) return
    setErrors({})
    setServerError(null)
    setTab('identity')
    setValues(patient ? fromPatient(patient) : emptyValues())
  }, [open, patient])

  const handleChange =
    (field: keyof PatientPayload) =>
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      const { value } = event.target
      setValues((prev) => ({ ...prev, [field]: value }))
      if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }))
      if (serverError) setServerError(null)
    }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    const nextErrors = validate(values)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      setTab('identity')
      return
    }

    try {
      const payload = toPayload(values)
      const saved = patient
        ? await update.mutateAsync({ publicId: patient.public_id, payload })
        : await create.mutateAsync(payload)
      onSaved?.(saved)
      onClose()
    } catch (error) {
      setServerError(getErrorMessage(error, 'No se pudo guardar el paciente'))
    }
  }

  const withoutDocument = values.document_type === 'SIN_DOCUMENTO'

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Editar paciente' : 'Nuevo paciente'}
      description={
        isEdit
          ? `Historia ${patient.history_number}`
          : 'Registre los datos del paciente para su atención'
      }
      size="xl"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="patient-form"
            size="sm"
            isLoading={isLoading}
            leftIcon={<Save className="h-4 w-4" />}
          >
            {isEdit ? 'Guardar cambios' : 'Registrar paciente'}
          </Button>
        </>
      }
    >
      <form id="patient-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {serverError && <Alert variant="danger">{serverError}</Alert>}

        <Tabs items={TABS} active={tab} onChange={setTab} />

        {tab === 'identity' && (
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Select
                label="Tipo de documento"
                options={DOCUMENT_OPTIONS}
                value={values.document_type}
                disabled={isLoading}
                onChange={handleChange('document_type')}
              />
              <Input
                label="Número de documento"
                placeholder={withoutDocument ? 'No aplica' : '45877844'}
                value={values.document_number ?? ''}
                error={errors.document_number}
                disabled={isLoading || withoutDocument}
                onChange={handleChange('document_number')}
              />
            </div>

            <Input
              label="Nombres"
              placeholder="María Elena"
              value={values.first_name}
              error={errors.first_name}
              disabled={isLoading}
              onChange={handleChange('first_name')}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Apellido paterno"
                value={values.last_name_paternal}
                error={errors.last_name_paternal}
                disabled={isLoading}
                onChange={handleChange('last_name_paternal')}
              />
              <Input
                label="Apellido materno"
                value={values.last_name_maternal ?? ''}
                disabled={isLoading}
                onChange={handleChange('last_name_maternal')}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <Input
                label="Fecha de nacimiento"
                type="date"
                value={values.birth_date ?? ''}
                error={errors.birth_date}
                disabled={isLoading}
                onChange={handleChange('birth_date')}
              />
              <Select
                label="Sexo"
                options={SEX_OPTIONS}
                placeholder="Sin especificar"
                value={values.sex ?? ''}
                disabled={isLoading}
                onChange={handleChange('sex')}
              />
              <Select
                label="Grupo sanguíneo"
                options={BLOOD_OPTIONS}
                placeholder="Sin registrar"
                value={values.blood_type ?? ''}
                disabled={isLoading}
                onChange={handleChange('blood_type')}
              />
            </div>

            <Switch
              label="Paciente activo"
              description="Los pacientes inactivos no aparecen al programar citas"
              checked={values.is_active}
              disabled={isLoading}
              onChange={(checked) => setValues((prev) => ({ ...prev, is_active: checked }))}
            />
          </div>
        )}

        {tab === 'contact' && (
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Teléfono"
                placeholder="964123456"
                icon={<Phone className="h-[18px] w-[18px]" />}
                value={values.phone ?? ''}
                disabled={isLoading}
                onChange={handleChange('phone')}
              />
              <Input
                label="WhatsApp"
                placeholder="964123456"
                hint="Se usa para enviar resultados y recordatorios"
                value={values.whatsapp ?? ''}
                disabled={isLoading}
                onChange={handleChange('whatsapp')}
              />
            </div>

            <Input
              label="Correo electrónico"
              type="email"
              value={values.email ?? ''}
              disabled={isLoading}
              onChange={handleChange('email')}
            />

            <Input
              label="Dirección"
              icon={<MapPin className="h-[18px] w-[18px]" />}
              value={values.address ?? ''}
              disabled={isLoading}
              onChange={handleChange('address')}
            />

            <div className="grid gap-4 sm:grid-cols-3">
              <Input
                label="Distrito"
                value={values.district ?? ''}
                disabled={isLoading}
                onChange={handleChange('district')}
              />
              <Input
                label="Provincia"
                value={values.province ?? ''}
                disabled={isLoading}
                onChange={handleChange('province')}
              />
              <Input
                label="Departamento"
                value={values.department ?? ''}
                disabled={isLoading}
                onChange={handleChange('department')}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Contacto de emergencia"
                value={values.emergency_contact ?? ''}
                disabled={isLoading}
                onChange={handleChange('emergency_contact')}
              />
              <Input
                label="Teléfono de emergencia"
                value={values.emergency_phone ?? ''}
                disabled={isLoading}
                onChange={handleChange('emergency_phone')}
              />
            </div>

            <Input
              label="Seguro o convenio"
              placeholder="SIS, EsSalud, particular"
              value={values.insurance ?? ''}
              disabled={isLoading}
              onChange={handleChange('insurance')}
            />
          </div>
        )}

        {tab === 'clinical' && (
          <div className="space-y-4">
            <Textarea
              label="Alergias"
              hint="Se muestra como alerta en la ficha del paciente"
              value={values.allergies ?? ''}
              disabled={isLoading}
              onChange={handleChange('allergies')}
            />
            <Textarea
              label="Medicación actual"
              value={values.current_medication ?? ''}
              disabled={isLoading}
              onChange={handleChange('current_medication')}
            />
            <Textarea
              label="Antecedentes personales"
              value={values.personal_history ?? ''}
              disabled={isLoading}
              onChange={handleChange('personal_history')}
            />
            <Textarea
              label="Antecedentes familiares"
              value={values.family_history ?? ''}
              disabled={isLoading}
              onChange={handleChange('family_history')}
            />
            <Textarea
              label="Antecedentes quirúrgicos"
              value={values.surgical_history ?? ''}
              disabled={isLoading}
              onChange={handleChange('surgical_history')}
            />
            <Textarea
              label="Observaciones"
              value={values.notes ?? ''}
              disabled={isLoading}
              onChange={handleChange('notes')}
            />
          </div>
        )}
      </form>
    </Modal>
  )
}
