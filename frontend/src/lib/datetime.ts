/**
 * Horario oficial del sistema: America/Lima.
 * Todo el formateo de fechas pasa por aquí, de modo que el sistema muestre la
 * hora del policlínico aunque el equipo del usuario tenga otra zona horaria.
 */
export const TIME_ZONE = 'America/Lima'
export const LOCALE = 'es-PE'

type DateInput = string | number | Date

const toDate = (value: DateInput): Date => (value instanceof Date ? value : new Date(value))
const isValid = (date: Date): boolean => !Number.isNaN(date.getTime())

const formatter = (options: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat(LOCALE, { timeZone: TIME_ZONE, ...options })

const longDate = formatter({ weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
const shortDate = formatter({ day: 'numeric', month: 'long', year: 'numeric' })
const numericDate = formatter({ day: '2-digit', month: '2-digit', year: 'numeric' })
const timeOnly = formatter({ hour: '2-digit', minute: '2-digit', hour12: false })
const dateAndTime = formatter({
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const safe = (value: DateInput, format: Intl.DateTimeFormat): string => {
  const date = toDate(value)
  return isValid(date) ? format.format(date) : '—'
}

/** "miércoles, 2 de setiembre de 2026" */
export const formatLongDate = (value: DateInput = new Date()): string => safe(value, longDate)

/** "2 de setiembre de 2026" */
export const formatDate = (value: DateInput): string => safe(value, shortDate)

/** "02/09/2026" */
export const formatShortDate = (value: DateInput): string => safe(value, numericDate)

/** "08:30" */
export const formatTime = (value: DateInput): string => safe(value, timeOnly)

/** "02/09/2026 08:30" */
export const formatDateTime = (value: DateInput): string => safe(value, dateAndTime)

/** Hora del día (0-23) en Perú, independiente del reloj del equipo. */
export function peruHour(value: DateInput = new Date()): number {
  const date = toDate(value)
  if (!isValid(date)) return 0
  const hour = new Intl.DateTimeFormat('en-GB', {
    timeZone: TIME_ZONE,
    hour: '2-digit',
    hourCycle: 'h23',
  }).format(date)
  return Number(hour)
}

export function greetingByHour(value: DateInput = new Date()): string {
  const hour = peruHour(value)
  if (hour < 12) return 'Buenos días'
  if (hour < 19) return 'Buenas tardes'
  return 'Buenas noches'
}

/** "2026-09-03" a partir de una fecha, para inputs type="date". */
export function toDateInput(value: DateInput = new Date()): string {
  const date = toDate(value)
  if (!isValid(date)) return ''
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
  return parts
}

/** "2026-09-03T09:00" para inputs type="datetime-local" en hora de Perú. */
export function toDateTimeInput(value: DateInput = new Date()): string {
  const date = toDate(value)
  if (!isValid(date)) return ''
  return `${toDateInput(date)}T${formatTime(date)}`
}

/**
 * Convierte el valor de un input local (hora de Perú) a ISO con desfase
 * explícito, de modo que el servidor reciba el instante correcto.
 */
export function fromDateTimeInput(value: string): string {
  return value ? `${value}:00-05:00` : ''
}

/** Fecha de hoy desplazada en días, en formato de input. */
export function shiftDays(days: number, from: DateInput = new Date()): string {
  const date = toDate(from)
  if (!isValid(date)) return ''
  const shifted = new Date(date.getTime() + days * 24 * 60 * 60 * 1000)
  return toDateInput(shifted)
}
