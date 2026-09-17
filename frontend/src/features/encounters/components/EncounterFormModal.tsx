import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Activity, ClipboardList, Pill, Plus, Save, Stethoscope, Trash2 } from 'lucide-react'

import {
  Alert,
  Button,
  Input,
  Modal,
  Select,
  Tabs,
  Textarea,
  type SelectOption,
  type TabItem,
} from '@/components/ui'
import { ServicePicker } from '@/features/catalog/components/ServicePicker'
import { useModuleAccess } from '@/hooks/useModuleAccess'
import { useActivePractitioners } from '@/features/catalog/hooks/useCatalog'
import { useEncounterActions } from '@/features/encounters/hooks/useEncounters'
import { inventoryApi } from '@/features/inventory/api/inventory.api'
import { ProductPicker } from '@/features/inventory/components/ProductPicker'
import { PatientPicker } from '@/features/patients/components/PatientPicker'
import { useOwnPractitioner } from '@/hooks/useOwnPractitioner'
import { getErrorMessage } from '@/services/http'
import {
  DIAGNOSIS_KIND_LABELS,
  DIAGNOSIS_KINDS,
  type DiagnosisPayload,
  type Encounter,
  type MedicalService,
  type PatientSummary,
  type PrescriptionPayload,
  type Product,
  type ProductSummary,
} from '@/types'

const TABS: TabItem[] = [
  { key: 'clinical', label: 'Consulta', icon: Stethoscope },
  { key: 'vitals', label: 'Signos vitales', icon: Activity },
  { key: 'diagnoses', label: 'Diagnósticos', icon: ClipboardList },
  { key: 'prescriptions', label: 'Recetas', icon: Pill },
]

const KIND_OPTIONS: SelectOption[] = DIAGNOSIS_KINDS.map((kind) => ({
  value: kind,
  label: DIAGNOSIS_KIND_LABELS[kind],
}))

interface FormValues {
  service_id: string
  chief_complaint: string
  current_illness: string
  physical_exam: string
  treatment_plan: string
  indications: string
  observations: string
  systolic_pressure: string
  diastolic_pressure: string
  heart_rate: string
  respiratory_rate: string
  temperature: string
  oxygen_saturation: string
  weight_kg: string
  height_cm: string
}

function snapshotOf(
  patient: PatientSummary | null,
  service: MedicalService | null,
  values: FormValues,
  diagnoses: DiagnosisPayload[],
  prescriptions: PrescriptionRow[],
): string {
  return JSON.stringify([
    patient?.id ?? null,
    service?.id ?? null,
    values,
    diagnoses,
    // `product` es apoyo del selector y no viaja al servidor.
    prescriptions.map(({ product: _product, ...row }) => row),
  ])
}

const emptyValues = (): FormValues => ({
  service_id: '',
  chief_complaint: '',
  current_illness: '',
  physical_exam: '',
  treatment_plan: '',
  indications: '',
  observations: '',
  systolic_pressure: '',
  diastolic_pressure: '',
  heart_rate: '',
  respiratory_rate: '',
  temperature: '',
  oxygen_saturation: '',
  weight_kg: '',
  height_cm: '',
})

const emptyDiagnosis = (): DiagnosisPayload => ({
  code: '',
  description: '',
  kind: 'DEFINITIVO',
})

/**
 * Fila de receta en el formulario.
 *
 * `product` no viaja al servidor: acompaña a `product_id` solo para que el
 * selector pueda mostrar el producto ya enlazado con su stock y su precio.
 */
interface PrescriptionRow extends PrescriptionPayload {
  product: ProductSummary | null
}

const emptyPrescription = (): PrescriptionRow => ({
  product_id: null,
  product: null,
  medication: '',
  dose: '',
  frequency_hours: null,
  frequency_text: '',
  duration_days: null,
  quantity: null,
  instructions: '',
})

/** El detalle del producto trae de más lo que el selector necesita. */
const toSummary = (product: Product): ProductSummary => ({
  id: product.id,
  code: product.code,
  name: product.name,
  full_name: product.full_name,
  unit: product.unit,
  stock: product.stock,
  sale_price: product.sale_price,
  purchase_price: product.purchase_price,
  requires_prescription: product.requires_prescription,
  needs_restock: product.needs_restock,
  expiry_date: product.expiry_date,
  is_expired: product.is_expired,
  expires_soon: product.expires_soon,
})

/** Cómo se nombra a un profesional, se elija o venga dado por la sesión. */
const practitionerLabel = (item: { full_name: string; specialty_name: string | null }): string =>
  item.specialty_name ? `${item.full_name} — ${item.specialty_name}` : item.full_name

const numberOrNull = (value: string): number | null => {
  const parsed = Number(value)
  return value.trim() === '' || Number.isNaN(parsed) ? null : parsed
}

const textOrNull = (value: string | null | undefined): string | null => {
  const trimmed = (value ?? '').trim()
  return trimmed === '' ? null : trimmed
}

interface EncounterFormModalProps {
  open: boolean
  encounter: Encounter | null
  /** Cita desde la que se inicia la atención, si la hay. */
  appointmentId?: number | null
  initialPatient?: PatientSummary | null
  initialPractitionerId?: number | null
  onClose: () => void
}

export function EncounterFormModal({
  open,
  encounter,
  appointmentId = null,
  initialPatient = null,
  initialPractitionerId = null,
  onClose,
}: EncounterFormModalProps) {
  const isEdit = encounter !== null
  // La historia la escribe quien atiende. El resto del personal con acceso
  // —administración incluida— la consulta, pero no la modifica.
  const { canManage } = useModuleAccess()
  const canWrite = canManage('ENCOUNTERS')
  // Una atención finalizada o anulada se consulta, pero ya no admite cambios.
  const isClosed = encounter !== null && !encounter.is_editable
  const isReadOnly = !canWrite || isClosed
  const { practitioners } = useActivePractitioners()
  // La historia la firma quien atiende: si la sesión tiene ficha propia, el
  // profesional no se elige, es quien está dentro.
  const ownPractitioner = useOwnPractitioner(practitioners)
  const ownPractitionerId = ownPractitioner?.id ?? null
  const { create, update } = useEncounterActions()
  const isLoading = create.isPending || update.isPending
  const locked = isLoading || isReadOnly

  const [tab, setTab] = useState('clinical')
  const [patient, setPatient] = useState<PatientSummary | null>(null)
  const [practitionerId, setPractitionerId] = useState('')
  const [service, setService] = useState<MedicalService | null>(null)
  const [values, setValues] = useState<FormValues>(emptyValues)
  const [diagnoses, setDiagnoses] = useState<DiagnosisPayload[]>([])
  const [prescriptions, setPrescriptions] = useState<PrescriptionRow[]>([])
  const [formError, setFormError] = useState<string | null>(null)
  // Instantánea del formulario al abrirlo: lo que difiera de ella es trabajo
  // que se perdería al cerrar.
  const baseline = useRef('')

  useEffect(() => {
    if (!open) return
    setTab('clinical')
    setFormError(null)
    setService(null)

    if (encounter) {
      const editValues: FormValues = {
        service_id: encounter.service_id ? String(encounter.service_id) : '',
        chief_complaint: encounter.chief_complaint ?? '',
        current_illness: encounter.current_illness ?? '',
        physical_exam: encounter.physical_exam ?? '',
        treatment_plan: encounter.treatment_plan ?? '',
        indications: encounter.indications ?? '',
        observations: encounter.observations ?? '',
        systolic_pressure: encounter.systolic_pressure?.toString() ?? '',
        diastolic_pressure: encounter.diastolic_pressure?.toString() ?? '',
        heart_rate: encounter.heart_rate?.toString() ?? '',
        respiratory_rate: encounter.respiratory_rate?.toString() ?? '',
        temperature: encounter.temperature ?? '',
        oxygen_saturation: encounter.oxygen_saturation?.toString() ?? '',
        weight_kg: encounter.weight_kg ?? '',
        height_cm: encounter.height_cm ?? '',
      }
      const editDiagnoses = encounter.diagnoses.map((item) => ({
        code: item.code ?? '',
        description: item.description,
        kind: item.kind,
      }))
      const editPrescriptions = encounter.prescriptions.map((item) => ({
        product_id: item.product_id,
        product: null,
        medication: item.medication,
        dose: item.dose ?? '',
        frequency_hours: item.frequency_hours,
        frequency_text: item.frequency_text ?? '',
        duration_days: item.duration_days,
        quantity: item.quantity,
        instructions: item.instructions ?? '',
      }))

      setPatient(encounter.patient)
      setPractitionerId(String(encounter.practitioner_id))
      setValues(editValues)
      setDiagnoses(editDiagnoses)
      setPrescriptions(editPrescriptions)
      baseline.current = snapshotOf(
        encounter.patient,
        null,
        editValues,
        editDiagnoses,
        editPrescriptions,
      )
      return
    }

    const nuevo = emptyValues()
    setPatient(initialPatient)
    setPractitionerId(initialPractitionerId ? String(initialPractitionerId) : '')
    setValues(nuevo)
    setDiagnoses([])
    setPrescriptions([])
    baseline.current = snapshotOf(initialPatient, null, nuevo, [], [])
  }, [open, encounter, initialPatient, initialPractitionerId])

  const dirty =
    !isReadOnly && snapshotOf(patient, service, values, diagnoses, prescriptions) !== baseline.current

  /* La lista de profesionales llega después del primer render, así que la
     ficha propia se rellena en un efecto aparte: meterla en el de reinicio lo
     haría dispararse otra vez al cargar y borraría lo ya escrito. Solo actúa
     sobre un campo vacío, para no pisar una elección deliberada. */
  useEffect(() => {
    if (!open || encounter || !ownPractitionerId) return
    setPractitionerId((actual) => actual || String(ownPractitionerId))
  }, [open, encounter, ownPractitionerId])

  /* Las recetas guardan el id del producto, no su ficha: al abrir una atención
     ya registrada se recuperan para que el selector muestre cuál es. */
  useEffect(() => {
    if (!open || !encounter) return
    const ids = [
      ...new Set(
        encounter.prescriptions
          .map((item) => item.product_id)
          .filter((id): id is number => id !== null),
      ),
    ]
    if (ids.length === 0) return

    let cancelled = false
    void Promise.all(ids.map((id) => inventoryApi.getProduct(id).catch(() => null))).then(
      (products) => {
        if (cancelled) return
        const byId = new Map(
          products.filter((item): item is Product => item !== null).map((item) => [item.id, item]),
        )
        setPrescriptions((prev) =>
          prev.map((row) => {
            const product = row.product_id === null ? null : byId.get(row.product_id)
            return product ? { ...row, product: toSummary(product) } : row
          }),
        )
      },
    )
    return () => {
      cancelled = true
    }
  }, [open, encounter])

  const setField = (field: keyof FormValues) => (value: string) =>
    setValues((prev) => ({ ...prev, [field]: value }))

  const updateDiagnosis = (index: number, patch: Partial<DiagnosisPayload>) =>
    setDiagnoses((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)))

  const updatePrescription = (index: number, patch: Partial<PrescriptionRow>) =>
    setPrescriptions((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)))

  /* Al enlazar un producto del catálogo se copia su nombre al medicamento,
     salvo que el médico ya haya escrito uno distinto a mano. */
  const linkProduct = (index: number, row: PrescriptionRow, product: ProductSummary | null) => {
    const wasAuto = !row.medication.trim() || row.medication === row.product?.full_name
    updatePrescription(index, {
      product,
      product_id: product?.id ?? null,
      ...(product && wasAuto ? { medication: product.full_name } : {}),
    })
  }

  const clinicalContent = () => ({
    service_id: numberOrNull(values.service_id),
    chief_complaint: textOrNull(values.chief_complaint),
    current_illness: textOrNull(values.current_illness),
    physical_exam: textOrNull(values.physical_exam),
    treatment_plan: textOrNull(values.treatment_plan),
    indications: textOrNull(values.indications),
    observations: textOrNull(values.observations),
    systolic_pressure: numberOrNull(values.systolic_pressure),
    diastolic_pressure: numberOrNull(values.diastolic_pressure),
    heart_rate: numberOrNull(values.heart_rate),
    respiratory_rate: numberOrNull(values.respiratory_rate),
    temperature: textOrNull(values.temperature),
    oxygen_saturation: numberOrNull(values.oxygen_saturation),
    weight_kg: textOrNull(values.weight_kg),
    height_cm: textOrNull(values.height_cm),
  })

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    if (!patient) return setFormError('Seleccione el paciente')
    if (!practitionerId) return setFormError('Seleccione el profesional que atiende')

    const incompleteDiagnosis = diagnoses.some((item) => item.description.trim().length < 3)
    if (incompleteDiagnosis) {
      setTab('diagnoses')
      return setFormError('Complete la descripción de todos los diagnósticos')
    }
    const incompletePrescription = prescriptions.some((item) => item.medication.trim().length < 2)
    if (incompletePrescription) {
      setTab('prescriptions')
      return setFormError('Indique el medicamento en todas las recetas')
    }

    const cleanDiagnoses = diagnoses.map((item) => ({
      code: textOrNull(item.code),
      description: item.description.trim(),
      kind: item.kind,
    }))
    // `product` es apoyo del selector; al servidor solo va `product_id`.
    const cleanPrescriptions = prescriptions.map(({ product: _product, ...item }) => ({
      ...item,
      medication: item.medication.trim(),
      dose: textOrNull(item.dose),
      frequency_text: textOrNull(item.frequency_text),
      instructions: textOrNull(item.instructions),
    }))

    try {
      if (encounter) {
        await update.mutateAsync({
          id: encounter.id,
          payload: {
            ...clinicalContent(),
            diagnoses: cleanDiagnoses,
            prescriptions: cleanPrescriptions,
          },
        })
      } else {
        await create.mutateAsync({
          ...clinicalContent(),
          patient_id: patient.id,
          practitioner_id: Number(practitionerId),
          appointment_id: appointmentId,
          diagnoses: cleanDiagnoses,
          prescriptions: cleanPrescriptions,
        })
      }
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo guardar la atención'))
    }
  }

  const practitionerOptions: SelectOption[] = practitioners.map((item) => ({
    value: String(item.id),
    label: practitionerLabel(item),
  }))

  return (
    <Modal
      open={open}
      onClose={onClose}
      dirty={dirty}
      title={isEdit ? 'Atención médica' : 'Nueva atención'}
      description={
        isEdit
          ? `${encounter.patient_name} · ${encounter.practitioner_name}`
          : 'Registre la consulta, el diagnóstico y las indicaciones'
      }
      size="xl"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            {isReadOnly ? 'Cerrar' : 'Cancelar'}
          </Button>
          {!isReadOnly && (
            <Button
              type="submit"
              form="encounter-form"
              size="sm"
              isLoading={isLoading}
              leftIcon={<Save className="h-4 w-4" />}
            >
              {isEdit ? 'Guardar atención' : 'Iniciar atención'}
            </Button>
          )}
        </>
      }
    >
      <form id="encounter-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        {isReadOnly && (
          <Alert variant="info">
            {isClosed
              ? `Esta atención está ${encounter.status_label.toLowerCase()} y se muestra solo para consulta.`
              : 'Su perfil consulta la historia clínica, pero no la modifica: solo la registra quien atiende al paciente.'}
          </Alert>
        )}

        {!isEdit && (
          <>
            <PatientPicker
              value={patient}
              onChange={setPatient}
              disabled={locked || appointmentId !== null}
            />
            {!ownPractitioner && practitionerOptions.length === 0 && (
              <Alert variant="warning">
                No hay ningún profesional dado de alta, así que la atención no se puede
                firmar. Un administrador debe registrarlo desde Usuarios y perfiles.
              </Alert>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              {ownPractitioner ? (
                <Input
                  label="Profesional"
                  value={practitionerLabel(ownPractitioner)}
                  hint="Firma la atención con su ficha"
                  readOnly
                  disabled
                />
              ) : (
                <Select
                  label="Profesional"
                  options={practitionerOptions}
                  placeholder={
                    practitionerOptions.length === 0
                      ? 'No hay profesionales registrados'
                      : 'Seleccione el profesional'
                  }
                  value={practitionerId}
                  disabled={locked || practitionerOptions.length === 0}
                  onChange={(event) => setPractitionerId(event.target.value)}
                />
              )}
              <ServicePicker
                label="Servicio"
                placeholder="Busque el servicio (opcional)"
                value={service}
                disabled={locked}
                onChange={(item) => {
                  setService(item)
                  setField('service_id')(item ? String(item.id) : '')
                }}
              />
            </div>
          </>
        )}

        {patient?.has_alerts && (
          <Alert variant="danger">
            El paciente tiene antecedentes registrados (alergias o medicación actual). Revíselos en
            su ficha antes de prescribir.
          </Alert>
        )}

        <Tabs items={TABS} active={tab} onChange={setTab} />

        {tab === 'clinical' && (
          <div className="space-y-4">
            <Input
              label="Motivo de consulta"
              placeholder="Dolor abdominal de 2 días"
              value={values.chief_complaint}
              disabled={locked}
              onChange={(event) => setField('chief_complaint')(event.target.value)}
            />
            <Textarea
              label="Enfermedad actual"
              rows={4}
              value={values.current_illness}
              disabled={locked}
              onChange={(event) => setField('current_illness')(event.target.value)}
            />
            <Textarea
              label="Examen físico"
              rows={4}
              value={values.physical_exam}
              disabled={locked}
              onChange={(event) => setField('physical_exam')(event.target.value)}
            />
            <Textarea
              label="Plan de tratamiento"
              value={values.treatment_plan}
              disabled={locked}
              onChange={(event) => setField('treatment_plan')(event.target.value)}
            />
            <Textarea
              label="Indicaciones al paciente"
              hint="Se imprime en la receta y sirve de base para los recordatorios"
              value={values.indications}
              disabled={locked}
              onChange={(event) => setField('indications')(event.target.value)}
            />
            <Textarea
              label="Observaciones"
              value={values.observations}
              disabled={locked}
              onChange={(event) => setField('observations')(event.target.value)}
            />
          </div>
        )}

        {tab === 'vitals' && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Input
              label="PA sistólica"
              type="number"
              hint="mmHg"
              value={values.systolic_pressure}
              disabled={locked}
              onChange={(event) => setField('systolic_pressure')(event.target.value)}
            />
            <Input
              label="PA diastólica"
              type="number"
              hint="mmHg"
              value={values.diastolic_pressure}
              disabled={locked}
              onChange={(event) => setField('diastolic_pressure')(event.target.value)}
            />
            <Input
              label="Frecuencia cardiaca"
              type="number"
              hint="lpm"
              value={values.heart_rate}
              disabled={locked}
              onChange={(event) => setField('heart_rate')(event.target.value)}
            />
            <Input
              label="Frecuencia respiratoria"
              type="number"
              hint="rpm"
              value={values.respiratory_rate}
              disabled={locked}
              onChange={(event) => setField('respiratory_rate')(event.target.value)}
            />
            <Input
              label="Temperatura"
              type="number"
              step="0.1"
              hint="°C"
              value={values.temperature}
              disabled={locked}
              onChange={(event) => setField('temperature')(event.target.value)}
            />
            <Input
              label="Saturación"
              type="number"
              hint="% SpO₂"
              value={values.oxygen_saturation}
              disabled={locked}
              onChange={(event) => setField('oxygen_saturation')(event.target.value)}
            />
            <Input
              label="Peso"
              type="number"
              step="0.01"
              hint="kg"
              value={values.weight_kg}
              disabled={locked}
              onChange={(event) => setField('weight_kg')(event.target.value)}
            />
            <Input
              label="Talla"
              type="number"
              step="0.1"
              hint="cm"
              value={values.height_cm}
              disabled={locked}
              onChange={(event) => setField('height_cm')(event.target.value)}
            />
          </div>
        )}

        {tab === 'diagnoses' && (
          <div className="space-y-3">
            {diagnoses.length === 0 && (
              <p className="text-sm text-muted">
                Agregue al menos un diagnóstico antes de finalizar la atención.
              </p>
            )}

            {diagnoses.map((diagnosis, index) => (
              <div
                key={index}
                className="grid gap-3 rounded-xl border border-border p-3 sm:grid-cols-[7rem_1fr_9rem_auto]"
              >
                <Input
                  placeholder="CIE-10"
                  value={diagnosis.code ?? ''}
                  disabled={locked}
                  onChange={(event) => updateDiagnosis(index, { code: event.target.value })}
                />
                <Input
                  placeholder="Descripción del diagnóstico"
                  value={diagnosis.description}
                  disabled={locked}
                  onChange={(event) => updateDiagnosis(index, { description: event.target.value })}
                />
                <Select
                  options={KIND_OPTIONS}
                  value={diagnosis.kind}
                  disabled={locked}
                  onChange={(event) =>
                    updateDiagnosis(index, { kind: event.target.value as DiagnosisPayload['kind'] })
                  }
                />
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Quitar diagnóstico"
                  disabled={locked}
                  onClick={() => setDiagnoses((prev) => prev.filter((_, i) => i !== index))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}

            <Button
              variant="outline"
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              disabled={locked}
              onClick={() => setDiagnoses((prev) => [...prev, emptyDiagnosis()])}
            >
              Agregar diagnóstico
            </Button>
          </div>
        )}

        {tab === 'prescriptions' && (
          <div className="space-y-3">
            {prescriptions.map((prescription, index) => (
              <div key={index} className="space-y-3 rounded-xl border border-border p-3">
                <ProductPicker
                  label="Producto de farmacia"
                  value={prescription.product}
                  disabled={locked}
                  onChange={(product) => linkProduct(index, prescription, product)}
                />
                {prescription.product?.requires_prescription && (
                  <p className="text-xs font-medium text-warning-dark">
                    Producto de venta bajo receta.
                  </p>
                )}

                <div className="flex items-start gap-3">
                  <Input
                    label="Medicamento"
                    hint="Enlace el producto para descontarlo de farmacia; si no está en el catálogo, escríbalo aquí."
                    placeholder="Omeprazol 20 mg"
                    value={prescription.medication}
                    disabled={locked}
                    onChange={(event) =>
                      updatePrescription(index, { medication: event.target.value })
                    }
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Quitar receta"
                    className="mt-7"
                    disabled={locked}
                    onClick={() => setPrescriptions((prev) => prev.filter((_, i) => i !== index))}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>

                <div className="grid gap-3 sm:grid-cols-4">
                  <Input
                    label="Dosis"
                    placeholder="1 cápsula"
                    value={prescription.dose ?? ''}
                    disabled={locked}
                    onChange={(event) => updatePrescription(index, { dose: event.target.value })}
                  />
                  <Input
                    label="Cada (horas)"
                    type="number"
                    value={prescription.frequency_hours?.toString() ?? ''}
                    disabled={locked}
                    onChange={(event) =>
                      updatePrescription(index, {
                        frequency_hours: numberOrNull(event.target.value),
                      })
                    }
                  />
                  <Input
                    label="Duración (días)"
                    type="number"
                    value={prescription.duration_days?.toString() ?? ''}
                    disabled={locked}
                    onChange={(event) =>
                      updatePrescription(index, {
                        duration_days: numberOrNull(event.target.value),
                      })
                    }
                  />
                  <Input
                    label="Cantidad"
                    type="number"
                    value={prescription.quantity?.toString() ?? ''}
                    disabled={locked}
                    onChange={(event) =>
                      updatePrescription(index, { quantity: numberOrNull(event.target.value) })
                    }
                  />
                </div>

                <Input
                  label="Indicaciones"
                  placeholder="En ayunas, con abundante agua"
                  value={prescription.instructions ?? ''}
                  disabled={locked}
                  onChange={(event) =>
                    updatePrescription(index, { instructions: event.target.value })
                  }
                />
              </div>
            ))}

            <Button
              variant="outline"
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              disabled={locked}
              onClick={() => setPrescriptions((prev) => [...prev, emptyPrescription()])}
            >
              Agregar medicamento
            </Button>
            <p className="text-xs text-muted">
              Indicar la frecuencia y la duración permite programar automáticamente los
              recordatorios de toma del paciente.
            </p>
          </div>
        )}
      </form>
    </Modal>
  )
}
