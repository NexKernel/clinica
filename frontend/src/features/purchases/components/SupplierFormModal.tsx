import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { Save } from 'lucide-react'

import { Alert, Button, Input, Modal, Switch, Textarea } from '@/components/ui'
import { usePurchaseActions } from '@/features/purchases/hooks/usePurchases'
import { getErrorMessage } from '@/services/http'
import type { Supplier, SupplierPayload } from '@/types'

const emptyValues = (): SupplierPayload => ({
  tax_id: '',
  business_name: '',
  trade_name: '',
  contact_name: '',
  phone: '',
  email: '',
  address: '',
  notes: '',
  is_active: true,
})

interface SupplierFormModalProps {
  open: boolean
  supplier: Supplier | null
  onClose: () => void
}

export function SupplierFormModal({ open, supplier, onClose }: SupplierFormModalProps) {
  const isEdit = supplier !== null
  const { createSupplier, updateSupplier } = usePurchaseActions()
  const isLoading = createSupplier.isPending || updateSupplier.isPending

  const [values, setValues] = useState<SupplierPayload>(emptyValues)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setFormError(null)
    setValues(
      supplier
        ? {
            tax_id: supplier.tax_id ?? '',
            business_name: supplier.business_name,
            trade_name: supplier.trade_name ?? '',
            contact_name: supplier.contact_name ?? '',
            phone: supplier.phone ?? '',
            email: supplier.email ?? '',
            address: supplier.address ?? '',
            notes: supplier.notes ?? '',
            is_active: supplier.is_active,
          }
        : emptyValues(),
    )
  }, [open, supplier])

  const setField =
    (field: keyof SupplierPayload) =>
    (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setValues((prev) => ({ ...prev, [field]: event.target.value }))

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    if (values.business_name.trim().length < 3) {
      return setFormError('Indique la razón social del proveedor')
    }
    const taxId = (values.tax_id ?? '').trim()
    if (taxId && (taxId.length !== 11 || !/^\d+$/.test(taxId))) {
      return setFormError('El RUC debe tener 11 dígitos')
    }

    const clean = (value: string | null) => {
      const trimmed = (value ?? '').trim()
      return trimmed === '' ? null : trimmed
    }

    const payload: SupplierPayload = {
      tax_id: clean(values.tax_id),
      business_name: values.business_name.trim(),
      trade_name: clean(values.trade_name),
      contact_name: clean(values.contact_name),
      phone: clean(values.phone),
      email: clean(values.email),
      address: clean(values.address),
      notes: clean(values.notes),
      is_active: values.is_active,
    }

    try {
      if (supplier) {
        await updateSupplier.mutateAsync({ id: supplier.id, payload })
      } else {
        await createSupplier.mutateAsync(payload)
      }
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo guardar el proveedor'))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Editar proveedor' : 'Nuevo proveedor'}
      description="Datos del proveedor de medicamentos, insumos y productos"
      size="md"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="supplier-form"
            size="sm"
            isLoading={isLoading}
            leftIcon={<Save className="h-4 w-4" />}
          >
            {isEdit ? 'Guardar cambios' : 'Registrar proveedor'}
          </Button>
        </>
      }
    >
      <form id="supplier-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        <div className="grid gap-4 sm:grid-cols-[10rem_1fr]">
          <Input
            label="RUC"
            placeholder="20512345678"
            value={values.tax_id ?? ''}
            disabled={isLoading}
            onChange={setField('tax_id')}
          />
          <Input
            label="Razón social"
            value={values.business_name}
            disabled={isLoading}
            onChange={setField('business_name')}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Nombre comercial"
            value={values.trade_name ?? ''}
            disabled={isLoading}
            onChange={setField('trade_name')}
          />
          <Input
            label="Contacto"
            value={values.contact_name ?? ''}
            disabled={isLoading}
            onChange={setField('contact_name')}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Teléfono"
            value={values.phone ?? ''}
            disabled={isLoading}
            onChange={setField('phone')}
          />
          <Input
            label="Correo"
            type="email"
            value={values.email ?? ''}
            disabled={isLoading}
            onChange={setField('email')}
          />
        </div>

        <Input
          label="Dirección"
          value={values.address ?? ''}
          disabled={isLoading}
          onChange={setField('address')}
        />

        <Textarea
          label="Observaciones"
          value={values.notes ?? ''}
          disabled={isLoading}
          onChange={setField('notes')}
        />

        <Switch
          label="Proveedor activo"
          description="Los proveedores inactivos no aparecen al registrar compras"
          checked={values.is_active}
          disabled={isLoading}
          onChange={(checked) => setValues((prev) => ({ ...prev, is_active: checked }))}
        />
      </form>
    </Modal>
  )
}
