import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { remindersApi } from '@/features/reminders/api/reminders.api'
import { getErrorMessage } from '@/services/http'
import type { ReminderChannel, ReminderFilters, ReminderPayload } from '@/types'

const REMINDERS_KEY = 'reminders'

export function useRemindersList(filters: ReminderFilters) {
  const query = useQuery({
    queryKey: [REMINDERS_KEY, 'list', filters],
    queryFn: () => remindersApi.list(filters),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar los recordatorios') : null,
  }
}

export function useReminderStats() {
  const query = useQuery({
    queryKey: [REMINDERS_KEY, 'stats'],
    queryFn: remindersApi.stats,
    staleTime: 60 * 1000,
  })
  return { stats: query.data ?? null, isLoading: query.isLoading }
}

export function useReminderActions() {
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: [REMINDERS_KEY] })

  const create = useMutation({
    mutationFn: (payload: ReminderPayload) => remindersApi.create(payload),
    onSuccess: invalidate,
  })

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ReminderPayload }) =>
      remindersApi.update(id, payload),
    onSuccess: invalidate,
  })

  const fromAppointment = useMutation({
    mutationFn: ({
      appointmentId,
      hoursBefore,
      channel,
    }: {
      appointmentId: number
      hoursBefore: number
      channel: ReminderChannel
    }) => remindersApi.fromAppointment(appointmentId, hoursBefore, channel),
    onSuccess: invalidate,
  })

  const fromEncounter = useMutation({
    mutationFn: ({
      encounterId,
      channel,
      startAt,
    }: {
      encounterId: number
      channel: ReminderChannel
      startAt?: string | null
    }) => remindersApi.fromEncounter(encounterId, channel, startAt),
    onSuccess: invalidate,
  })

  const markSent = useMutation({
    mutationFn: (id: number) => remindersApi.markSent(id),
    onSuccess: invalidate,
  })

  const cancel = useMutation({
    mutationFn: (id: number) => remindersApi.cancel(id),
    onSuccess: invalidate,
  })

  return { create, update, fromAppointment, fromEncounter, markSent, cancel }
}
