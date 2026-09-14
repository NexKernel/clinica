import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { Save } from 'lucide-react'

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
import { useCategories, useInventoryActions } from '@/features/inventory/hooks/useInventory'
import { getErrorMessage } from '@/services/http'
import {
  EXPIRY_ALERT_DAYS,
  PRODUCT_KIND_LABELS,
  PRODUCT_KINDS,
  type Product,
  type ProductKind,
  type ProductPayload,
} from '@/types'

const KIND_OPTIONS: SelectOption[] = PRODUCT_KINDS.map((kind) => ({
  value: kind,
  label: PRODUCT_KIND_LABELS[kind],
}))

const UNIT_OPTIONS: SelectOption[] = [
  'UNIDAD',
  'TABLETA',
  'CAPSULA',
  'FRASCO',
  'AMPOLLA',
  'CAJA',
  'BLISTER',
  'PAR',
  'JUEGO',
  'METRO',
].map((value) => ({ value, label: value.charAt(0) + value.slice(1).toLowerCase() }))

interface FormValues extends Omit<ProductPayload, 'initial_stock'> {
  initial_stock: string
}

const emptyValues = (): FormValues => ({
  code: '',
  name: '',
  kind: 'MEDICAMENTO',
  category_id: null,
  barcode: '',
  presentation: '',
  concentration: '',
  unit: 'UNIDAD',
  laboratory: '',
  requires_prescription: false,
  purchase_price: '0.00',
  sale_price: '0.00',
  min_stock: 0,
  max_stock: 0,
  location: '',
  lot: '',
  expiry_date: '',
  notes: '',
  is_active: true,
  initial_stock: '0',
})

interface ProductFormModalProps {
  open: boolean
  product: Product | null
  onClose: () => void
}

export function ProductFormModal({ open, product, onClose }: ProductFormModalProps) {
  const isEdit = product !== null
  const { categories } = useCategories()
  const { createProduct, updateProduct } = useInventoryActions()
  const isLoading = createProduct.isPending || updateProduct.isPending

  const [values, setValues] = useState<FormValues>(emptyValues)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setFormError(null)

    if (product) {
      setValues({
        code: product.code,
        name: product.name,
        kind: product.kind,
        category_id: product.category_id,
        barcode: product.barcode ?? '',
        presentation: product.presentation ?? '',
        concentration: product.concentration ?? '',
        unit: product.unit,
        laboratory: product.laboratory ?? '',
        requires_prescription: product.requires_prescription,
        purchase_price: product.purchase_price,
        sale_price: product.sale_price,
        min_stock: product.min_stock,
        max_stock: product.max_stock,
        location: product.location ?? '',
        lot: product.lot ?? '',
        expiry_date: product.expiry_date ?? '',
        notes: product.notes ?? '',
        is_active: product.is_active,
        initial_stock: '0',
      })
      return
    }

    setValues(emptyValues())
  }, [open, product])

  const setField =
    (field: keyof FormValues) =>
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setValues((prev) => ({ ...prev, [field]: event.target.value }))

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    if (values.name.trim().length < 2) return setFormError('Indique el nombre del producto')
    if (values.max_stock > 0 && values.max_stock < values.min_stock) {
      return setFormError('El stock máximo debe ser mayor o igual al mínimo')
    }

    const clean = (value: string | null | undefined) => {
      const trimmed = (value ?? '').trim()
      return trimmed === '' ? null : trimmed
    }

    const base: ProductPayload = {
      name: values.name.trim(),
      kind: values.kind,
      category_id: values.category_id,
      barcode: clean(values.barcode),
      presentation: clean(values.presentation),
      concentration: clean(values.concentration),
      unit: values.unit,
      laboratory: clean(values.laboratory),
      requires_prescription: values.requires_prescription,
      purchase_price: values.purchase_price || '0.00',
      sale_price: values.sale_price || '0.00',
      min_stock: Number(values.min_stock) || 0,
      max_stock: Number(values.max_stock) || 0,
      location: clean(values.location),
      lot: clean(values.lot),
      expiry_date: clean(values.expiry_date),
      notes: clean(values.notes),
      is_active: values.is_active,
    }

    try {
      if (product) {
        await updateProduct.mutateAsync({ id: product.id, payload: { ...base, code: values.code } })
      } else {
        await createProduct.mutateAsync({
          ...base,
          code: clean(values.code),
          initial_stock: Number(values.initial_stock) || 0,
        })
      }
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo guardar el producto'))
    }
  }

  const categoryOptions: SelectOption[] = categories.map((item) => ({
    value: String(item.id),
    label: item.name,
  }))

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Editar producto' : 'Nuevo producto'}
      description={
        isEdit
          ? `${product.code} · stock actual ${product.stock} ${product.unit.toLowerCase()}`
          : 'El stock posterior se controla mediante compras y movimientos'
      }
      size="xl"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="product-form"
            size="sm"
            isLoading={isLoading}
            leftIcon={<Save className="h-4 w-4" />}
          >
            {isEdit ? 'Guardar cambios' : 'Registrar producto'}
          </Button>
        </>
      }
    >
      <form id="product-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        <Input
          label="Nombre"
          placeholder="Paracetamol"
          value={values.name}
          disabled={isLoading}
          onChange={setField('name')}
        />

        <div className="grid gap-4 sm:grid-cols-3">
          <Input
            label="Concentración"
            placeholder="500 mg"
            value={values.concentration ?? ''}
            disabled={isLoading}
            onChange={setField('concentration')}
          />
          <Input
            label="Presentación"
            placeholder="Tableta, frasco 120 ml"
            value={values.presentation ?? ''}
            disabled={isLoading}
            onChange={setField('presentation')}
          />
          <Select
            label="Unidad"
            options={UNIT_OPTIONS}
            value={values.unit}
            disabled={isLoading}
            onChange={setField('unit')}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <Select
            label="Tipo"
            options={KIND_OPTIONS}
            value={values.kind}
            disabled={isLoading}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, kind: event.target.value as ProductKind }))
            }
          />
          <Select
            label="Categoría"
            options={categoryOptions}
            placeholder="Sin categoría"
            value={values.category_id ? String(values.category_id) : ''}
            disabled={isLoading}
            onChange={(event) =>
              setValues((prev) => ({
                ...prev,
                category_id: event.target.value ? Number(event.target.value) : null,
              }))
            }
          />
          <Input
            label="Código"
            placeholder={isEdit ? undefined : 'Se genera automáticamente'}
            value={values.code ?? ''}
            disabled={isLoading}
            onChange={setField('code')}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <Input
            label="Laboratorio / marca"
            value={values.laboratory ?? ''}
            disabled={isLoading}
            onChange={setField('laboratory')}
          />
          <Input
            label="Código de barras"
            value={values.barcode ?? ''}
            disabled={isLoading}
            onChange={setField('barcode')}
          />
          <Input
            label="Ubicación"
            placeholder="Estante A-3"
            value={values.location ?? ''}
            disabled={isLoading}
            onChange={setField('location')}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-4">
          <Input
            label="Precio de compra"
            type="number"
            step="0.01"
            value={values.purchase_price}
            disabled={isLoading}
            onChange={setField('purchase_price')}
          />
          <Input
            label="Precio de venta"
            type="number"
            step="0.01"
            value={values.sale_price}
            disabled={isLoading}
            onChange={setField('sale_price')}
          />
          <Input
            label="Stock mínimo"
            type="number"
            hint="Genera la alerta de reposición"
            value={String(values.min_stock)}
            disabled={isLoading}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, min_stock: Number(event.target.value) || 0 }))
            }
          />
          <Input
            label="Stock máximo"
            type="number"
            hint="Define la compra sugerida"
            value={String(values.max_stock)}
            disabled={isLoading}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, max_stock: Number(event.target.value) || 0 }))
            }
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Lote"
            placeholder="L-2026-08"
            hint="Lote en existencia"
            value={values.lot ?? ''}
            disabled={isLoading}
            onChange={setField('lot')}
          />
          <Input
            label="Fecha de vencimiento"
            type="date"
            hint={`Avisa ${EXPIRY_ALERT_DAYS} días antes`}
            value={values.expiry_date ?? ''}
            disabled={isLoading}
            onChange={setField('expiry_date')}
          />
        </div>

        {!isEdit && (
          <Input
            label="Stock inicial"
            type="number"
            hint="Se registra en el kardex como inventario inicial"
            value={values.initial_stock}
            disabled={isLoading}
            onChange={setField('initial_stock')}
          />
        )}

        <Textarea
          label="Observaciones"
          value={values.notes ?? ''}
          disabled={isLoading}
          onChange={setField('notes')}
        />

        <Switch
          label="Requiere receta médica"
          description="Se advierte al dispensar el producto"
          checked={values.requires_prescription}
          disabled={isLoading}
          onChange={(checked) =>
            setValues((prev) => ({ ...prev, requires_prescription: checked }))
          }
        />

        <Switch
          label="Producto activo"
          description="Los productos inactivos no aparecen en ventas ni compras"
          checked={values.is_active}
          disabled={isLoading}
          onChange={(checked) => setValues((prev) => ({ ...prev, is_active: checked }))}
        />
      </form>
    </Modal>
  )
}
