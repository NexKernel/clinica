/**
 * Aritmética de calendario para la agenda.
 *
 * Los días se manejan como cadenas `YYYY-MM-DD` y las operaciones se hacen en
 * UTC a medianoche: así sumar días nunca se ve afectado por husos ni horarios
 * de verano. La conversión entre un instante del servidor y el día/minuto que
 * le corresponde en la agenda pasa siempre por la zona horaria del sistema
 * (America/Lima), no por el reloj del equipo.
 */

import { LOCALE, TIME_ZONE } from '@/lib/datetime'

const MINUTES_IN_DAY = 24 * 60

const MS_PER_DAY = 24 * 60 * 60 * 1000

const partsFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: TIME_ZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

const weekdayFormatter = new Intl.DateTimeFormat(LOCALE, {
  timeZone: 'UTC',
  weekday: 'short',
})

const monthTitleFormatter = new Intl.DateTimeFormat(LOCALE, {
  timeZone: 'UTC',
  month: 'long',
  year: 'numeric',
})

const dayTitleFormatter = new Intl.DateTimeFormat(LOCALE, {
  timeZone: 'UTC',
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})

const rangeFormatter = new Intl.DateTimeFormat(LOCALE, {
  timeZone: 'UTC',
  day: 'numeric',
  month: 'short',
})

/** Medianoche UTC del día indicado, usada como base de todos los cálculos. */
function epochOf(day: string): number {
  const [year = 1970, month = 1, date = 1] = day.split('-').map(Number)
  return Date.UTC(year, month - 1, date)
}

const dayOf = (epoch: number): string => new Date(epoch).toISOString().slice(0, 10)

export const addDays = (day: string, amount: number): string =>
  dayOf(epochOf(day) + amount * MS_PER_DAY)

export const addMonths = (day: string, amount: number): string => {
  const [year = 1970, month = 1] = day.split('-').map(Number)
  return dayOf(Date.UTC(year, month - 1 + amount, 1))
}

/** Lunes de la semana del día indicado: la semana laboral empieza el lunes. */
function startOfWeek(day: string): string {
  const weekday = new Date(epochOf(day)).getUTCDay()
  return addDays(day, -((weekday + 6) % 7))
}

const startOfMonth = (day: string): string => `${day.slice(0, 7)}-01`

/** Los siete días de la semana a la que pertenece `day`. */
export const weekDays = (day: string): string[] =>
  Array.from({ length: 7 }, (_, index) => addDays(startOfWeek(day), index))

/** Rejilla de seis semanas que cubre el mes completo, como la de Google Calendar. */
export const monthGrid = (day: string): string[] => {
  const first = startOfWeek(startOfMonth(day))
  return Array.from({ length: 42 }, (_, index) => addDays(first, index))
}

export const isSameMonth = (day: string, reference: string): boolean =>
  day.slice(0, 7) === reference.slice(0, 7)

export const dayNumber = (day: string): number => Number(day.slice(8, 10))

/** "lun", "mar"… en español, sin depender del huso del navegador. */
export const weekdayLabel = (day: string): string =>
  weekdayFormatter.format(new Date(epochOf(day))).replace('.', '')

/** Día y minuto del día que le corresponde a un instante en hora de Perú. */
export function localSlot(value: string): { day: string; minutes: number } {
  const parts = partsFormatter.formatToParts(new Date(value))
  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? '00'
  return {
    day: `${get('year')}-${get('month')}-${get('day')}`,
    minutes: Number(get('hour')) * 60 + Number(get('minute')),
  }
}

/** "08:30" a partir de los minutos transcurridos desde la medianoche. */
export const minutesToTime = (minutes: number): string => {
  const clamped = Math.max(0, Math.min(MINUTES_IN_DAY - 1, Math.round(minutes)))
  return `${String(Math.floor(clamped / 60)).padStart(2, '0')}:${String(clamped % 60).padStart(2, '0')}`
}

/* En español solo va en mayúscula la primera letra: «Setiembre de 2026», no
   «Setiembre De 2026», que es lo que haría un `capitalize` de CSS. */
const upperFirst = (text: string): string => text.charAt(0).toUpperCase() + text.slice(1)

/** Título del período que se está mirando. */
export function periodLabel(view: 'day' | 'week' | 'month', day: string): string {
  if (view === 'day') return upperFirst(dayTitleFormatter.format(new Date(epochOf(day))))
  if (view === 'month') return upperFirst(monthTitleFormatter.format(new Date(epochOf(day))))

  const days = weekDays(day)
  const first = days[0] as string
  const last = days[6] as string
  return upperFirst(
    `${rangeFormatter.format(new Date(epochOf(first)))} – ` +
      `${rangeFormatter.format(new Date(epochOf(last)))} de ${last.slice(0, 4)}`,
  )
}

/* --- Disposición de citas superpuestas ----------------------------------- */

export interface TimeRange {
  start: number
  end: number
}

export interface Placed<T> extends TimeRange {
  item: T
  /** Columna que ocupa dentro de su grupo de citas superpuestas. */
  lane: number
  /** Columnas que tiene ese grupo: define el ancho de cada bloque. */
  lanes: number
}

/**
 * Reparte en columnas las citas que se pisan en el tiempo.
 *
 * Se recorren en orden de inicio acumulando un grupo: mientras una cita empiece
 * antes de que termine la última del grupo, comparte espacio con él y se le
 * asigna la primera columna libre. Al cerrarse el grupo, todas sus citas
 * reciben el mismo número de columnas para que queden alineadas.
 */
export function placeOverlapping<T>(entries: (TimeRange & { item: T })[]): Placed<T>[] {
  const ordered = [...entries].sort((a, b) => a.start - b.start || b.end - a.end)
  const placed: Placed<T>[] = []

  let group: Placed<T>[] = []
  let groupEnd = -1

  const closeGroup = () => {
    const lanes = group.reduce((total, entry) => Math.max(total, entry.lane + 1), 1)
    for (const entry of group) entry.lanes = lanes
    placed.push(...group)
    group = []
    groupEnd = -1
  }

  for (const entry of ordered) {
    if (group.length > 0 && entry.start >= groupEnd) closeGroup()

    const taken = new Set(
      group.filter((other) => other.end > entry.start).map((other) => other.lane),
    )
    let lane = 0
    while (taken.has(lane)) lane += 1

    group.push({ ...entry, lane, lanes: 1 })
    groupEnd = Math.max(groupEnd, entry.end)
  }

  if (group.length > 0) closeGroup()
  return placed
}

/* --- Colores por profesional --------------------------------------------- */

/** Tantos tonos como define `index.css`; se repiten si hay más profesionales. */
const CALENDAR_HUES = 6

/** Tono estable para un profesional: no cambia al filtrar ni al recargar. */
const hueOf = (practitionerId: number): number => (Math.abs(practitionerId) % CALENDAR_HUES) + 1

export const hueColor = (practitionerId: number, alpha = 1): string =>
  `rgb(var(--cal-${hueOf(practitionerId)}) / ${alpha})`
