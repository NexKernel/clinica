/** Estados de una casilla del carné, tal como los calcula el servidor. */
export const CRED_STATUSES = ['APLICADA', 'PENDIENTE', 'ATRASADA', 'FUTURA'] as const
export type CredStatus = (typeof CRED_STATUSES)[number]

export const CRED_KINDS = [
  'VACUNA',
  'CONTROL',
  'TAMIZAJE',
  'SUPLEMENTO',
  'PRESTACION',
] as const
export type CredKind = (typeof CRED_KINDS)[number]

export interface CredEntry {
  id: number
  patient_id: number
  item_code: string
  sequence: number
  performed_on: string
  result: string | null
  notes: string | null
  practitioner_id: number | null
  practitioner_name: string | null
  created_at: string
}

/** Una casilla: lo que toca a esa edad y, si ya se dio, cuándo. */
export interface CredSlot {
  item_code: string
  group: string
  label: string
  dose: string
  due_month: number | null
  status: CredStatus
  status_label: string
  records_result: boolean
  entries: CredEntry[]
}

export interface CredSection {
  kind: CredKind
  label: string
  slots: CredSlot[]
  applied: number
  overdue: number
}

export interface CredCard {
  patient: {
    id: number
    public_id: string
    history_number: string
    full_name: string
    age: number | null
    sex: string | null
  }
  age_months: number | null
  age_label: string
  in_program: boolean
  sections: CredSection[]
  applied: number
  overdue: number
  pending: number
}

export interface CredCatalogItem {
  code: string
  kind: CredKind
  kind_label: string
  group: string
  label: string
  dose: string
  due_month: number | null
  records_result: boolean
  repeatable: boolean
  already_applied: boolean
}

export interface CredSheet {
  title: string
  number: string
  html: string
}

export interface CredEntryPayload {
  item_code: string
  performed_on: string
  result: string | null
  notes: string | null
  practitioner_id: number | null
}

export interface CredEntryCreatePayload extends CredEntryPayload {
  patient_id: number
}
