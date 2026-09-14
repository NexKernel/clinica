export const ROUTES = {
  login: '/login',
  dashboard: '/dashboard',
  patients: '/pacientes',
  patientDetail: '/pacientes/:patientId',
  appointments: '/citas',
  consultations: '/consultas',
  medicalRecords: '/historias-clinicas',
  studies: '/estudios',
  documents: '/documentos',
  reminders: '/recordatorios',
  billing: '/caja',
  pharmacy: '/farmacia',
  purchases: '/compras',
  reports: '/reportes',
  users: '/usuarios',
  profile: '/perfil',
  settings: '/configuracion',
} as const

export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES]

/** Ficha del paciente a pantalla completa; se direcciona por `public_id`
 *  para no exponer el correlativo interno en la barra de direcciones. */
export const patientDetailPath = (publicId: string): string =>
  ROUTES.patientDetail.replace(':patientId', publicId)

/** Consulta pública del resultado enviada al paciente por WhatsApp. */
export const SHARED_RESULT_PATH = '/resultados/:token'
