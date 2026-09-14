import { http } from '@/services/http'
import type {
  Page,
  Reminder,
  ReminderBatch,
  ReminderChannel,
  ReminderFilters,
  ReminderPayload,
  ReminderStats,
  WhatsAppMessage,
} from '@/types'

export const remindersApi = {
  list: async (filters: ReminderFilters): Promise<Page<Reminder>> => {
    const { data } = await http.get<Page<Reminder>>('/reminders', { params: filters })
    return data
  },
  pending: async (): Promise<Reminder[]> => {
    const { data } = await http.get<Reminder[]>('/reminders/pending')
    return data
  },
  stats: async (): Promise<ReminderStats> => {
    const { data } = await http.get<ReminderStats>('/reminders/stats')
    return data
  },
  create: async (payload: ReminderPayload): Promise<Reminder> => {
    const { data } = await http.post<Reminder>('/reminders', payload)
    return data
  },
  update: async (id: number, payload: ReminderPayload): Promise<Reminder> => {
    const { data } = await http.put<Reminder>(`/reminders/${id}`, payload)
    return data
  },
  fromAppointment: async (
    appointmentId: number,
    hoursBefore: number,
    channel: ReminderChannel,
  ): Promise<ReminderBatch> => {
    const { data } = await http.post<ReminderBatch>(
      `/reminders/from-appointment/${appointmentId}`,
      { hours_before: hoursBefore, channel },
    )
    return data
  },
  fromEncounter: async (
    encounterId: number,
    channel: ReminderChannel,
    startAt?: string | null,
  ): Promise<ReminderBatch> => {
    const { data } = await http.post<ReminderBatch>(`/reminders/from-encounter/${encounterId}`, {
      channel,
      start_at: startAt ?? null,
    })
    return data
  },
  whatsapp: async (id: number): Promise<WhatsAppMessage> => {
    const { data } = await http.get<WhatsAppMessage>(`/reminders/${id}/whatsapp`)
    return data
  },
  markSent: async (id: number): Promise<Reminder> => {
    const { data } = await http.post<Reminder>(`/reminders/${id}/sent`)
    return data
  },
  cancel: async (id: number): Promise<Reminder> => {
    const { data } = await http.post<Reminder>(`/reminders/${id}/cancel`)
    return data
  },
}
