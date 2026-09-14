import { http } from '@/services/http'
import type {
  AgendaSummary,
  Appointment,
  AppointmentFilters,
  AppointmentPayload,
  AppointmentStatus,
  DayAvailability,
  Page,
} from '@/types'

export const appointmentsApi = {
  list: async (filters: AppointmentFilters): Promise<Page<Appointment>> => {
    const { data } = await http.get<Page<Appointment>>('/appointments', { params: filters })
    return data
  },
  agenda: async (day: string, practitionerId?: number): Promise<Appointment[]> => {
    const { data } = await http.get<Appointment[]>('/appointments/agenda', {
      params: { day, ...(practitionerId ? { practitioner_id: practitionerId } : {}) },
    })
    return data
  },
  agendaRange: async (
    dateFrom: string,
    dateTo: string,
    practitionerId?: number,
  ): Promise<Appointment[]> => {
    const { data } = await http.get<Appointment[]>('/appointments/agenda', {
      params: {
        date_from: dateFrom,
        date_to: dateTo,
        ...(practitionerId ? { practitioner_id: practitionerId } : {}),
      },
    })
    return data
  },
  summary: async (day: string, practitionerId?: number): Promise<AgendaSummary> => {
    const { data } = await http.get<AgendaSummary>('/appointments/summary', {
      params: { day, ...(practitionerId ? { practitioner_id: practitionerId } : {}) },
    })
    return data
  },
  availability: async (practitionerId: number, day: string): Promise<DayAvailability> => {
    const { data } = await http.get<DayAvailability>('/appointments/availability', {
      params: { practitioner_id: practitionerId, day },
    })
    return data
  },
  forPatient: async (patientId: number): Promise<Appointment[]> => {
    const { data } = await http.get<Appointment[]>(`/appointments/patient/${patientId}`)
    return data
  },
  get: async (id: number): Promise<Appointment> => {
    const { data } = await http.get<Appointment>(`/appointments/${id}`)
    return data
  },
  create: async (payload: AppointmentPayload): Promise<Appointment> => {
    const { data } = await http.post<Appointment>('/appointments', payload)
    return data
  },
  update: async (id: number, payload: AppointmentPayload): Promise<Appointment> => {
    const { data } = await http.put<Appointment>(`/appointments/${id}`, payload)
    return data
  },
  changeStatus: async (
    id: number,
    status: AppointmentStatus,
    cancelReason?: string,
  ): Promise<Appointment> => {
    const { data } = await http.patch<Appointment>(`/appointments/${id}/status`, {
      status,
      cancel_reason: cancelReason ?? null,
    })
    return data
  },
}
