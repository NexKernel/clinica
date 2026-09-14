import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { appointmentsApi } from '@/features/appointments/api/appointments.api'
import { getErrorMessage } from '@/services/http'
import type { AppointmentFilters, AppointmentPayload, AppointmentStatus } from '@/types'

const APPOINTMENTS_KEY = 'appointments'

export function useAgenda(day: string, practitionerId?: number) {
  const query = useQuery({
    queryKey: [APPOINTMENTS_KEY, 'agenda', day, practitionerId ?? null],
    queryFn: () => appointmentsApi.agenda(day, practitionerId),
    placeholderData: (previous) => previous,
  })

  return {
    appointments: query.data ?? [],
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar la agenda') : null,
  }
}

/** Agenda de un rango de días: alimenta las vistas de semana y de mes. */
export function useAgendaRange(dateFrom: string, dateTo: string, practitionerId?: number) {
  const query = useQuery({
    queryKey: [APPOINTMENTS_KEY, 'agenda-range', dateFrom, dateTo, practitionerId ?? null],
    queryFn: () => appointmentsApi.agendaRange(dateFrom, dateTo, practitionerId),
    placeholderData: (previous) => previous,
  })

  return {
    appointments: query.data ?? [],
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar la agenda') : null,
  }
}

export function useAgendaSummary(day: string, practitionerId?: number) {
  const query = useQuery({
    queryKey: [APPOINTMENTS_KEY, 'summary', day, practitionerId ?? null],
    queryFn: () => appointmentsApi.summary(day, practitionerId),
  })
  return { summary: query.data ?? null, isLoading: query.isLoading }
}

export function useAvailability(practitionerId: number | null, day: string) {
  const query = useQuery({
    queryKey: [APPOINTMENTS_KEY, 'availability', practitionerId, day],
    queryFn: () => appointmentsApi.availability(practitionerId as number, day),
    enabled: practitionerId !== null && Boolean(day),
  })

  return {
    availability: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar la disponibilidad') : null,
  }
}

export function useAppointmentsList(filters: AppointmentFilters) {
  const query = useQuery({
    queryKey: [APPOINTMENTS_KEY, 'list', filters],
    queryFn: () => appointmentsApi.list(filters),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar las citas') : null,
  }
}

export function usePatientAppointments(patientId: number | null) {
  const query = useQuery({
    queryKey: [APPOINTMENTS_KEY, 'patient', patientId],
    queryFn: () => appointmentsApi.forPatient(patientId as number),
    enabled: patientId !== null,
  })
  return { appointments: query.data ?? [], isLoading: query.isLoading }
}

export function useAppointmentActions() {
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: [APPOINTMENTS_KEY] })

  const create = useMutation({
    mutationFn: (payload: AppointmentPayload) => appointmentsApi.create(payload),
    onSuccess: invalidate,
  })

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: AppointmentPayload }) =>
      appointmentsApi.update(id, payload),
    onSuccess: invalidate,
  })

  const changeStatus = useMutation({
    mutationFn: ({
      id,
      status,
      cancelReason,
    }: {
      id: number
      status: AppointmentStatus
      cancelReason?: string
    }) => appointmentsApi.changeStatus(id, status, cancelReason),
    onSuccess: invalidate,
  })

  return { create, update, changeStatus }
}
