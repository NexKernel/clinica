import type { PatientSummary } from './patient'
import type { StudyType } from './study'

export const DOCUMENT_FAMILIES = ['INFORME', 'FICHA', 'CONSENTIMIENTO', 'ADMINISTRATIVO'] as const
export type DocumentFamily = (typeof DOCUMENT_FAMILIES)[number]

export const DOCUMENT_FAMILY_LABELS: Record<DocumentFamily, string> = {
  INFORME: 'Informe de resultado',
  FICHA: 'Ficha clínica',
  CONSENTIMIENTO: 'Consentimiento y declaración',
  ADMINISTRATIVO: 'Documento administrativo',
}

export const DOCUMENT_STATUSES = ['BORRADOR', 'EMITIDO', 'ANULADO'] as const
export type DocumentStatus = (typeof DOCUMENT_STATUSES)[number]

export const DOCUMENT_STATUS_LABELS: Record<DocumentStatus, string> = {
  BORRADOR: 'Borrador',
  EMITIDO: 'Emitido',
  ANULADO: 'Anulado',
}

/** Controles que sabe dibujar el formulario dinámico. */
const TEMPLATE_FIELD_TYPES = [
  'text',
  'textarea',
  'number',
  'date',
  'select',
  'boolean',
  'computed',
  'odontograma',
] as const
export type TemplateFieldType = (typeof TEMPLATE_FIELD_TYPES)[number]

export interface TemplateOption {
  value: string
  label: string
}

/** Definición de un campo editable, tal como la publica la plantilla. */
export interface TemplateField {
  key: string
  label: string
  type: TemplateFieldType
  group: string | null
  default: string | number | boolean | null
  placeholder: string | null
  help: string | null
  options: TemplateOption[] | null
  /** Sólo en `computed`: claves cuyos valores se suman para obtener el puntaje. */
  sum: string[] | null
  required: boolean
  /** Ocupa el ancho completo de la fila del formulario. */
  wide: boolean
}

export interface DocumentTemplateSummary {
  id: number
  code: string
  version: number
  family: DocumentFamily
  family_label: string
  title: string
  description: string | null
  requires_signature: boolean
  study_type: StudyType | null
  field_count: number
}

/** Datos capturados. Las claves son las de `TemplateField`. */
/** El odontograma guarda un objeto por pieza; el resto de campos, escalares. */
export type DocumentData = Record<string, string | number | boolean | null | object>

export interface DocumentPayload {
  patient_id: number
  encounter_id: number | null
  study_id: number | null
  practitioner_id: number | null
  data: DocumentData
}

export interface DocumentCreatePayload extends DocumentPayload {
  template_code: string
}

export interface DocumentListItem {
  id: number
  number: string
  patient_id: number
  patient_name: string
  template_code: string
  template_version: number
  family: DocumentFamily
  family_label: string
  title: string
  status: DocumentStatus
  status_label: string
  practitioner_name: string | null
  study_id: number | null
  encounter_id: number | null
  issued_at: string | null
  created_at: string
}

export interface ClinicalDocument extends DocumentListItem {
  template_id: number
  practitioner_id: number | null
  data: DocumentData
  void_reason: string | null
  voided_at: string | null
  is_draft: boolean
  is_issued: boolean
  patient: PatientSummary
  /** Campos de la versión con la que se llenó, no de la vigente. */
  fields: TemplateField[]
}

/** Hoja lista para mostrar o imprimir. */
export interface DocumentSheet {
  id: number
  number: string
  title: string
  status: DocumentStatus
  is_issued: boolean
  html: string
}

export interface DocumentFilters {
  search?: string
  patient_id?: number
  family?: string
  status?: string
  template_code?: string
  date_from?: string
  date_to?: string
  page: number
  page_size: number
}
