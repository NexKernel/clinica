export const PRODUCT_KINDS = [
  'MEDICAMENTO',
  'INSUMO',
  'ORTOPEDICO',
  'UNIFORME',
  'OPTICA',
  'OTRO',
] as const
export type ProductKind = (typeof PRODUCT_KINDS)[number]

export const PRODUCT_KIND_LABELS: Record<ProductKind, string> = {
  MEDICAMENTO: 'Medicamento',
  INSUMO: 'Insumo médico',
  ORTOPEDICO: 'Producto ortopédico',
  UNIFORME: 'Uniforme de enfermería',
  OPTICA: 'Óptica',
  OTRO: 'Otro',
}

/** Antelación con que el sistema avisa un vencimiento (igual que el backend). */
export const EXPIRY_ALERT_DAYS = 60

export const MOVEMENT_TYPES = ['ENTRADA', 'SALIDA', 'AJUSTE'] as const
export type MovementType = (typeof MOVEMENT_TYPES)[number]

export const MOVEMENT_REASONS = [
  'COMPRA',
  'VENTA',
  'DISPENSACION',
  'DEVOLUCION',
  'MERMA',
  'VENCIMIENTO',
  'INVENTARIO_INICIAL',
  'AJUSTE_MANUAL',
  'ANULACION',
] as const
export type MovementReason = (typeof MOVEMENT_REASONS)[number]

export const MOVEMENT_REASON_LABELS: Record<MovementReason, string> = {
  COMPRA: 'Ingreso por compra',
  VENTA: 'Salida por venta',
  DISPENSACION: 'Dispensación al paciente',
  DEVOLUCION: 'Devolución',
  MERMA: 'Merma o pérdida',
  VENCIMIENTO: 'Producto vencido',
  INVENTARIO_INICIAL: 'Inventario inicial',
  AJUSTE_MANUAL: 'Ajuste manual',
  ANULACION: 'Reposición por anulación',
}

/** Motivos que el usuario puede elegir para cada tipo de movimiento. */
export const REASONS_BY_TYPE: Record<MovementType, MovementReason[]> = {
  ENTRADA: ['COMPRA', 'DEVOLUCION', 'INVENTARIO_INICIAL'],
  SALIDA: ['DISPENSACION', 'MERMA', 'VENCIMIENTO'],
  AJUSTE: ['AJUSTE_MANUAL'],
}

export interface CategoryPayload {
  name: string
  description: string | null
  is_active: boolean
}

export interface Category extends CategoryPayload {
  id: number
}

export interface ProductPayload {
  name: string
  kind: ProductKind
  category_id: number | null
  barcode: string | null
  presentation: string | null
  concentration: string | null
  unit: string
  laboratory: string | null
  requires_prescription: boolean
  purchase_price: string
  sale_price: string
  min_stock: number
  max_stock: number
  location: string | null
  lot: string | null
  expiry_date: string | null
  notes: string | null
  is_active: boolean
  code?: string | null
  initial_stock?: number
}

export interface Product extends Omit<ProductPayload, 'code' | 'initial_stock'> {
  id: number
  code: string
  full_name: string
  category_name: string | null
  kind_label: string
  stock: number
  needs_restock: boolean
  is_out_of_stock: boolean
  suggested_purchase: number
  days_to_expiry: number | null
  is_expired: boolean
  expires_soon: boolean
  expiry_label: string | null
  updated_at: string
}

export interface ProductSummary {
  id: number
  code: string
  name: string
  full_name: string
  unit: string
  stock: number
  sale_price: string
  purchase_price: string
  requires_prescription: boolean
  needs_restock: boolean
  expiry_date: string | null
  is_expired: boolean
  expires_soon: boolean
}

export interface MovementPayload {
  product_id: number
  movement_type: MovementType
  reason: MovementReason
  quantity: number
  unit_cost: string | null
  lot: string | null
  expiry_date: string | null
  occurred_at: string | null
  notes: string | null
}

export interface Movement {
  id: number
  product_id: number
  product_name: string
  movement_type: MovementType
  reason: MovementReason
  reason_label: string
  quantity: number
  signed_quantity: number
  stock_before: number
  stock_after: number
  unit_cost: string | null
  lot: string | null
  expiry_date: string | null
  reference_type: string | null
  reference_id: number | null
  notes: string | null
  occurred_at: string
}

export interface InventoryStats {
  total_products: number
  active_products: number
  low_stock: number
  out_of_stock: number
  expiring_soon: number
  expired: number
  inventory_value: number
}

/** Producto con stock vencido o próximo a vencer. */
export interface ExpiringItem {
  id: number
  code: string
  full_name: string
  unit: string
  stock: number
  lot: string | null
  expiry_date: string | null
  days_to_expiry: number | null
  expiry_label: string | null
  is_expired: boolean
  category_name: string | null
}

export interface LowStockItem {
  id: number
  code: string
  full_name: string
  unit: string
  stock: number
  min_stock: number
  max_stock: number
  suggested_purchase: number
  is_out_of_stock: boolean
  category_name: string | null
}

export interface ProductFilters {
  search?: string
  kind?: string
  category_id?: number
  is_active?: boolean
  low_stock?: boolean
  expiring?: boolean
  page: number
  page_size: number
}

export interface MovementFilters {
  product_id?: number
  movement_type?: string
  reason?: string
  date_from?: string
  date_to?: string
  page: number
  page_size: number
}
