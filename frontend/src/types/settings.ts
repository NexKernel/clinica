export interface ClinicSettingsPayload {
  name: string
  short_name: string
  tagline: string | null
  legal_name: string | null
  tax_id: string | null
  address: string | null
  district: string | null
  province: string | null
  department: string | null
  phone: string | null
  whatsapp: string | null
  email: string | null
  website: string | null
  health_facility_code: string | null
  medical_director: string | null
  category: string | null
  /** Pie de página de los documentos impresos. */
  document_footer: string | null
  opening_hours: string | null
  appointment_slot_minutes: number
  currency: string
  tax_rate: number
  invoice_series: string | null
  receipt_series: string | null
}

export interface ClinicSettings extends ClinicSettingsPayload {
  id: number
  logo_url: string | null
  location: string | null
  updated_at: string
}

export interface PublicBranding {
  name: string
  short_name: string
  tagline: string | null
  location: string | null
  address: string | null
  phone: string | null
  logo_url: string | null
}
