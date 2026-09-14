import { useMemo } from 'react'

import { dayNumber, hueColor, isSameMonth, localSlot, weekdayLabel } from '@/lib/calendar'
import { toDateInput } from '@/lib/datetime'
import { cn } from '@/lib/utils'
import type { Appointment } from '@/types'

/** Citas que caben en una celda antes de resumir el resto en «+N». */
const VISIBLE_PER_DAY = 3

interface CalendarMonthGridProps {
  /** Las 42 celdas de la rejilla, de lunes a domingo. */
  days: string[]
  /** Día de referencia: distingue el mes en curso de los días de relleno. */
  reference: string
  appointments: Appointment[]
  onSelectDay: (day: string) => void
  onSelectAppointment: (appointment: Appointment) => void
}

export function CalendarMonthGrid({
  days,
  reference,
  appointments,
  onSelectDay,
  onSelectAppointment,
}: CalendarMonthGridProps) {
  const today = toDateInput()

  const byDay = useMemo(() => {
    const groups = new Map<string, { appointment: Appointment; minutes: number }[]>()
    for (const appointment of appointments) {
      const { day, minutes } = localSlot(appointment.scheduled_at)
      const bucket = groups.get(day)
      if (bucket) bucket.push({ appointment, minutes })
      else groups.set(day, [{ appointment, minutes }])
    }
    for (const bucket of groups.values()) bucket.sort((a, b) => a.minutes - b.minutes)
    return groups
  }, [appointments])

  return (
    <div className="overflow-hidden">
      <div className="grid grid-cols-7 border-b border-border">
        {days.slice(0, 7).map((day) => (
          <div
            key={day}
            className="py-2 text-center text-[11px] uppercase tracking-wide text-muted"
          >
            {weekdayLabel(day)}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7">
        {days.map((day) => {
          const items = byDay.get(day) ?? []
          const outside = !isSameMonth(day, reference)

          return (
            <div
              key={day}
              className={cn(
                'min-h-[104px] border-b border-l border-border p-1.5 first:border-l-0',
                outside && 'bg-background/60',
              )}
            >
              <button
                type="button"
                onClick={() => onSelectDay(day)}
                className={cn(
                  'mb-1 flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold tabular-nums transition-colors',
                  day === today
                    ? 'bg-primary text-white'
                    : outside
                      ? 'text-muted hover:bg-primary/10'
                      : 'text-foreground hover:bg-primary/10',
                )}
                aria-label={`Ver el ${day}`}
              >
                {dayNumber(day)}
              </button>

              <ul className="space-y-0.5">
                {items.slice(0, VISIBLE_PER_DAY).map(({ appointment, minutes }) => {
                  const closed =
                    appointment.status === 'CANCELADA' || appointment.status === 'NO_ASISTIO'
                  return (
                    <li key={appointment.id}>
                      <button
                        type="button"
                        onClick={() => onSelectAppointment(appointment)}
                        title={`${appointment.patient_name} · ${appointment.practitioner_name}`}
                        className={cn(
                          'flex w-full items-center gap-1 rounded px-1 py-0.5 text-left text-[11px] transition-colors hover:bg-primary/10',
                          closed && 'opacity-60',
                        )}
                      >
                        <span
                          className="h-1.5 w-1.5 shrink-0 rounded-full"
                          style={{ backgroundColor: hueColor(appointment.practitioner_id) }}
                        />
                        <span className="shrink-0 tabular-nums text-muted">
                          {String(Math.floor(minutes / 60)).padStart(2, '0')}:
                          {String(minutes % 60).padStart(2, '0')}
                        </span>
                        <span className={cn('truncate', closed && 'line-through')}>
                          {appointment.patient_name}
                        </span>
                      </button>
                    </li>
                  )
                })}

                {items.length > VISIBLE_PER_DAY && (
                  <li>
                    <button
                      type="button"
                      onClick={() => onSelectDay(day)}
                      className="w-full rounded px-1 py-0.5 text-left text-[11px] font-medium text-primary-dark hover:bg-primary/10"
                    >
                      +{items.length - VISIBLE_PER_DAY} más
                    </button>
                  </li>
                )}
              </ul>
            </div>
          )
        })}
      </div>
    </div>
  )
}
