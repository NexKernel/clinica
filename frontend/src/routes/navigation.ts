import {
  BarChart3,
  BellRing,
  CalendarDays,
  ClipboardList,
  FileSignature,
  FlaskConical,
  LayoutDashboard,
  Pill,
  Settings,
  Stethoscope,
  Truck,
  UserCircle,
  UserCog,
  Users,
  Wallet,
  type LucideIcon,
} from 'lucide-react'

import { ROUTES, type RoutePath } from '@/routes/paths'
import type { Role } from '@/types'

export interface NavItem {
  key: string
  label: string
  description: string
  path: RoutePath
  icon: LucideIcon
  /** Módulo aún no implementado: se muestra como "Próximamente". */
  comingSoon?: boolean
  /** Roles con acceso. Vacío o ausente = todos los roles autenticados. */
  roles?: Role[]
  /** Se muestra en la barra inferior de mobile. */
  primary?: boolean
  /** No aparece en el menú, pero conserva título y ruta propios. */
  hidden?: boolean
}

/* Los roles de cada módulo replican la matriz de permisos del backend
   (app/core/permissions.py); el servidor sigue siendo la fuente de verdad. */
export const NAV_ITEMS: NavItem[] = [
  {
    key: 'dashboard',
    label: 'Dashboard',
    description: 'Resumen de la atención diaria',
    path: ROUTES.dashboard,
    icon: LayoutDashboard,
    primary: true,
  },
  {
    key: 'patients',
    label: 'Pacientes',
    description: 'Registro, ficha e historia del paciente',
    path: ROUTES.patients,
    icon: Users,
    primary: true,
    roles: ['ADMIN', 'RECEPCION', 'MEDICO', 'ENFERMERIA', 'CAJA', 'LABORATORIO', 'OPTOMETRIA'],
  },
  {
    key: 'appointments',
    label: 'Citas',
    description: 'Agenda, disponibilidad y estados',
    path: ROUTES.appointments,
    icon: CalendarDays,
    primary: true,
    roles: ['ADMIN', 'RECEPCION', 'MEDICO', 'ENFERMERIA', 'CAJA', 'LABORATORIO', 'OPTOMETRIA'],
  },
  {
    key: 'consultations',
    label: 'Atenciones',
    description: 'Consultas, diagnósticos y recetas',
    path: ROUTES.consultations,
    icon: Stethoscope,
    primary: true,
    roles: ['ADMIN', 'MEDICO', 'ENFERMERIA', 'OPTOMETRIA'],
  },
  {
    key: 'medical-records',
    label: 'Historias',
    description: 'Historia clínica consolidada',
    path: ROUTES.medicalRecords,
    icon: ClipboardList,
    roles: ['ADMIN', 'MEDICO', 'ENFERMERIA', 'OPTOMETRIA'],
  },
  {
    key: 'studies',
    label: 'Resultados',
    description: 'Laboratorio, Rayos X y envío al paciente',
    path: ROUTES.studies,
    icon: FlaskConical,
    roles: ['ADMIN', 'RECEPCION', 'MEDICO', 'ENFERMERIA', 'LABORATORIO', 'OPTOMETRIA'],
  },
  {
    key: 'documents',
    label: 'Documentos',
    description: 'Informes, fichas, consentimientos y actas',
    path: ROUTES.documents,
    icon: FileSignature,
    roles: ['ADMIN', 'RECEPCION', 'MEDICO', 'ENFERMERIA', 'LABORATORIO', 'OPTOMETRIA'],
  },
  {
    key: 'reminders',
    label: 'Recordatorios',
    description: 'Avisos de medicación y citas',
    path: ROUTES.reminders,
    icon: BellRing,
    roles: ['ADMIN', 'RECEPCION', 'MEDICO', 'ENFERMERIA'],
  },
  {
    key: 'billing',
    label: 'Caja',
    description: 'Notas de venta y comprobantes',
    path: ROUTES.billing,
    icon: Wallet,
    roles: ['ADMIN', 'CAJA', 'ALMACEN', 'RECEPCION'],
  },
  {
    key: 'pharmacy',
    label: 'Farmacia',
    description: 'Stock, kardex y alertas de reposición',
    path: ROUTES.pharmacy,
    icon: Pill,
    roles: ['ADMIN', 'ALMACEN', 'CAJA', 'MEDICO'],
  },
  {
    key: 'purchases',
    label: 'Compras',
    description: 'Proveedores e ingreso a inventario',
    path: ROUTES.purchases,
    icon: Truck,
    roles: ['ADMIN', 'ALMACEN', 'CAJA'],
  },
  {
    key: 'reports',
    label: 'Reportes',
    description: 'Indicadores y reportes del policlínico',
    path: ROUTES.reports,
    icon: BarChart3,
    roles: ['ADMIN', 'CAJA'],
  },
  {
    key: 'users',
    label: 'Usuarios',
    description: 'Cuentas de acceso y perfiles del personal',
    path: ROUTES.users,
    icon: UserCog,
    roles: ['ADMIN'],
  },
  {
    key: 'profile',
    label: 'Mi perfil',
    description: 'Datos de la cuenta y seguridad',
    path: ROUTES.profile,
    icon: UserCircle,
    hidden: true,
  },
  {
    key: 'settings',
    label: 'Configuración',
    description: 'Parámetros, catálogos y seguridad',
    path: ROUTES.settings,
    icon: Settings,
    roles: ['ADMIN'],
  },
]

/** Elementos visibles en el menú para un rol determinado. */
export function getNavItemsForRole(role: Role | undefined): NavItem[] {
  if (!role) return []
  return NAV_ITEMS.filter((item) => !item.hidden && (!item.roles || item.roles.includes(role)))
}

/** Roles declarados para un módulo del menú, o `undefined` si no los restringe. */
export function rolesForNavItem(key: string): Role[] | undefined {
  return NAV_ITEMS.find((item) => item.key === key)?.roles
}

export function findNavItemByPath(pathname: string): NavItem | undefined {
  return NAV_ITEMS.find((item) => pathname === item.path || pathname.startsWith(`${item.path}/`))
}
