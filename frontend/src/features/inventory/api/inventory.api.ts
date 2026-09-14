import { http } from '@/services/http'
import type {
  Category,
  CategoryPayload,
  ExpiringItem,
  InventoryStats,
  LowStockItem,
  Movement,
  MovementFilters,
  MovementPayload,
  Page,
  Product,
  ProductFilters,
  ProductPayload,
  ProductSummary,
} from '@/types'

export const inventoryApi = {
  categories: async (onlyActive = false): Promise<Category[]> => {
    const { data } = await http.get<Category[]>('/inventory/categories', {
      params: { only_active: onlyActive },
    })
    return data
  },
  createCategory: async (payload: CategoryPayload): Promise<Category> => {
    const { data } = await http.post<Category>('/inventory/categories', payload)
    return data
  },
  updateCategory: async (id: number, payload: CategoryPayload): Promise<Category> => {
    const { data } = await http.put<Category>(`/inventory/categories/${id}`, payload)
    return data
  },
  stats: async (): Promise<InventoryStats> => {
    const { data } = await http.get<InventoryStats>('/inventory/stats')
    return data
  },
  alerts: async (limit?: number): Promise<LowStockItem[]> => {
    const { data } = await http.get<LowStockItem[]>('/inventory/alerts', {
      params: limit ? { limit } : {},
    })
    return data
  },
  expiring: async (limit?: number): Promise<ExpiringItem[]> => {
    const { data } = await http.get<ExpiringItem[]>('/inventory/expiring', {
      params: limit ? { limit } : {},
    })
    return data
  },
  products: async (filters: ProductFilters): Promise<Page<Product>> => {
    const { data } = await http.get<Page<Product>>('/inventory/products', { params: filters })
    return data
  },
  searchProducts: async (term: string): Promise<ProductSummary[]> => {
    const { data } = await http.get<ProductSummary[]>('/inventory/products/search', {
      params: { term },
    })
    return data
  },
  getProduct: async (id: number): Promise<Product> => {
    const { data } = await http.get<Product>(`/inventory/products/${id}`)
    return data
  },
  createProduct: async (payload: ProductPayload): Promise<Product> => {
    const { data } = await http.post<Product>('/inventory/products', payload)
    return data
  },
  updateProduct: async (id: number, payload: ProductPayload): Promise<Product> => {
    const { data } = await http.put<Product>(`/inventory/products/${id}`, payload)
    return data
  },
  setProductStatus: async (id: number, isActive: boolean): Promise<Product> => {
    const { data } = await http.patch<Product>(`/inventory/products/${id}/status`, {
      is_active: isActive,
    })
    return data
  },
  movements: async (filters: MovementFilters): Promise<Page<Movement>> => {
    const { data } = await http.get<Page<Movement>>('/inventory/movements', { params: filters })
    return data
  },
  registerMovement: async (payload: MovementPayload): Promise<Movement> => {
    const { data } = await http.post<Movement>('/inventory/movements', payload)
    return data
  },
  adjustStock: async (
    productId: number,
    countedStock: number,
    notes?: string,
  ): Promise<Movement> => {
    const { data } = await http.post<Movement>('/inventory/movements/adjust', {
      product_id: productId,
      counted_stock: countedStock,
      notes: notes ?? null,
    })
    return data
  },
}
