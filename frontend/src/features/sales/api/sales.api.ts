import { http } from '@/services/http'
import type {
  DocumentSeries,
  Page,
  Sale,
  SaleFilters,
  SaleListItem,
  SalePayload,
  SalesSummary,
  SeriesPayload,
} from '@/types'

export const salesApi = {
  series: async (onlyActive = false): Promise<DocumentSeries[]> => {
    const { data } = await http.get<DocumentSeries[]>('/sales/series', {
      params: { only_active: onlyActive },
    })
    return data
  },
  createSeries: async (payload: SeriesPayload): Promise<DocumentSeries> => {
    const { data } = await http.post<DocumentSeries>('/sales/series', payload)
    return data
  },
  updateSeries: async (id: number, payload: SeriesPayload): Promise<DocumentSeries> => {
    const { data } = await http.put<DocumentSeries>(`/sales/series/${id}`, payload)
    return data
  },
  summary: async (dateFrom?: string, dateTo?: string): Promise<SalesSummary> => {
    const { data } = await http.get<SalesSummary>('/sales/summary', {
      params: { ...(dateFrom ? { date_from: dateFrom } : {}), ...(dateTo ? { date_to: dateTo } : {}) },
    })
    return data
  },
  list: async (filters: SaleFilters): Promise<Page<SaleListItem>> => {
    const { data } = await http.get<Page<SaleListItem>>('/sales', { params: filters })
    return data
  },
  get: async (id: number): Promise<Sale> => {
    const { data } = await http.get<Sale>(`/sales/${id}`)
    return data
  },
  create: async (payload: SalePayload): Promise<Sale> => {
    const { data } = await http.post<Sale>('/sales', payload)
    return data
  },
  cancel: async (id: number, reason: string): Promise<Sale> => {
    const { data } = await http.post<Sale>(`/sales/${id}/cancel`, { reason })
    return data
  },
}
