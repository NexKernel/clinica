import type { PatientSummary } from './patient'

export const STUDY_TYPES = ['LABORATORIO', 'RAYOS_X', 'ECOGRAFIA', 'OPTOMETRIA', 'OTRO'] as const
export type StudyType = (typeof STUDY_TYPES)[number]

export const STUDY_TYPE_LABELS: Record<StudyType, string> = {
  LABORATORIO: 'Laboratorio',
  RAYOS_X: 'Rayos X',
  ECOGRAFIA: 'Ecografía',
  OPTOMETRIA: 'Optometría',
  OTRO: 'Otro estudio',
}

export const STUDY_STATUSES = ['SOLICITADO', 'EN_PROCESO', 'COMPLETADO', 'ANULADO'] as const
export type StudyStatus = (typeof STUDY_STATUSES)[number]

export const STUDY_STATUS_LABELS: Record<StudyStatus, string> = {
  SOLICITADO: 'Solicitado',
  EN_PROCESO: 'En proceso',
  COMPLETADO: 'Completado',
  ANULADO: 'Anulado',
}

export interface Attachment {
  id: number
  filename: string
  content_type: string
  size_bytes: number
  size_label: string
  is_image: boolean
  description: string | null
  created_at: string
}

export interface StudyPayload {
  patient_id: number
  encounter_id: number | null
  requested_by_id: number | null
  service_id: number | null
  study_type: StudyType
  name: string
  clinical_notes: string | null
}

export interface StudyResultPayload {
  result_summary: string | null
  report: string | null
  performed_by: string | null
  performed_at: string | null
  complete: boolean
}

export interface Study {
  id: number
  patient_id: number
  encounter_id: number | null
  requested_by_id: number | null
  service_id: number | null
  study_type: StudyType
  type_label: string
  name: string
  status: StudyStatus
  status_label: string
  requested_at: string
  performed_at: string | null
  performed_by: string | null
  clinical_notes: string | null
  result_summary: string | null
  report: string | null
  has_result: boolean
  is_completed: boolean
  attachment_count: number
  shared_at: string | null
  share_expires_at: string | null
  patient_name: string
  requested_by_name: string | null
  attachments: Attachment[]
  patient: PatientSummary
  created_at: string
}

export interface StudyListItem {
  id: number
  patient_id: number
  patient_name: string
  study_type: StudyType
  type_label: string
  name: string
  status: StudyStatus
  status_label: string
  requested_at: string
  performed_at: string | null
  result_summary: string | null
  attachment_count: number
  has_result: boolean
  shared_at: string | null
}

export interface ShareLink {
  study_id: number
  url: string
  whatsapp_url: string | null
  message: string
  expires_at: string
}

export interface SharedAttachment {
  id: number
  filename: string
  content_type: string
  size_label: string
  is_image: boolean
  url: string
}

export interface SharedStudy {
  clinic_name: string
  clinic_logo_url: string | null
  patient_name: string
  study_name: string
  type_label: string
  performed_at: string | null
  result_summary: string | null
  report: string | null
  performed_by: string | null
  attachments: SharedAttachment[]
  expires_at: string
}

export interface StudyFilters {
  search?: string
  patient_id?: number
  study_type?: string
  status?: string
  date_from?: string
  date_to?: string
  page: number
  page_size: number
}
