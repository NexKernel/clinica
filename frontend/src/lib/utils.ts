import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

import { LOCALE } from '@/lib/datetime'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function getInitials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '??'
  const first = parts[0]?.charAt(0) ?? ''
  const second = parts.length > 1 ? (parts[1]?.charAt(0) ?? '') : (parts[0]?.charAt(1) ?? '')
  return (first + second).toUpperCase()
}

/** Importe redondeado, para tarjetas de indicadores: "S/ 1,480". */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat(LOCALE, {
    style: 'currency',
    currency: 'PEN',
    minimumFractionDigits: 0,
  }).format(value)
}

/** Importe exacto de caja y comprobantes: "S/ 38.00". */
export function formatMoney(value: number | string | null | undefined): string {
  const amount = typeof value === 'string' ? Number(value) : (value ?? 0)
  return new Intl.NumberFormat(LOCALE, {
    style: 'currency',
    currency: 'PEN',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(amount) ? amount : 0)
}

/** Tasa como porcentaje legible: 0.18 -> "18 %", 0.105 -> "10.5 %". */
export function formatPercent(rate: number): string {
  const percent = rate * 100
  return `${Number.isInteger(percent) ? percent : percent.toFixed(2).replace(/\.?0+$/, '')} %`
}

/** Variación porcentual entre dos periodos, lista para StatCard. */
export function trendBetween(
  current: number,
  previous: number,
): { value: string; direction: 'up' | 'down' } | undefined {
  if (!previous) return undefined
  const change = ((current - previous) / previous) * 100
  if (!Number.isFinite(change) || Math.abs(change) < 0.5) return undefined
  return {
    value: `${change > 0 ? '+' : ''}${change.toFixed(0)}%`,
    direction: change >= 0 ? 'up' : 'down',
  }
}
