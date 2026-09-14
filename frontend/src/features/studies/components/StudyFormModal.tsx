import { useEffect, useState, type FormEvent } from 'react'
import { Save } from 'lucide-react'

import { Alert, Button, Input, Modal, Select, Textarea, type SelectOption } from '@/components/ui'
import { useActivePractitioners } from '@/features/catalog/hooks/useCatalog'
import { useStudyActions } from '@/features/studies/hooks/useStudies'
import { PatientPicker } from '@/features/patients/components/PatientPicker'
import { getErrorMessage } from '@/services/http'
import {
  STUDY_TYPE_LABELS,
  STUDY_TYPES,
  type PatientSummary,
  type Study,
  type StudyType,
} from '@/types'

const TYPE_OPTIONS: SelectOption[] = STUDY_TYPES.map((type) => ({
  value: type,
  label: STUDY_TYPE_LABELS[type],
}))

interface StudyFormModalProps {
  open: boolean
  study: Study | null
  onClose: () => void
}

export function StudyFormModal({ open, study, onClose }: StudyFormModalProps) {
  const isEdit = study !== null
  const { practitioners } = useActivePractitioners()
  const { create, update } = useStudyActions()
  const isLoading = create.isPending || update.isPending

  const [patient, setPatient] = useState<PatientSummary | null>(null)
  const [studyType, setStudyType] = useState<StudyType>('LABORATORIO')
  const [name, setName] = useState('')
  const [requestedBy, setRequestedBy] = useState('')
  const [clinicalNotes, setClinicalNotes] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setFormError(null)

    if (study) {
      setPatient(study.patient)
      setStudyType(study.study_type)
      setName(study.name)
      setRequestedBy(study.requested_by_id ? String(study.requested_by_id) : '')
      setClinicalNotes(study.clinical_notes ?? '')
      return
    }

    setPatient(null)
    setStudyType('LABORATORIO')
    setName('')
    setRequestedBy('')
    setClinicalNotes('')
  }, [open, study])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    if (!patient) return setFormError('Seleccione el paciente')
    if (name.trim().length < 3) return setFormError('Indique el nombre del estudio')

    const payload = {
      patient_id: patient.id,
      encounter_id: study?.encounter_id ?? null,
      requested_by_id: requestedBy ? Number(requestedBy) : null,
      service_id: study?.service_id ?? null,
      study_type: studyType,
      name: name.trim(),
      clinical_notes: clinicalNotes.trim() || null,
    }

    try {
      if (study) {
        await update.mutateAsync({ id: study.id, payload })
      } else {
        await create.mutateAsync(payload)
      }
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo guardar el estudio'))
    }
  }

  const practitionerOptions: SelectOption[] = practitioners.map((item) => ({
    value: String(item.id),
    label: item.full_name,
  }))

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Editar solicitud' : 'Nueva solicitud de estudio'}
      description="Laboratorio, Rayos X, ecografía u otro apoyo al diagnóstico"
      size="md"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="study-form"
            size="sm"
            isLoading={isLoading}
            leftIcon={<Save className="h-4 w-4" />}
          >
            {isEdit ? 'Guardar cambios' : 'Registrar solicitud'}
          </Button>
        </>
      }
    >
      <form id="study-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        <PatientPicker value={patient} onChange={setPatient} disabled={isLoading || isEdit} />

        <div className="grid gap-4 sm:grid-cols-2">
          <Select
            label="Tipo de estudio"
            options={TYPE_OPTIONS}
            value={studyType}
            disabled={isLoading}
            onChange={(event) => setStudyType(event.target.value as StudyType)}
          />
          <Select
            label="Solicitado por"
            options={practitionerOptions}
            placeholder="Sin profesional"
            value={requestedBy}
            disabled={isLoading}
            onChange={(event) => setRequestedBy(event.target.value)}
          />
        </div>

        <Input
          label="Nombre del estudio"
          placeholder="Radiografía de tórax PA, hemograma completo…"
          value={name}
          disabled={isLoading}
          onChange={(event) => setName(event.target.value)}
        />

        <Textarea
          label="Indicación clínica"
          placeholder="Motivo por el que se solicita el estudio"
          value={clinicalNotes}
          disabled={isLoading}
          onChange={(event) => setClinicalNotes(event.target.value)}
        />
      </form>
    </Modal>
  )
}
