import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { inventoryApi } from '@/features/inventory/api/inventory.api'
import { getErrorMessage } from '@/services/http'
import type {
  CategoryPayload,
  MovementFilters,
  MovementPayload,
  ProductFilters,
  ProductPayload,
} from '@/types'

const INVENTORY_KEY = 'inventory'

export function useCategories(onlyActive = false) {
  const query = useQuery({
    queryKey: [INVENTORY_KEY, 'categories', onlyActive],
    queryFn: () => inventoryApi.categories(onlyActive),
    staleTime: 10 * 60 * 1000,
  })
  return { categories: query.data ?? [], isLoading: query.isLoading }
}

export function useInventoryStats() {
  const query = useQuery({
    queryKey: [INVENTORY_KEY, 'stats'],
    queryFn: inventoryApi.stats,
    staleTime: 60 * 1000,
  })
  return { stats: query.data ?? null, isLoading: query.isLoading }
}

export function useStockAlerts(limit?: number) {
  const query = useQuery({
    queryKey: [INVENTORY_KEY, 'alerts', limit ?? null],
    queryFn: () => inventoryApi.alerts(limit),
  })
  return { alerts: query.data ?? [], isLoading: query.isLoading }
}

export function useExpiringStock(limit?: number) {
  const query = useQuery({
    queryKey: [INVENTORY_KEY, 'expiring', limit ?? null],
    queryFn: () => inventoryApi.expiring(limit),
  })
  return { items: query.data ?? [], isLoading: query.isLoading }
}

export function useProductsList(filters: ProductFilters) {
  const query = useQuery({
    queryKey: [INVENTORY_KEY, 'products', filters],
    queryFn: () => inventoryApi.products(filters),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar los productos') : null,
  }
}

export function useMovementsList(filters: MovementFilters) {
  const query = useQuery({
    queryKey: [INVENTORY_KEY, 'movements', filters],
    queryFn: () => inventoryApi.movements(filters),
    placeholderData: (previous) => previous,
  })

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar el kardex') : null,
  }
}

export function useInventoryActions() {
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: [INVENTORY_KEY] })

  const createCategory = useMutation({
    mutationFn: (payload: CategoryPayload) => inventoryApi.createCategory(payload),
    onSuccess: invalidate,
  })

  const updateCategory = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: CategoryPayload }) =>
      inventoryApi.updateCategory(id, payload),
    onSuccess: invalidate,
  })

  const createProduct = useMutation({
    mutationFn: (payload: ProductPayload) => inventoryApi.createProduct(payload),
    onSuccess: invalidate,
  })

  const updateProduct = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ProductPayload }) =>
      inventoryApi.updateProduct(id, payload),
    onSuccess: invalidate,
  })

  const setProductStatus = useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) =>
      inventoryApi.setProductStatus(id, isActive),
    onSuccess: invalidate,
  })

  const registerMovement = useMutation({
    mutationFn: (payload: MovementPayload) => inventoryApi.registerMovement(payload),
    onSuccess: invalidate,
  })

  const adjustStock = useMutation({
    mutationFn: ({
      productId,
      countedStock,
      notes,
    }: {
      productId: number
      countedStock: number
      notes?: string
    }) => inventoryApi.adjustStock(productId, countedStock, notes),
    onSuccess: invalidate,
  })

  return {
    createCategory,
    updateCategory,
    createProduct,
    updateProduct,
    setProductStatus,
    registerMovement,
    adjustStock,
  }
}
