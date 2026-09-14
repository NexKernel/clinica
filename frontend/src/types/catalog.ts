export const SERVICE_KINDS = ['CONSULTA', 'PROCEDIMIENTO', 'LABORATORIO', 'IMAGENES', 'OTRO'] as const
export type ServiceKind = (typeof SERVICE_KINDS)[number]

export const SERVICE_KIND_LABELS: Record<ServiceKind, string> = {
  CONSULTA: 'Consulta',
  PROCEDIMIENTO: 'Procedimiento',
  LABORATORIO: 'Laboratorio',
  IMAGENES: 'Imágenes / Rayos X',
  OTRO: 'Otro',
}

export interface SpecialtyPayload {
  name: string
  description: string | null
  default_duration_minutes: number
  is_active: boolean
}

export interface Specialty extends SpecialtyPayload {
  id: number
}

export interface MedicalServicePayload {
  code: string
  name: string
  kind: ServiceKind
  specialty_id: number | null
  price: string
  duration_minutes: number
  is_active: boolean
}

export interface MedicalService extends MedicalServicePayload {
  id: number
  specialty_name: string | null
  kind_label: string
}
