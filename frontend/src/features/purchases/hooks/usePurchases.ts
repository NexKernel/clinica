import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { purchasesApi } from '@/features/purchases/api/purchases.api'
import { getErrorMessage } from '@/services/http'
import type { PurchaseFilters, PurchasePayload, SupplierPayload } from '@/types'

const PURCHASES_KEY = 'purchases'

export function useActiveSuppliers() {
  const query = useQuery({
    queryKey: [PURCHASES_KEY, 'suppliers', 'active'],
    queryFn: purchasesApi.activeSuppliers,
    staleTime: 5 * 60 * 1000,
  })
  return { suppliers: query.data ?? [], isLoading: query.isLoading }
}

export function useSuppliersList(params: {
  page: number
  page_size: number
  search?: string
  is_active?: boolean
}) {
  const query = useQuery({
    queryKey: [PURCHASES_KEY, 'suppliers', params],
    queryFn: () => purchasesApi.suppliers(params),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar los proveedores') : null,
  }
}

export function usePurchaseStats() {
  const query = useQuery({
    queryKey: [PURCHASES_KEY, 'stats'],
    queryFn: purchasesApi.stats,
    staleTime: 60 * 1000,
  })
  return { stats: query.data ?? null, isLoading: query.isLoading }
}

export function usePurchasesList(filters: PurchaseFilters) {
  const query = useQuery({
    queryKey: [PURCHASES_KEY, 'list', filters],
    queryFn: () => purchasesApi.list(filters),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar las compras') : null,
  }
}

export function usePurchase(purchaseId: number | null) {
  const query = useQuery({
    queryKey: [PURCHASES_KEY, 'detail', purchaseId],
    queryFn: () => purchasesApi.get(purchaseId as number),
    enabled: purchaseId !== null,
  })

  return {
    purchase: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar la compra') : null,
  }
}

export function usePurchaseActions() {
  const queryClient = useQueryClient()
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: [PURCHASES_KEY] })
    void queryClient.invalidateQueries({ queryKey: ['inventory'] })
  }

  const createSupplier = useMutation({
    mutationFn: (payload: SupplierPayload) => purchasesApi.createSupplier(payload),
    onSuccess: invalidate,
  })

  const updateSupplier = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: SupplierPayload }) =>
      purchasesApi.updateSupplier(id, payload),
    onSuccess: invalidate,
  })

  const create = useMutation({
    mutationFn: (payload: PurchasePayload) => purchasesApi.create(payload),
    onSuccess: invalidate,
  })

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: PurchasePayload }) =>
      purchasesApi.update(id, payload),
    onSuccess: invalidate,
  })

  const receive = useMutation({
    mutationFn: (id: number) => purchasesApi.receive(id),
    onSuccess: invalidate,
  })

  const cancel = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      purchasesApi.cancel(id, reason),
    onSuccess: invalidate,
  })

  return { createSupplier, updateSupplier, create, update, receive, cancel }
}
