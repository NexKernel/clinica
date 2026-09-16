import type { LucideIcon } from 'lucide-react'
import { CalendarDays, ClipboardList, FileSignature, FlaskConical, Printer } from 'lucide-react'
import type { ReactNode } from 'react'

import {
  Badge,
  Button,
  DataSummary,
  EmptyState,
  LoadingState,
  type BadgeVariant,
} from '@/components/ui'
import { formatDate, formatDateTime } from '@/lib/datetime'
import type {
  Appointment,
  DocumentListItem,
  DocumentStatus,
  EncounterListItem,
  Patient,
  StudyListItem,
} from '@/types'

const DOCUMENT_VARIANT: Record<DocumentStatus, BadgeVariant> = {
  BORRADOR: 'warning',
  EMITIDO: 'success',
  ANULADO: 'danger',
}

interface RecordListProps<T> {
  items: T[]
  isLoading: boolean
  /** Resumen: recorta la lista; la sección completa la muestra entera. */
  limit?: number
  loadingLabel: string
  emptyIcon: LucideIcon
  emptyTitle: string
  emptyDescription: string
  keyOf: (item: T) => number
  render: (item: T) => ReactNode
}

/* Las cuatro áreas clínicas de la ficha se leen igual: una lista de registros
   con su estado a la derecha. La diferencia está sólo en cada fila. */
function RecordList<T>({
  items,
  isLoading,
  limit,
  loadingLabel,
  emptyIcon,
  emptyTitle,
  emptyDescription,
  keyOf,
  render,
}: RecordListProps<T>) {
  if (isLoading) return <LoadingState label={loadingLabel} className="py-8" />

  if (items.length === 0) {
    return (
      <EmptyState
        icon={emptyIcon}
        title={emptyTitle}
        description={emptyDescription}
        className="py-8"
      />
    )
  }

  const visible = limit ? items.slice(0, limit) : items

  return (
    <ul className="divide-y divide-border">
      {visible.map((item) => (
        <li key={keyOf(item)} className="py-3 first:pt-0 last:pb-0">
          {render(item)}
        </li>
      ))}
    </ul>
  )
}

/** Datos de filiación y contacto. */
export function PatientProfilePanel({ patient }: { patient: Patient }) {
  return (
    <DataSummary
      columns={2}
      items={[
        { label: 'Historia', value: patient.history_number },
        { label: 'Documento', value: patient.document_label },
        { label: 'Edad', value: patient.age !== null ? `${patient.age} años` : null },
        { label: 'Sexo', value: patient.sex_label },
        {
          label: 'Nacimiento',
          value: patient.birth_date ? formatDate(patient.birth_date) : null,
        },
        { label: 'Lugar de nacimiento', value: patient.birth_place },
        { label: 'Estado civil', value: patient.marital_status },
        { label: 'Ocupación', value: patient.occupation },
        { label: 'Grupo sanguíneo', value: patient.blood_type },
        { label: 'Teléfono', value: patient.phone },
        { label: 'WhatsApp', value: patient.whatsapp },
        { label: 'Correo', value: patient.email, span: true },
        { label: 'Seguro', value: patient.insurance },
        {
          label: 'Estado',
          value: (
            <Badge variant={patient.is_active ? 'success' : 'neutral'} dot>
              {patient.is_active ? 'Activo' : 'Inactivo'}
            </Badge>
          ),
        },
        {
          label: 'Dirección',
          value: [patient.address, patient.district, patient.province, patient.department]
            .filter(Boolean)
            .join(', '),
          span: true,
        },
        {
          label: 'Contacto de emergencia',
          value: [patient.emergency_contact, patient.emergency_phone].filter(Boolean).join(' · '),
          span: true,
        },
      ]}
    />
  )
}

/** Antecedentes y observaciones registrados en la ficha. */
export function PatientHistoryPanel({ patient }: { patient: Patient }) {
  return (
    <DataSummary
      columns={2}
      items={[
        { label: 'Antecedentes personales', value: patient.personal_history },
        { label: 'Antecedentes familiares', value: patient.family_history },
        { label: 'Antecedentes quirúrgicos', value: patient.surgical_history },
        { label: 'Alergias', value: patient.allergies },
        { label: 'Medicación actual', value: patient.current_medication },
        { label: 'Observaciones', value: patient.notes },
      ]}
    />
  )
}

interface PanelProps {
  isLoading: boolean
  limit?: number
}

export function PatientAppointmentsPanel({
  appointments,
  isLoading,
  limit,
}: PanelProps & { appointments: Appointment[] }) {
  return (
    <RecordList
      items={appointments}
      isLoading={isLoading}
      limit={limit}
      loadingLabel="Cargando citas"
      emptyIcon={CalendarDays}
      emptyTitle="Sin citas registradas"
      emptyDescription="Las citas programadas del paciente aparecerán aquí."
      keyOf={(appointment) => appointment.id}
      render={(appointment) => (
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground">
              {formatDateTime(appointment.scheduled_at)}
            </p>
            <p className="truncate text-xs text-muted">
              {appointment.practitioner_name}
              {appointment.specialty_name ? ` · ${appointment.specialty_name}` : ''}
            </p>
          </div>
          <Badge variant="info" dot>
            {appointment.status_label}
          </Badge>
        </div>
      )}
    />
  )
}

export function PatientEncountersPanel({
  encounters,
  isLoading,
  limit,
}: PanelProps & { encounters: EncounterListItem[] }) {
  return (
    <RecordList
      items={encounters}
      isLoading={isLoading}
      limit={limit}
      loadingLabel="Cargando historia clínica"
      emptyIcon={ClipboardList}
      emptyTitle="Sin atenciones registradas"
      emptyDescription="La historia clínica se construye con cada atención médica."
      keyOf={(encounter) => encounter.id}
      render={(encounter) => (
        <>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground">
                {formatDateTime(encounter.started_at)}
              </p>
              <p className="truncate text-xs text-muted">
                {encounter.practitioner_name}
                {encounter.specialty_name ? ` · ${encounter.specialty_name}` : ''}
              </p>
            </div>
            <Badge variant={encounter.status === 'FINALIZADA' ? 'success' : 'warning'} dot>
              {encounter.status_label}
            </Badge>
          </div>
          {encounter.main_diagnosis && (
            <p className="mt-1.5 text-sm text-foreground">{encounter.main_diagnosis}</p>
          )}
        </>
      )}
    />
  )
}

export function PatientStudiesPanel({
  studies,
  isLoading,
  limit,
}: PanelProps & { studies: StudyListItem[] }) {
  return (
    <RecordList
      items={studies}
      isLoading={isLoading}
      limit={limit}
      loadingLabel="Cargando resultados"
      emptyIcon={FlaskConical}
      emptyTitle="Sin estudios registrados"
      emptyDescription="Los exámenes y estudios de imagen aparecerán aquí."
      keyOf={(study) => study.id}
      render={(study) => (
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-foreground">{study.name}</p>
            <p className="truncate text-xs text-muted">
              {study.type_label} · {formatDate(study.requested_at)}
              {study.attachment_count > 0 ? ` · ${study.attachment_count} archivo(s)` : ''}
            </p>
          </div>
          <Badge variant={study.status === 'COMPLETADO' ? 'success' : 'warning'} dot>
            {study.status_label}
          </Badge>
        </div>
      )}
    />
  )
}

export function PatientDocumentsPanel({
  documents,
  isLoading,
  limit,
  onPrint,
}: PanelProps & { documents: DocumentListItem[]; onPrint: (documentId: number) => void }) {
  return (
    <RecordList
      items={documents}
      isLoading={isLoading}
      limit={limit}
      loadingLabel="Cargando documentos"
      emptyIcon={FileSignature}
      emptyTitle="Sin documentos emitidos"
      emptyDescription="Los informes, fichas y consentimientos del paciente aparecerán aquí."
      keyOf={(document) => document.id}
      render={(document) => (
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-foreground">{document.title}</p>
            <p className="truncate text-xs text-muted">
              {document.number} · {formatDate(document.issued_at ?? document.created_at)}
              {document.practitioner_name ? ` · ${document.practitioner_name}` : ''}
            </p>
          </div>
          <Badge variant={DOCUMENT_VARIANT[document.status]} dot>
            {document.status_label}
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            aria-label={`Imprimir ${document.number}`}
            onClick={() => onPrint(document.id)}
          >
            <Printer className="h-4 w-4" />
          </Button>
        </div>
      )}
    />
  )
}
