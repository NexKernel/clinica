import { useCallback } from 'react'

import { EntityPicker } from '@/components/common/EntityPicker'
import { inventoryApi } from '@/features/inventory/api/inventory.api'
import { formatMoney } from '@/lib/utils'
import type { ProductSummary } from '@/types'

interface ProductPickerProps {
  label?: string
  value: ProductSummary | null
  onChange: (product: ProductSummary | null) => void
  disabled?: boolean
  error?: string | null
  /** Muestra el precio de venta en lugar del costo de compra. */
  priceMode?: 'sale' | 'purchase'
}

export function ProductPicker({
  label = 'Producto',
  value,
  onChange,
  disabled,
  error,
  priceMode = 'sale',
}: ProductPickerProps) {
  const search = useCallback((term: string) => inventoryApi.searchProducts(term), [])
  const priceOf = (product: ProductSummary) =>
    priceMode === 'sale' ? product.sale_price : product.purchase_price

  return (
    <EntityPicker<ProductSummary>
      label={label}
      placeholder="Nombre o código del producto"
      value={value}
      onChange={onChange}
      search={search}
      disabled={disabled}
      error={error}
      emptyLabel="No se encontraron productos"
      getKey={(product) => product.id}
      getLabel={(product) => product.full_name}
      renderItem={(product) => (
        <div className="flex items-baseline justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate font-medium text-foreground">{product.full_name}</p>
            <p className="truncate text-xs text-muted">
              {product.code} · stock {product.stock} {product.unit.toLowerCase()}
            </p>
            {product.is_expired && (
              <p className="truncate text-xs font-medium text-danger">Lote vencido</p>
            )}
            {!product.is_expired && product.expires_soon && (
              <p className="truncate text-xs font-medium text-warning-dark">Próximo a vencer</p>
            )}
          </div>
          <span className="shrink-0 text-xs font-semibold text-primary-dark">
            {formatMoney(priceOf(product))}
          </span>
        </div>
      )}
    />
  )
}
