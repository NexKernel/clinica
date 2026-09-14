import { useEffect, useMemo, useState } from 'react'
import { Eye, Save, Stamp } from 'lucide-react'

import {
  Alert,
  Badge,
  Button,
  LoadingState,
  Modal,
  Select,
  type SelectOption,
} from '@/components/ui'
import {
  DocumentFieldset,
  missingRequired,
  toDocumentData,
  toFieldValues,
  type FieldValues,
} from '@/features/documents/components/DocumentFieldset'
import { useDocument, useDocumentActions } from '@/features/documents/hooks/useDocuments'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useActivePractitioners } from '@/features/catalog/hooks/useCatalog'
import { usePatientEncounters } from '@/features/encounters/hooks/useEncounters'
import { usePatientStudies } from '@/features/studies/hooks/useStudies'
import { formatDate, formatDateTime } from '@/lib/datetime'
import { rolesForNavItem } from '@/routes/navigation'
import { getErrorMessage } from '@/services/http'
import { hasRole } from '@/store/auth.store'
import type { ClinicalDocument, DocumentPayload } from '@/types'

/* Recepción y laboratorio emiten documentos pero no ven atenciones: para esos
   perfiles el selector se omite en vez de pedir al servidor algo que negará. */
const ENCOUNTER_ROLES = rolesForNavItem('consultations')

const STATUS_VARIANT = {
  BORRADOR: 'warning',
  EMITIDO: 'success',
  ANULADO: 'danger',
} as const

interface DocumentEditorModalProps {
  open: boolean
  documentId: number | null
  onClose: () => void
  onPreview: (documentId: number) => void
}

export function DocumentEditorModal({
  open,
  documentId,
  onClose,
  onPreview,
}: DocumentEditorModalProps) {
  const { document, isLoading, error } = useDocument(open ? documentId : null)
  const { update, issue } = useDocumentActions()
  const { practitioners } = useActivePractitioners()
  const { user } = useAuth()

  const canLinkEncounter = hasRole(user, ENCOUNTER_ROLES)
  const patientId = document?.patient_id ?? null
  const { studies } = usePatientStudies(open ? patientId : null)
  const { encounters } = usePatientEncounters(open ? patientId : null, canLinkEncounter)

  const [values, setValues] = useState<FieldValues>({})
  const [practitionerId, setPractitionerId] = useState('')
  const [encounterId, setEncounterId] = useState('')
  const [studyId, setStudyId] = useState('')
  const [invalidKeys, setInvalidKeys] = useState<string[]>([])
  const [feedback, setFeedback] = useState<{ tone: 'success' | 'danger'; text: string } | null>(
    null,
  )

  useEffect(() => {
    if (!open || !document) return
    setValues(toFieldValues(document.fields, document.data))
    setPractitionerId(document.practitioner_id ? String(document.practitioner_id) : '')
    setEncounterId(document.encounter_id ? String(document.encounter_id) : '')
    setStudyId(document.study_id ? String(document.study_id) : '')
    setInvalidKeys([])
    setFeedback(null)
  }, [open, document])

  const isEditable = document?.is_draft ?? false
  const isBusy = update.isPending || issue.isPending

  const practitionerOptions: SelectOption[] = useMemo(
    () => practitioners.map((item) => ({ value: String(item.id), label: item.full_name })),
    [practitioners],
  )

  const encounterOptions: SelectOption[] = useMemo(
    () =>
      encounters.map((item) => ({
        value: String(item.id),
        label: `${formatDate(item.started_at)} · ${item.practitioner_name}`,
      })),
    [encounters],
  )

  const studyOptions: SelectOption[] = useMemo(
    () =>
      studies.map((item) => ({
        value: String(item.id),
        label: `${item.name} · ${formatDate(item.requested_at)}`,
      })),
    [studies],
  )

  const payloadOf = (source: ClinicalDocument): DocumentPayload => ({
    patient_id: source.patient_id,
    encounter_id: encounterId ? Number(encounterId) : null,
    study_id: studyId ? Number(studyId) : null,
    practitioner_id: practitionerId ? Number(practitionerId) : null,
    data: toDocumentData(source.fields, values),
  })

  const save = async (): Promise<boolean> => {
    if (!document) return false
    setFeedback(null)
    try {
      await update.mutateAsync({ id: document.id, payload: payloadOf(document) })
      return true
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo guardar el documento') })
      return false
    }
  }

  const handleSave = async () => {
    if (await save()) setFeedback({ tone: 'success', text: 'Borrador guardado.' })
  }

  const handlePreview = async () => {
    if (!document) return
    // La hoja se arma en el servidor con lo guardado: primero se persiste lo
    // escrito, para que la vista previa muestre el estado actual del borrador.
    if (isEditable && !(await save())) return
    onPreview(document.id)
  }

  const handleIssue = async () => {
    if (!document) return

    const missing = missingRequired(document.fields, values)
    setInvalidKeys(missing.map((field) => field.key))
    if (missing.length > 0) {
      setFeedback({
        tone: 'danger',
        text: `Complete antes de emitir: ${missing.map((field) => field.label).join(', ')}`,
      })
      return
    }

    if (!(await save())) return

    try {
      await issue.mutateAsync(document.id)
      onPreview(document.id)
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo emitir el documento') })
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={document ? document.title : 'Documento'}
      description={document ? `${document.number} · ${document.patient_name}` : 'Cargando documento'}
      size="xl"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isBusy} onClick={onClose}>
            Cerrar
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!document || isBusy}
            leftIcon={<Eye className="h-4 w-4" />}
            onClick={() => void handlePreview()}
          >
            Vista previa
          </Button>
          {isEditable && (
            <>
              <Button
                variant="outline"
                size="sm"
                isLoading={update.isPending}
                leftIcon={<Save className="h-4 w-4" />}
                onClick={() => void handleSave()}
              >
                Guardar borrador
              </Button>
              <Button
                size="sm"
                isLoading={issue.isPending}
                leftIcon={<Stamp className="h-4 w-4" />}
                onClick={() => void handleIssue()}
              >
                Emitir
              </Button>
            </>
          )}
        </>
      }
    >
      {isLoading && <LoadingState label="Cargando documento" />}
      {error && <Alert variant="danger">{error}</Alert>}

      {document && (
        <div className="space-y-5">
          {feedback && <Alert variant={feedback.tone}>{feedback.text}</Alert>}

          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={STATUS_VARIANT[document.status]} dot>
              {document.status_label}
            </Badge>
            <Badge variant="neutral">{document.family_label}</Badge>
            <span className="text-xs text-muted">
              {document.template_code} v{document.template_version}
            </span>
            {document.issued_at && (
              <span className="text-xs text-muted">
                Emitido el {formatDateTime(document.issued_at)}
              </span>
            )}
          </div>

          {!isEditable && (
            <Alert variant={document.status === 'ANULADO' ? 'danger' : 'info'}>
              {document.status === 'ANULADO'
                ? `Documento anulado: ${document.void_reason ?? 'sin motivo registrado'}`
                : 'El documento fue emitido y ya no se puede corregir. Para cambiarlo, anúlelo y emita uno nuevo.'}
            </Alert>
          )}

          <div className="grid gap-4 sm:grid-cols-3">
            <Select
              label="Profesional que firma"
              options={practitionerOptions}
              placeholder="Sin profesional"
              value={practitionerId}
              disabled={!isEditable || isBusy}
              onChange={(event) => setPractitionerId(event.target.value)}
            />
            {canLinkEncounter && (
              <Select
                label="Atención vinculada"
                options={encounterOptions}
                placeholder="Sin vincular"
                value={encounterId}
                disabled={!isEditable || isBusy}
                onChange={(event) => setEncounterId(event.target.value)}
              />
            )}
            <Select
              label="Estudio vinculado"
              options={studyOptions}
              placeholder="Sin vincular"
              value={studyId}
              disabled={!isEditable || isBusy}
              onChange={(event) => setStudyId(event.target.value)}
            />
          </div>

          {document.family === 'INFORME' && (
            <p className="text-xs text-muted">
              Al emitir un informe vinculado a un estudio, el resultado se vuelca a ese estudio y
              queda listo para enviarse al paciente por WhatsApp.
            </p>
          )}

          <div className="border-t border-border pt-5">
            <DocumentFieldset
              fields={document.fields}
              values={values}
              disabled={!isEditable || isBusy}
              invalidKeys={invalidKeys}
              onChange={(key, value) => {
                setValues((prev) => ({ ...prev, [key]: value }))
                setInvalidKeys((prev) => prev.filter((item) => item !== key))
              }}
            />
          </div>
        </div>
      )}
    </Modal>
  )
}
