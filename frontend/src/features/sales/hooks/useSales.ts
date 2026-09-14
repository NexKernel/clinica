import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { salesApi } from '@/features/sales/api/sales.api'
import { getErrorMessage } from '@/services/http'
import type { SaleFilters, SalePayload, SeriesPayload } from '@/types'

const SALES_KEY = 'sales'

export function useDocumentSeries(onlyActive = false) {
  const query = useQuery({
    queryKey: [SALES_KEY, 'series', onlyActive],
    queryFn: () => salesApi.series(onlyActive),
    staleTime: 5 * 60 * 1000,
  })
  return { series: query.data ?? [], isLoading: query.isLoading }
}

export function useSalesSummary(dateFrom?: string, dateTo?: string) {
  const query = useQuery({
    queryKey: [SALES_KEY, 'summary', dateFrom ?? null, dateTo ?? null],
    queryFn: () => salesApi.summary(dateFrom, dateTo),
  })

  return {
    summary: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar el resumen') : null,
  }
}

export function useSalesList(filters: SaleFilters) {
  const query = useQuery({
    queryKey: [SALES_KEY, 'list', filters],
    queryFn: () => salesApi.list(filters),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar los comprobantes') : null,
  }
}

export function useSale(saleId: number | null) {
  const query = useQuery({
    queryKey: [SALES_KEY, 'detail', saleId],
    queryFn: () => salesApi.get(saleId as number),
    enabled: saleId !== null,
  })

  return {
    sale: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar el comprobante') : null,
  }
}

export function useSaleActions() {
  const queryClient = useQueryClient()
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: [SALES_KEY] })
    void queryClient.invalidateQueries({ queryKey: ['inventory'] })
    void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  const create = useMutation({
    mutationFn: (payload: SalePayload) => salesApi.create(payload),
    onSuccess: invalidate,
  })

  const cancel = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => salesApi.cancel(id, reason),
    onSuccess: invalidate,
  })

  const createSeries = useMutation({
    mutationFn: (payload: SeriesPayload) => salesApi.createSeries(payload),
    onSuccess: invalidate,
  })

  const updateSeries = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: SeriesPayload }) =>
      salesApi.updateSeries(id, payload),
    onSuccess: invalidate,
  })

  return { create, cancel, createSeries, updateSeries }
}
