import type { PatientSummary } from './patient'

export const APPOINTMENT_STATUSES = [
  'PROGRAMADA',
  'CONFIRMADA',
  'EN_ATENCION',
  'ATENDIDA',
  'CANCELADA',
  'NO_ASISTIO',
] as const

export type AppointmentStatus = (typeof APPOINTMENT_STATUSES)[number]

export const APPOINTMENT_STATUS_LABELS: Record<AppointmentStatus, string> = {
  PROGRAMADA: 'Programada',
  CONFIRMADA: 'Confirmada',
  EN_ATENCION: 'En atención',
  ATENDIDA: 'Atendida',
  CANCELADA: 'Cancelada',
  NO_ASISTIO: 'No asistió',
}

export interface AppointmentPayload {
  patient_id: number
  practitioner_id: number
  service_id: number | null
  scheduled_at: string
  duration_minutes: number | null
  reason: string | null
  notes: string | null
}

export interface Appointment {
  id: number
  patient_id: number
  practitioner_id: number
  service_id: number | null
  scheduled_at: string
  duration_minutes: number
  status: AppointmentStatus
  status_label: string
  reason: string | null
  notes: string | null
  cancel_reason: string | null
  is_closed: boolean
  patient_name: string
  practitioner_name: string
  specialty_name: string | null
  service_name: string | null
  patient: PatientSummary
  created_at: string
}

export interface AppointmentSlot {
  start: string
  end: string
  available: boolean
  appointment_id: number | null
  patient_name: string | null
  status: AppointmentStatus | null
}

export interface DayAvailability {
  practitioner_id: number
  practitioner_name: string
  day: string
  slot_minutes: number
  working: boolean
  slots: AppointmentSlot[]
}

export interface AgendaSummary {
  day: string
  total: number
  scheduled: number
  attended: number
  cancelled: number
  no_show: number
}

export interface AppointmentFilters {
  search?: string
  practitioner_id?: number
  patient_id?: number
  status?: string
  day?: string
  date_from?: string
  date_to?: string
  page: number
  page_size: number
}
