import { http } from '@/services/http'
import type {
  Page,
  Purchase,
  PurchaseFilters,
  PurchaseListItem,
  PurchasePayload,
  PurchaseStats,
  Supplier,
  SupplierPayload,
} from '@/types'

export const purchasesApi = {
  suppliers: async (params: {
    page: number
    page_size: number
    search?: string
    is_active?: boolean
  }): Promise<Page<Supplier>> => {
    const { data } = await http.get<Page<Supplier>>('/purchases/suppliers', { params })
    return data
  },
  activeSuppliers: async (): Promise<Supplier[]> => {
    const { data } = await http.get<Supplier[]>('/purchases/suppliers/active')
    return data
  },
  createSupplier: async (payload: SupplierPayload): Promise<Supplier> => {
    const { data } = await http.post<Supplier>('/purchases/suppliers', payload)
    return data
  },
  updateSupplier: async (id: number, payload: SupplierPayload): Promise<Supplier> => {
    const { data } = await http.put<Supplier>(`/purchases/suppliers/${id}`, payload)
    return data
  },
  stats: async (): Promise<PurchaseStats> => {
    const { data } = await http.get<PurchaseStats>('/purchases/stats')
    return data
  },
  list: async (filters: PurchaseFilters): Promise<Page<PurchaseListItem>> => {
    const { data } = await http.get<Page<PurchaseListItem>>('/purchases', { params: filters })
    return data
  },
  get: async (id: number): Promise<Purchase> => {
    const { data } = await http.get<Purchase>(`/purchases/${id}`)
    return data
  },
  create: async (payload: PurchasePayload): Promise<Purchase> => {
    const { data } = await http.post<Purchase>('/purchases', payload)
    return data
  },
  update: async (id: number, payload: PurchasePayload): Promise<Purchase> => {
    const { data } = await http.put<Purchase>(`/purchases/${id}`, payload)
    return data
  },
  receive: async (id: number): Promise<Purchase> => {
    const { data } = await http.post<Purchase>(`/purchases/${id}/receive`)
    return data
  },
  cancel: async (id: number, reason: string): Promise<Purchase> => {
    const { data } = await http.post<Purchase>(`/purchases/${id}/cancel`, { reason })
    return data
  },
}
