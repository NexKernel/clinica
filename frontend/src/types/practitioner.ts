export const WEEKDAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'] as const

export interface SchedulePayload {
  weekday: number
  start_time: string
  end_time: string
  is_active: boolean
}

export interface Schedule extends SchedulePayload {
  id: number
  weekday_label: string
}

export interface PractitionerPayload {
  full_name: string
  specialty_id: number | null
  user_id: number | null
  license_number: string | null
  document_number: string | null
  phone: string | null
  email: string | null
  slot_minutes: number
  is_active: boolean
  schedules?: SchedulePayload[]
}

export interface Practitioner extends Omit<PractitionerPayload, 'schedules'> {
  id: number
  specialty_name: string | null
  display_name: string
  schedules: Schedule[]
}

export interface PractitionerSummary {
  id: number
  full_name: string
  specialty_name: string | null
  slot_minutes: number
  is_active: boolean
}
