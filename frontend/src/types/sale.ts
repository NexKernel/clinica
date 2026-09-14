export const DOCUMENT_TYPES = ['NOTA_VENTA', 'BOLETA', 'FACTURA'] as const
export type SaleDocumentType = (typeof DOCUMENT_TYPES)[number]

export const DOCUMENT_TYPE_LABELS: Record<SaleDocumentType, string> = {
  NOTA_VENTA: 'Nota de venta',
  BOLETA: 'Boleta de venta',
  FACTURA: 'Factura',
}

export const PAYMENT_METHODS = [
  'EFECTIVO',
  'TARJETA',
  'YAPE',
  'PLIN',
  'TRANSFERENCIA',
  'CREDITO',
] as const
export type PaymentMethod = (typeof PAYMENT_METHODS)[number]

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  EFECTIVO: 'Efectivo',
  TARJETA: 'Tarjeta',
  YAPE: 'Yape',
  PLIN: 'Plin',
  TRANSFERENCIA: 'Transferencia',
  CREDITO: 'Crédito',
}

export type SaleStatus = 'EMITIDA' | 'ANULADA'

export interface SeriesPayload {
  document_type: SaleDocumentType
  series: string
  next_number: number
  is_default: boolean
  is_active: boolean
}

export interface DocumentSeries extends SeriesPayload {
  id: number
  document_label: string
}

export interface SaleItemPayload {
  product_id: number | null
  service_id: number | null
  description: string | null
  quantity: number
  unit_price: string | null
  discount: string
}

export interface SaleItem {
  id: number
  product_id: number | null
  service_id: number | null
  description: string
  unit: string
  quantity: number
  unit_price: string
  discount: string
  subtotal: string
}

export interface SalePayload {
  document_type: SaleDocumentType
  series: string | null
  patient_id: number | null
  encounter_id: number | null
  customer_document_type: string | null
  customer_document_number: string | null
  customer_name: string | null
  customer_address: string | null
  payment_method: PaymentMethod
  issued_at: string | null
  apply_tax: boolean
  notes: string | null
  items: SaleItemPayload[]
}

export interface Sale {
  id: number
  document_type: SaleDocumentType
  document_label: string
  series: string
  number: string
  full_number: string
  patient_id: number | null
  encounter_id: number | null
  customer_document_type: string | null
  customer_document_number: string | null
  customer_name: string
  customer_address: string | null
  issued_at: string
  status: SaleStatus
  status_label: string
  is_cancelled: boolean
  is_electronic: boolean
  payment_method: PaymentMethod
  payment_label: string
  subtotal: string
  tax: string
  discount: string
  total: string
  tax_rate: string
  notes: string | null
  cancel_reason: string | null
  external_id: string | null
  external_status: string | null
  item_count: number
  items: SaleItem[]
  created_at: string
}

export interface SaleListItem {
  id: number
  document_label: string
  full_number: string
  customer_name: string
  issued_at: string
  payment_label: string
  total: string
  status: SaleStatus
  status_label: string
  item_count: number
}

export interface SalesSummary {
  date_from: string
  date_to: string
  documents: number
  cancelled: number
  subtotal: number
  tax: number
  total: number
  by_payment_method: Record<string, number>
  by_document_type: Record<string, number>
}

export interface SaleFilters {
  search?: string
  document_type?: string
  status?: string
  patient_id?: number
  payment_method?: string
  date_from?: string
  date_to?: string
  page: number
  page_size: number
}
