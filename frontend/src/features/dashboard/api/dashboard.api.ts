import { http } from '@/services/http'
import type { DashboardSummary } from '@/types'

export const dashboardApi = {
  summary: async (day?: string): Promise<DashboardSummary> => {
    const { data } = await http.get<DashboardSummary>('/dashboard/summary', {
      params: day ? { day } : {},
    })
    return data
  },
}
