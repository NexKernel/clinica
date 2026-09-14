import { useEffect, useMemo, useState } from 'react'
import { FileSignature, Search } from 'lucide-react'

import { Alert, Badge, Button, Input, LoadingState, Modal, Select } from '@/components/ui'
import { useDocumentActions, useDocumentTemplates } from '@/features/documents/hooks/useDocuments'
import { useActivePractitioners } from '@/features/catalog/hooks/useCatalog'
import { PatientPicker } from '@/features/patients/components/PatientPicker'
import { cn } from '@/lib/utils'
import { getErrorMessage } from '@/services/http'
import {
  DOCUMENT_FAMILIES,
  DOCUMENT_FAMILY_LABELS,
  type DocumentTemplateSummary,
  type PatientSummary,
} from '@/types'

const FAMILY_OPTIONS = DOCUMENT_FAMILIES.map((family) => ({
  value: family,
  label: DOCUMENT_FAMILY_LABELS[family],
}))

const normalize = (text: string): string =>
  text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()

interface TemplatePickerModalProps {
  open: boolean
  /** Paciente sugerido al abrir desde su ficha. */
  patient?: PatientSummary | null
  onClose: () => void
  /** Recibe el borrador recién creado para continuar llenándolo. */
  onCreated: (documentId: number) => void
}

export function TemplatePickerModal({
  open,
  patient: initialPatient = null,
  onClose,
  onCreated,
}: TemplatePickerModalProps) {
  const { templates, isLoading, error } = useDocumentTemplates()
  const { practitioners } = useActivePractitioners()
  const { create } = useDocumentActions()

  const [patient, setPatient] = useState<PatientSummary | null>(initialPatient)
  const [practitionerId, setPractitionerId] = useState('')
  const [family, setFamily] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<DocumentTemplateSummary | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setPatient(initialPatient)
    setPractitionerId('')
    setFamily('')
    setSearch('')
    setSelected(null)
    setFormError(null)
  }, [open, initialPatient])

  const visible = useMemo(() => {
    const term = normalize(search.trim())
    return templates.filter(
      (template) =>
        (!family || template.family === family) &&
        (!term ||
          normalize(template.title).includes(term) ||
          normalize(template.description ?? '').includes(term) ||
          normalize(template.code).includes(term)),
    )
  }, [templates, family, search])

  const practitionerOptions = practitioners.map((item) => ({
    value: String(item.id),
    label: item.full_name,
  }))

  const handleCreate = async () => {
    if (create.isPending) return
    if (!patient) return setFormError('Seleccione el paciente')
    if (!selected) return setFormError('Elija el formato a emitir')

    setFormError(null)
    try {
      const document = await create.mutateAsync({
        template_code: selected.code,
        patient_id: patient.id,
        encounter_id: null,
        study_id: null,
        practitioner_id: practitionerId ? Number(practitionerId) : null,
        data: {},
      })
      onCreated(document.id)
    } catch (err) {
      setFormError(getErrorMessage(err, 'No se pudo crear el documento'))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Nuevo documento"
      description="Elija el formato del catálogo y el paciente al que corresponde"
      size="xl"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={create.isPending} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            size="sm"
            isLoading={create.isPending}
            leftIcon={<FileSignature className="h-4 w-4" />}
            onClick={() => void handleCreate()}
          >
            Continuar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}

        <div className="grid gap-4 sm:grid-cols-2">
          <PatientPicker value={patient} onChange={setPatient} disabled={create.isPending} />
          <Select
            label="Profesional responsable"
            options={practitionerOptions}
            placeholder="Sin profesional"
            value={practitionerId}
            disabled={create.isPending}
            onChange={(event) => setPractitionerId(event.target.value)}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <Input
            containerClassName="sm:col-span-2"
            placeholder="Buscar formato"
            icon={<Search className="h-[18px] w-[18px]" />}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <Select
            options={FAMILY_OPTIONS}
            placeholder="Todas las familias"
            value={family}
            onChange={(event) => setFamily(event.target.value)}
          />
        </div>

        {isLoading ? (
          <LoadingState label="Cargando catálogo" />
        ) : visible.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted">
            Ningún formato coincide con la búsqueda.
          </p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {visible.map((template) => {
              const isSelected = selected?.code === template.code
              return (
                <li key={template.code}>
                  <button
                    type="button"
                    aria-pressed={isSelected}
                    onClick={() => {
                      setSelected(template)
                      setFormError(null)
                    }}
                    className={cn(
                      'w-full rounded-xl border p-3 text-left transition-colors',
                      isSelected
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/40 hover:bg-primary/5',
                    )}
                  >
                    <p className="text-sm font-medium text-foreground">{template.title}</p>
                    {template.description && (
                      <p className="mt-0.5 text-xs text-muted">{template.description}</p>
                    )}
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      <Badge variant={isSelected ? 'primary' : 'neutral'}>
                        {template.family_label}
                      </Badge>
                      <span className="text-[11px] text-muted">
                        {template.code} · {template.field_count} campo
                        {template.field_count === 1 ? '' : 's'}
                      </span>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </Modal>
  )
}
