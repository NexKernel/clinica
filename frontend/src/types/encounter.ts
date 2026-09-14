import type { PatientSummary } from './patient'

export const DIAGNOSIS_KINDS = ['PRESUNTIVO', 'DEFINITIVO', 'REPETIDO'] as const
export type DiagnosisKind = (typeof DIAGNOSIS_KINDS)[number]

export const DIAGNOSIS_KIND_LABELS: Record<DiagnosisKind, string> = {
  PRESUNTIVO: 'Presuntivo',
  DEFINITIVO: 'Definitivo',
  REPETIDO: 'Repetido',
}

export type EncounterStatus = 'EN_CURSO' | 'FINALIZADA' | 'ANULADA'

export interface DiagnosisPayload {
  code: string | null
  description: string
  kind: DiagnosisKind
}

export interface Diagnosis extends DiagnosisPayload {
  id: number
  kind_label: string
  summary: string
}

export interface PrescriptionPayload {
  product_id: number | null
  medication: string
  dose: string | null
  frequency_hours: number | null
  frequency_text: string | null
  duration_days: number | null
  quantity: number | null
  instructions: string | null
}

export interface Prescription extends PrescriptionPayload {
  id: number
  schedule_label: string
}

export interface VitalSigns {
  systolic_pressure: number | null
  diastolic_pressure: number | null
  heart_rate: number | null
  respiratory_rate: number | null
  temperature: string | null
  oxygen_saturation: number | null
  weight_kg: string | null
  height_cm: string | null
}

export interface EncounterContent extends VitalSigns {
  service_id: number | null
  chief_complaint: string | null
  current_illness: string | null
  physical_exam: string | null
  treatment_plan: string | null
  indications: string | null
  observations: string | null
}

export interface EncounterCreatePayload extends EncounterContent {
  patient_id: number
  practitioner_id: number
  appointment_id: number | null
  started_at?: string | null
  diagnoses: DiagnosisPayload[]
  prescriptions: PrescriptionPayload[]
}

export interface EncounterUpdatePayload extends EncounterContent {
  diagnoses: DiagnosisPayload[] | null
  prescriptions: PrescriptionPayload[] | null
}

export interface Encounter extends EncounterContent {
  id: number
  patient_id: number
  practitioner_id: number
  appointment_id: number | null
  started_at: string
  finished_at: string | null
  status: EncounterStatus
  status_label: string
  is_editable: boolean
  patient_name: string
  practitioner_name: string
  specialty_name: string | null
  blood_pressure: string | null
  bmi: number | null
  main_diagnosis: string | null
  diagnoses: Diagnosis[]
  prescriptions: Prescription[]
  patient: PatientSummary
  created_at: string
}

export interface EncounterListItem {
  id: number
  patient_id: number
  patient_name: string
  practitioner_name: string
  specialty_name: string | null
  started_at: string
  finished_at: string | null
  status: EncounterStatus
  status_label: string
  chief_complaint: string | null
  main_diagnosis: string | null
}

export interface MedicalRecord {
  patient: PatientSummary
  total_encounters: number
  last_encounter_at: string | null
  encounters: EncounterListItem[]
}

export interface EncounterFilters {
  search?: string
  patient_id?: number
  practitioner_id?: number
  status?: string
  day?: string
  date_from?: string
  date_to?: string
  page: number
  page_size: number
}
