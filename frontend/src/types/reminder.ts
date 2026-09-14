export const REMINDER_KINDS = ['MEDICAMENTO', 'CITA', 'CONTROL', 'RESULTADO'] as const
export type ReminderKind = (typeof REMINDER_KINDS)[number]

export const REMINDER_KIND_LABELS: Record<ReminderKind, string> = {
  MEDICAMENTO: 'Toma de medicamento',
  CITA: 'Recordatorio de cita',
  CONTROL: 'Control médico',
  RESULTADO: 'Entrega de resultado',
}

export const REMINDER_CHANNELS = ['WHATSAPP', 'LLAMADA', 'SMS', 'PRESENCIAL'] as const
export type ReminderChannel = (typeof REMINDER_CHANNELS)[number]

export const REMINDER_CHANNEL_LABELS: Record<ReminderChannel, string> = {
  WHATSAPP: 'WhatsApp',
  LLAMADA: 'Llamada telefónica',
  SMS: 'Mensaje de texto',
  PRESENCIAL: 'Aviso presencial',
}

export const REMINDER_STATUSES = ['PENDIENTE', 'ENVIADO', 'CANCELADO'] as const
export type ReminderStatus = (typeof REMINDER_STATUSES)[number]

export const REMINDER_STATUS_LABELS: Record<ReminderStatus, string> = {
  PENDIENTE: 'Pendiente',
  ENVIADO: 'Enviado',
  CANCELADO: 'Cancelado',
}

export interface ReminderPayload {
  patient_id: number
  kind: ReminderKind
  channel: ReminderChannel
  title: string
  message: string
  scheduled_for: string
  appointment_id: number | null
  encounter_id: number | null
  prescription_id: number | null
  notes: string | null
}

export interface Reminder {
  id: number
  patient_id: number
  patient_name: string
  patient_phone: string | null
  appointment_id: number | null
  encounter_id: number | null
  prescription_id: number | null
  kind: ReminderKind
  kind_label: string
  channel: ReminderChannel
  channel_label: string
  status: ReminderStatus
  status_label: string
  is_pending: boolean
  title: string
  message: string
  scheduled_for: string
  sent_at: string | null
  notes: string | null
  created_at: string
}

export interface ReminderBatch {
  created: number
  items: Reminder[]
}

export interface ReminderStats {
  pending_today: number
  overdue: number
  sent_today: number
  upcoming_week: number
}

export interface WhatsAppMessage {
  reminder_id: number
  phone: string | null
  message: string
  whatsapp_url: string | null
}

export interface ReminderFilters {
  patient_id?: number
  kind?: string
  status?: string
  channel?: string
  date_from?: string
  date_to?: string
  page: number
  page_size: number
}
