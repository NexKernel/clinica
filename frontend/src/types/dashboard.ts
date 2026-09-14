import type { Appointment } from './appointment'
import type { LowStockItem } from './inventory'

export interface DashboardTotals {
  appointments_today: number
  appointments_yesterday: number
  attended_today: number
  pending_today: number
  /** null para los perfiles sin acceso de consulta al módulo de ventas. */
  revenue_today: number | null
  revenue_yesterday: number | null
  patients_total: number
  patients_new_today: number
}

export interface SeriesPoint {
  day: string
  label: string
  value: number
}

export interface StatusSlice {
  status: string
  label: string
  value: number
}

export interface OperationAlerts {
  low_stock: number
  expiring_soon: number
  expired: number
  pending_studies: number
  pending_reminders: number
  draft_purchases: number
}

export interface DashboardSummary {
  day: string
  totals: DashboardTotals
  attentions_series: SeriesPoint[]
  revenue_series: SeriesPoint[]
  appointment_status: StatusSlice[]
  alerts: OperationAlerts
  upcoming_appointments: Appointment[]
  restock_items: LowStockItem[]
}
