import { http } from '@/services/http'
import type { NotificationFeed } from '@/types'

export const notificationsApi = {
  feed: async (): Promise<NotificationFeed> => {
    const { data } = await http.get<NotificationFeed>('/notifications')
    return data
  },
}
