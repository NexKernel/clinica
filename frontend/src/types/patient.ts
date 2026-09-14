export const DOCUMENT_TYPES = ['DNI', 'CE', 'PASAPORTE', 'RUC', 'SIN_DOCUMENTO'] as const
export type DocumentType = (typeof DOCUMENT_TYPES)[number]

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  DNI: 'DNI',
  CE: 'Carné de extranjería',
  PASAPORTE: 'Pasaporte',
  RUC: 'RUC',
  SIN_DOCUMENTO: 'Sin documento',
}

export type Sex = 'M' | 'F'

export interface PatientPayload {
  document_type: DocumentType
  document_number: string | null
  first_name: string
  last_name_paternal: string
  last_name_maternal: string | null
  birth_date: string | null
  sex: Sex | null
  phone: string | null
  whatsapp: string | null
  email: string | null
  address: string | null
  district: string | null
  province: string | null
  department: string | null
  emergency_contact: string | null
  emergency_phone: string | null
  blood_type: string | null
  insurance: string | null
  allergies: string | null
  personal_history: string | null
  family_history: string | null
  surgical_history: string | null
  current_medication: string | null
  notes: string | null
  is_active: boolean
}

export interface Patient extends PatientPayload {
  id: number
  /** Identificador opaco con el que la ficha viaja en la URL. */
  public_id: string
  history_number: string
  full_name: string
  display_name: string
  age: number | null
  sex_label: string | null
  document_label: string
  has_alerts: boolean
  created_at: string
  updated_at: string
}

export interface PatientSummary {
  id: number
  public_id: string
  history_number: string
  full_name: string
  document_type: string
  document_number: string | null
  age: number | null
  sex: string | null
  phone: string | null
  whatsapp: string | null
  has_alerts: boolean
}

export interface PatientFilters {
  search?: string
  is_active?: boolean
  page: number
  page_size: number
}

export interface PatientStats {
  total: number
  active: number
  registered_today: number
  registered_this_month: number
}
