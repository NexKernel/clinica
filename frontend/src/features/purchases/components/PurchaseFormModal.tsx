import { useEffect, useState, type FormEvent } from 'react'
import { Plus, Save, Trash2 } from 'lucide-react'

import {
  Alert,
  Button,
  Input,
  Modal,
  Select,
  Switch,
  Textarea,
  type SelectOption,
} from '@/components/ui'
import { ProductPicker } from '@/features/inventory/components/ProductPicker'
import { useActiveSuppliers, usePurchaseActions } from '@/features/purchases/hooks/usePurchases'
import { useTaxRate } from '@/features/settings/hooks/useSettings'
import { toDateInput } from '@/lib/datetime'
import { formatMoney, formatPercent } from '@/lib/utils'
import { getErrorMessage } from '@/services/http'
import {
  SUPPLIER_DOCUMENT_LABELS,
  SUPPLIER_DOCUMENT_TYPES,
  type ProductSummary,
  type Purchase,
  type SupplierDocumentType,
} from '@/types'

const DOCUMENT_OPTIONS: SelectOption[] = SUPPLIER_DOCUMENT_TYPES.map((type) => ({
  value: type,
  label: SUPPLIER_DOCUMENT_LABELS[type],
}))


interface ItemDraft {
  product: ProductSummary | null
  quantity: string
  unitCost: string
  lot: string
  expiry: string
}

const emptyItem = (): ItemDraft => ({
  product: null,
  quantity: '1',
  unitCost: '',
  lot: '',
  expiry: '',
})

const lineTotal = (item: ItemDraft): number => {
  const quantity = Number(item.quantity) || 0
  const cost = Number(item.unitCost) || 0
  return quantity * cost
}

interface PurchaseFormModalProps {
  open: boolean
  purchase: Purchase | null
  onClose: () => void
}

export function PurchaseFormModal({ open, purchase, onClose }: PurchaseFormModalProps) {
  const isEdit = purchase !== null
  // Una compra recibida o anulada se consulta, pero ya no admite cambios.
  const isReadOnly = purchase !== null && !purchase.is_editable
  const { suppliers } = useActiveSuppliers()
  const { create, update } = usePurchaseActions()
  const taxRate = useTaxRate()
  const isLoading = create.isPending || update.isPending
  const locked = isLoading || isReadOnly

  const [supplierId, setSupplierId] = useState('')
  const [documentType, setDocumentType] = useState<SupplierDocumentType>('FACTURA')
  const [series, setSeries] = useState('')
  const [number, setNumber] = useState('')
  const [issueDate, setIssueDate] = useState(() => toDateInput())
  const [applyTax, setApplyTax] = useState(true)
  const [notes, setNotes] = useState('')
  const [items, setItems] = useState<ItemDraft[]>([emptyItem()])
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setFormError(null)

    if (purchase) {
      setSupplierId(String(purchase.supplier_id))
      setDocumentType(purchase.document_type)
      setSeries(purchase.series ?? '')
      setNumber(purchase.number ?? '')
      setIssueDate(purchase.issue_date)
      setApplyTax(Number(purchase.tax) > 0)
      setNotes(purchase.notes ?? '')
      setItems(
        purchase.items.map((item) => ({
          product: {
            id: item.product_id,
            code: item.product_code,
            name: item.product_name,
            full_name: item.product_name,
            unit: item.unit,
            stock: 0,
            sale_price: '0.00',
            purchase_price: item.unit_cost,
            requires_prescription: false,
            needs_restock: false,
            expiry_date: item.expiry_date,
            is_expired: false,
            expires_soon: false,
          },
          quantity: String(item.quantity),
          unitCost: item.unit_cost,
          lot: item.lot ?? '',
          expiry: item.expiry_date ?? '',
        })),
      )
      return
    }

    setSupplierId('')
    setDocumentType('FACTURA')
    setSeries('')
    setNumber('')
    setIssueDate(toDateInput())
    setApplyTax(true)
    setNotes('')
    setItems([emptyItem()])
  }, [open, purchase])

  const updateItem = (index: number, patch: Partial<ItemDraft>) =>
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)))

  const subtotal = items.reduce((sum, item) => sum + lineTotal(item), 0)
  const tax = applyTax ? subtotal * taxRate : 0

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    if (!supplierId) return setFormError('Seleccione el proveedor')
    const validItems = items.filter((item) => item.product !== null)
    if (validItems.length === 0) return setFormError('Agregue al menos un producto')
    if (validItems.some((item) => Number(item.quantity) <= 0)) {
      return setFormError('Las cantidades deben ser mayores que cero')
    }

    const payload = {
      supplier_id: Number(supplierId),
      document_type: documentType,
      series: series.trim() || null,
      number: number.trim() || null,
      issue_date: issueDate,
      apply_tax: applyTax,
      notes: notes.trim() || null,
      items: validItems.map((item) => ({
        product_id: (item.product as ProductSummary).id,
        quantity: Number(item.quantity),
        unit_cost: item.unitCost || '0.00',
        lot: item.lot.trim() || null,
        expiry_date: item.expiry || null,
      })),
    }

    try {
      if (purchase) {
        await update.mutateAsync({ id: purchase.id, payload })
      } else {
        await create.mutateAsync(payload)
      }
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo guardar la compra'))
    }
  }

  const supplierOptions: SelectOption[] = suppliers.map((item) => ({
    value: String(item.id),
    label: item.display_name,
  }))

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Editar compra' : 'Nueva compra'}
      description="El inventario se actualiza al marcar la compra como recibida"
      size="xl"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            {isReadOnly ? 'Cerrar' : 'Cancelar'}
          </Button>
          {!isReadOnly && (
            <Button
              type="submit"
              form="purchase-form"
              size="sm"
              isLoading={isLoading}
              leftIcon={<Save className="h-4 w-4" />}
            >
              {isEdit ? 'Guardar cambios' : 'Registrar compra'}
            </Button>
          )}
        </>
      }
    >
      <form id="purchase-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        {isReadOnly && (
          <Alert variant="info">
            Esta compra está {purchase.status_label.toLowerCase()} y se muestra solo para
            consulta.
          </Alert>
        )}

        <Select
          label="Proveedor"
          options={supplierOptions}
          placeholder="Seleccione el proveedor"
          value={supplierId}
          disabled={locked}
          onChange={(event) => setSupplierId(event.target.value)}
        />

        <div className="grid gap-4 sm:grid-cols-4">
          <Select
            label="Documento"
            options={DOCUMENT_OPTIONS}
            value={documentType}
            disabled={locked}
            onChange={(event) => setDocumentType(event.target.value as SupplierDocumentType)}
          />
          <Input
            label="Serie"
            placeholder="F001"
            value={series}
            disabled={locked}
            onChange={(event) => setSeries(event.target.value)}
          />
          <Input
            label="Número"
            placeholder="0001234"
            value={number}
            disabled={locked}
            onChange={(event) => setNumber(event.target.value)}
          />
          <Input
            label="Fecha de emisión"
            type="date"
            value={issueDate}
            disabled={locked}
            onChange={(event) => setIssueDate(event.target.value)}
          />
        </div>

        <div className="space-y-3">
          <p className="caption uppercase tracking-wide">Detalle de la compra</p>

          {items.map((item, index) => (
            <div key={index} className="space-y-3 rounded-xl border border-border p-3">
              <div className="flex items-start gap-3">
                <ProductPicker
                  value={item.product}
                  priceMode="purchase"
                  disabled={locked}
                  onChange={(product) =>
                    updateItem(index, {
                      product,
                      unitCost: product ? product.purchase_price : item.unitCost,
                    })
                  }
                />
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Quitar producto"
                  className="mt-1"
                  disabled={locked || items.length === 1}
                  onClick={() => setItems((prev) => prev.filter((_, i) => i !== index))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>

              <div className="grid gap-3 sm:grid-cols-5">
                <Input
                  label="Cantidad"
                  type="number"
                  value={item.quantity}
                  disabled={locked}
                  onChange={(event) => updateItem(index, { quantity: event.target.value })}
                />
                <Input
                  label="Costo unitario"
                  type="number"
                  step="0.01"
                  value={item.unitCost}
                  disabled={locked}
                  onChange={(event) => updateItem(index, { unitCost: event.target.value })}
                />
                <Input
                  label="Lote"
                  value={item.lot}
                  disabled={locked}
                  onChange={(event) => updateItem(index, { lot: event.target.value })}
                />
                <Input
                  label="Vencimiento"
                  type="date"
                  value={item.expiry}
                  disabled={locked}
                  onChange={(event) => updateItem(index, { expiry: event.target.value })}
                />
                <div className="flex items-end pb-3">
                  <span className="text-sm font-semibold text-foreground">
                    {formatMoney(lineTotal(item))}
                  </span>
                </div>
              </div>
            </div>
          ))}

          <Button
            variant="outline"
            size="sm"
            leftIcon={<Plus className="h-4 w-4" />}
            disabled={locked}
            onClick={() => setItems((prev) => [...prev, emptyItem()])}
          >
            Agregar producto
          </Button>
        </div>

        <Switch
          label="Agregar IGV"
          description="El impuesto se calcula sobre el subtotal de la compra"
          checked={applyTax}
          disabled={locked}
          onChange={setApplyTax}
        />

        <div className="rounded-xl bg-background/70 px-4 py-3 text-sm">
          <div className="flex justify-between text-muted">
            <span>Subtotal</span>
            <span>{formatMoney(subtotal)}</span>
          </div>
          <div className="flex justify-between text-muted">
            <span>IGV{applyTax ? ` (${formatPercent(taxRate)})` : ''}</span>
            <span>{formatMoney(tax)}</span>
          </div>
          <div className="mt-1 flex justify-between border-t border-border pt-1 text-base font-semibold text-foreground">
            <span>Total</span>
            <span>{formatMoney(subtotal + tax)}</span>
          </div>
        </div>

        <Textarea
          label="Observaciones"
          value={notes}
          disabled={locked}
          onChange={(event) => setNotes(event.target.value)}
        />
      </form>
    </Modal>
  )
}
