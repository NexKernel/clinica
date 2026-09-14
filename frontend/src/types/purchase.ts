export const SUPPLIER_DOCUMENT_TYPES = ['FACTURA', 'BOLETA', 'GUIA_REMISION', 'OTRO'] as const
export type SupplierDocumentType = (typeof SUPPLIER_DOCUMENT_TYPES)[number]

export const SUPPLIER_DOCUMENT_LABELS: Record<SupplierDocumentType, string> = {
  FACTURA: 'Factura',
  BOLETA: 'Boleta',
  GUIA_REMISION: 'Guía de remisión',
  OTRO: 'Otro documento',
}

export const PURCHASE_STATUSES = ['BORRADOR', 'RECIBIDA', 'ANULADA'] as const
export type PurchaseStatus = (typeof PURCHASE_STATUSES)[number]

export const PURCHASE_STATUS_LABELS: Record<PurchaseStatus, string> = {
  BORRADOR: 'Borrador',
  RECIBIDA: 'Recibida',
  ANULADA: 'Anulada',
}

export interface SupplierPayload {
  tax_id: string | null
  business_name: string
  trade_name: string | null
  contact_name: string | null
  phone: string | null
  email: string | null
  address: string | null
  notes: string | null
  is_active: boolean
}

export interface Supplier extends SupplierPayload {
  id: number
  display_name: string
}

export interface PurchaseItemPayload {
  product_id: number
  quantity: number
  unit_cost: string
  lot: string | null
  expiry_date: string | null
}

export interface PurchaseItem extends PurchaseItemPayload {
  id: number
  product_name: string
  product_code: string
  unit: string
  subtotal: string
}

export interface PurchasePayload {
  supplier_id: number
  document_type: SupplierDocumentType
  series: string | null
  number: string | null
  issue_date: string
  apply_tax: boolean
  notes: string | null
  items: PurchaseItemPayload[]
}

export interface Purchase {
  id: number
  supplier_id: number
  supplier_name: string
  document_type: SupplierDocumentType
  document_label: string
  series: string | null
  number: string | null
  document_number: string | null
  issue_date: string
  received_at: string | null
  status: PurchaseStatus
  status_label: string
  is_editable: boolean
  subtotal: string
  tax: string
  total: string
  item_count: number
  total_units: number
  notes: string | null
  cancel_reason: string | null
  items: PurchaseItem[]
  created_at: string
}

export interface PurchaseListItem {
  id: number
  supplier_name: string
  document_label: string
  document_number: string | null
  issue_date: string
  status: PurchaseStatus
  status_label: string
  item_count: number
  total: string
}

export interface PurchaseStats {
  drafts: number
  received_this_month: number
  amount_this_month: number
  active_suppliers: number
}

export interface PurchaseFilters {
  search?: string
  supplier_id?: number
  status?: string
  date_from?: string
  date_to?: string
  page: number
  page_size: number
}
