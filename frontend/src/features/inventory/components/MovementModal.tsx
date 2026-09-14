import { useEffect, useState, type FormEvent } from 'react'
import { Save } from 'lucide-react'

import { Alert, Button, Input, Modal, Select, Textarea, type SelectOption } from '@/components/ui'
import { ProductPicker } from '@/features/inventory/components/ProductPicker'
import { useInventoryActions } from '@/features/inventory/hooks/useInventory'
import { getErrorMessage } from '@/services/http'
import {
  MOVEMENT_REASON_LABELS,
  MOVEMENT_TYPES,
  REASONS_BY_TYPE,
  type MovementReason,
  type MovementType,
  type ProductSummary,
} from '@/types'

const TYPE_LABELS: Record<MovementType, string> = {
  ENTRADA: 'Entrada',
  SALIDA: 'Salida',
  AJUSTE: 'Ajuste por inventario',
}

const TYPE_OPTIONS: SelectOption[] = MOVEMENT_TYPES.map((type) => ({
  value: type,
  label: TYPE_LABELS[type],
}))

interface MovementModalProps {
  open: boolean
  product?: ProductSummary | null
  onClose: () => void
}

export function MovementModal({ open, product = null, onClose }: MovementModalProps) {
  const { registerMovement, adjustStock } = useInventoryActions()
  const isLoading = registerMovement.isPending || adjustStock.isPending

  const [selected, setSelected] = useState<ProductSummary | null>(null)
  const [movementType, setMovementType] = useState<MovementType>('ENTRADA')
  const [reason, setReason] = useState<MovementReason>('COMPRA')
  const [quantity, setQuantity] = useState('')
  const [unitCost, setUnitCost] = useState('')
  const [lot, setLot] = useState('')
  const [expiry, setExpiry] = useState('')
  const [notes, setNotes] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setSelected(product)
    setMovementType('ENTRADA')
    setReason('COMPRA')
    setQuantity('')
    setUnitCost('')
    setLot('')
    setExpiry('')
    setNotes('')
    setFormError(null)
  }, [open, product])

  const changeType = (value: MovementType) => {
    setMovementType(value)
    const [firstReason] = REASONS_BY_TYPE[value]
    if (firstReason) setReason(firstReason)
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    if (!selected) return setFormError('Seleccione el producto')
    const amount = Number(quantity)
    if (!Number.isFinite(amount) || amount < 0) return setFormError('Indique una cantidad válida')

    try {
      if (movementType === 'AJUSTE') {
        await adjustStock.mutateAsync({
          productId: selected.id,
          countedStock: amount,
          notes: notes.trim() || undefined,
        })
      } else {
        if (amount <= 0) return setFormError('La cantidad debe ser mayor que cero')
        await registerMovement.mutateAsync({
          product_id: selected.id,
          movement_type: movementType,
          reason,
          quantity: amount,
          unit_cost: unitCost.trim() || null,
          lot: lot.trim() || null,
          expiry_date: expiry || null,
          occurred_at: null,
          notes: notes.trim() || null,
        })
      }
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo registrar el movimiento'))
    }
  }

  const reasonOptions: SelectOption[] = REASONS_BY_TYPE[movementType].map((value) => ({
    value,
    label: MOVEMENT_REASON_LABELS[value],
  }))

  const isAdjustment = movementType === 'AJUSTE'

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Movimiento de almacén"
      description="Entradas, salidas y ajustes quedan registrados en el kardex"
      size="md"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="movement-form"
            size="sm"
            isLoading={isLoading}
            leftIcon={<Save className="h-4 w-4" />}
          >
            Registrar movimiento
          </Button>
        </>
      }
    >
      <form id="movement-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        <ProductPicker
          value={selected}
          onChange={setSelected}
          disabled={isLoading}
          priceMode="purchase"
        />

        {selected && (
          <p className="text-xs text-muted">
            Stock actual: <strong className="text-foreground">{selected.stock}</strong>{' '}
            {selected.unit.toLowerCase()}
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <Select
            label="Tipo de movimiento"
            options={TYPE_OPTIONS}
            value={movementType}
            disabled={isLoading}
            onChange={(event) => changeType(event.target.value as MovementType)}
          />
          <Select
            label="Motivo"
            options={reasonOptions}
            value={reason}
            disabled={isLoading || isAdjustment}
            onChange={(event) => setReason(event.target.value as MovementReason)}
          />
        </div>

        <Input
          label={isAdjustment ? 'Stock contado' : 'Cantidad'}
          type="number"
          hint={
            isAdjustment
              ? 'El sistema calcula la diferencia con el stock registrado'
              : undefined
          }
          value={quantity}
          disabled={isLoading}
          onChange={(event) => setQuantity(event.target.value)}
        />

        {movementType === 'ENTRADA' && (
          <div className="grid gap-4 sm:grid-cols-3">
            <Input
              label="Costo unitario"
              type="number"
              step="0.01"
              hint="Actualiza el precio de compra"
              value={unitCost}
              disabled={isLoading}
              onChange={(event) => setUnitCost(event.target.value)}
            />
            <Input
              label="Lote"
              value={lot}
              disabled={isLoading}
              onChange={(event) => setLot(event.target.value)}
            />
            <Input
              label="Vencimiento"
              type="date"
              value={expiry}
              disabled={isLoading}
              onChange={(event) => setExpiry(event.target.value)}
            />
          </div>
        )}

        <Textarea
          label="Observaciones"
          value={notes}
          disabled={isLoading}
          onChange={(event) => setNotes(event.target.value)}
        />
      </form>
    </Modal>
  )
}
