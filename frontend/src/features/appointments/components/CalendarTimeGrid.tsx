import { useEffect, useMemo, useRef, useState, type MouseEvent } from 'react'

import {
  hueColor,
  localSlot,
  minutesToTime,
  placeOverlapping,
  weekdayLabel,
  type Placed,
} from '@/lib/calendar'
import { toDateInput } from '@/lib/datetime'
import { cn } from '@/lib/utils'
import type { Appointment } from '@/types'

/** Alto de una hora en píxeles: la referencia visual de toda la rejilla. */
const HOUR_HEIGHT = 56
/** Al hacer clic en un hueco, la hora se redondea a este múltiplo. */
const SNAP_MINUTES = 15
/** Franja que se muestra siempre, aunque no haya citas a esas horas. */
const DEFAULT_FROM_HOUR = 7
const DEFAULT_TO_HOUR = 21

interface CalendarTimeGridProps {
  days: string[]
  appointments: Appointment[]
  /** Hueco libre: abre la programación con fecha y hora ya puestas. */
  onSelectSlot: (day: string, time: string) => void
  onSelectAppointment: (appointment: Appointment) => void
}

export function CalendarTimeGrid({
  days,
  appointments,
  onSelectSlot,
  onSelectAppointment,
}: CalendarTimeGridProps) {
  const scroller = useRef<HTMLDivElement>(null)
  const today = toDateInput()
  const nowMinutes = useCurrentMinutes()

  // Cada cita se resuelve una sola vez a su día y minuto en hora de Perú.
  const entries = useMemo(
    () =>
      appointments.map((appointment) => {
        const { day, minutes } = localSlot(appointment.scheduled_at)
        return {
          appointment,
          day,
          start: minutes,
          end: minutes + Math.max(appointment.duration_minutes, 15),
        }
      }),
    [appointments],
  )

  // La franja horaria se estira para que ninguna cita quede fuera de la vista.
  const [fromHour, toHour] = useMemo(() => {
    let from = DEFAULT_FROM_HOUR
    let to = DEFAULT_TO_HOUR
    for (const entry of entries) {
      from = Math.min(from, Math.floor(entry.start / 60))
      to = Math.max(to, Math.ceil(entry.end / 60))
    }
    return [Math.max(0, from), Math.min(24, Math.max(to, from + 1))]
  }, [entries])

  const hours = Array.from({ length: toHour - fromHour }, (_, index) => fromHour + index)
  const offsetOf = (minutes: number) => ((minutes - fromHour * 60) / 60) * HOUR_HEIGHT

  const byDay = useMemo(() => {
    const groups = new Map<string, Placed<Appointment>[]>()
    for (const day of days) {
      const ofDay = entries
        .filter((entry) => entry.day === day)
        .map((entry) => ({ item: entry.appointment, start: entry.start, end: entry.end }))
      groups.set(day, placeOverlapping(ofDay))
    }
    return groups
  }, [days, entries])

  // Al cambiar de período la vista se centra en la hora actual, o en el inicio
  // de la jornada si el período no incluye hoy. Después el usuario manda.
  const periodKey = `${days[0] ?? ''}:${days.length}`
  useEffect(() => {
    const node = scroller.current
    if (!node) return
    const focus = days.includes(today) ? nowMinutes - 90 : DEFAULT_FROM_HOUR * 60
    node.scrollTop = Math.max(0, ((focus - fromHour * 60) / 60) * HOUR_HEIGHT)
  }, [periodKey])

  const handleSlotClick = (day: string, hour: number) => (event: MouseEvent<HTMLElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect()
    const within = ((event.clientY - bounds.top) / bounds.height) * 60
    const minutes = Math.round((hour * 60 + within) / SNAP_MINUTES) * SNAP_MINUTES
    onSelectSlot(day, minutesToTime(minutes))
  }

  return (
    <div
      ref={scroller}
      className="scrollbar-thin h-[calc(100vh-24rem)] min-h-[24rem] overflow-auto"
    >
      <div className="flex min-w-[560px]">
        <div className="sticky left-0 z-30 w-14 shrink-0 bg-surface sm:w-16">
          <div className="sticky top-0 z-40 h-[58px] border-b border-border bg-surface" />
          {hours.map((hour) => (
            <div key={hour} className="relative" style={{ height: HOUR_HEIGHT }} aria-hidden="true">
              {hour > fromHour && (
                <span className="absolute right-2 -top-2 text-[11px] tabular-nums text-muted">
                  {String(hour).padStart(2, '0')}:00
                </span>
              )}
            </div>
          ))}
        </div>

        {days.map((day) => (
          <div key={day} className="flex-1 border-l border-border">
            <DayHeading day={day} isToday={day === today} single={days.length === 1} />

            <div
              className={cn('relative', day === today && 'bg-primary/[0.03]')}
              style={{ height: hours.length * HOUR_HEIGHT }}
            >
              {hours.map((hour) => (
                <button
                  key={hour}
                  type="button"
                  onClick={handleSlotClick(day, hour)}
                  aria-label={`Programar cita el ${day} a las ${String(hour).padStart(2, '0')}:00`}
                  className="block w-full border-b border-border/70 transition-colors hover:bg-primary/[0.06]"
                  style={{ height: HOUR_HEIGHT }}
                >
                  <span className="block h-1/2 border-b border-border/40" aria-hidden="true" />
                </button>
              ))}

              {(byDay.get(day) ?? []).map((placed) => (
                <AppointmentBlock
                  key={placed.item.id}
                  placed={placed}
                  top={offsetOf(placed.start)}
                  height={Math.max(((placed.end - placed.start) / 60) * HOUR_HEIGHT - 2, 20)}
                  onSelect={onSelectAppointment}
                />
              ))}

              {day === today && nowMinutes >= fromHour * 60 && nowMinutes <= toHour * 60 && (
                <div
                  className="pointer-events-none absolute inset-x-0 z-20 flex items-center"
                  style={{ top: offsetOf(nowMinutes) }}
                  aria-hidden="true"
                >
                  <span className="-ml-1 h-2 w-2 rounded-full bg-danger" />
                  <span className="h-px flex-1 bg-danger" />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

interface DayHeadingProps {
  day: string
  isToday: boolean
  single: boolean
}

function DayHeading({ day, isToday, single }: DayHeadingProps) {
  return (
    <div className="sticky top-0 z-30 h-[58px] border-b border-border bg-surface px-1 py-2 text-center">
      <p className="text-[11px] uppercase tracking-wide text-muted">{weekdayLabel(day)}</p>
      <p
        className={cn(
          'mx-auto mt-0.5 flex h-7 items-center justify-center rounded-full text-base font-semibold tabular-nums',
          single ? 'w-auto px-3' : 'w-7',
          isToday ? 'bg-primary text-white' : 'text-foreground',
        )}
      >
        {Number(day.slice(8, 10))}
      </p>
    </div>
  )
}

interface AppointmentBlockProps {
  placed: Placed<Appointment>
  top: number
  height: number
  onSelect: (appointment: Appointment) => void
}

function AppointmentBlock({ placed, top, height, onSelect }: AppointmentBlockProps) {
  const appointment = placed.item
  const closed = appointment.status === 'CANCELADA' || appointment.status === 'NO_ASISTIO'
  const hue = hueColor(appointment.practitioner_id)
  const width = 100 / placed.lanes
  // Una cita de 20 o 30 minutos no da para dos líneas: se resume en una sola,
  // con la hora delante, como hace cualquier agenda.
  const compact = height < 34

  return (
    <button
      type="button"
      onClick={() => onSelect(appointment)}
      title={`${minutesToTime(placed.start)} · ${appointment.patient_name} · ${appointment.practitioner_name}`}
      className={cn(
        'absolute z-10 overflow-hidden rounded-lg border-l-[3px] px-1.5 py-1 text-left transition-shadow',
        'hover:z-20 hover:shadow-popover focus-visible:z-20',
        closed && 'opacity-60',
      )}
      style={{
        top,
        height,
        left: `calc(${placed.lane * width}% + 2px)`,
        width: `calc(${width}% - 4px)`,
        backgroundColor: hueColor(appointment.practitioner_id, 0.14),
        borderColor: hue,
        color: hue,
      }}
    >
      <span
        className={cn(
          'block truncate text-[11px] font-semibold leading-tight',
          closed && 'line-through',
        )}
      >
        {compact && (
          <span className="mr-1 font-normal tabular-nums opacity-80">
            {minutesToTime(placed.start)}
          </span>
        )}
        {appointment.patient_name}
        {compact && (
          <span className="ml-1.5 font-normal opacity-70">· {appointment.practitioner_name}</span>
        )}
      </span>
      {!compact && (
        <span className="block truncate text-[10px] leading-tight opacity-80">
          {minutesToTime(placed.start)} · {appointment.practitioner_name}
        </span>
      )}
    </button>
  )
}

/** Minutos transcurridos hoy en hora de Perú, refrescados cada minuto. */
function useCurrentMinutes(): number {
  const read = () => localSlot(new Date().toISOString()).minutes
  const [minutes, setMinutes] = useState(read)

  useEffect(() => {
    const timer = setInterval(() => setMinutes(read()), 60_000)
    return () => clearInterval(timer)
  }, [])

  return minutes
}
