import { useEffect, useState, type FormEvent } from 'react'
import { Save } from 'lucide-react'

import { Alert, Button, Input, Modal, Select, Switch, type SelectOption } from '@/components/ui'
import { useSaleActions } from '@/features/sales/hooks/useSales'
import { getErrorMessage } from '@/services/http'
import {
  SALE_DOCUMENT_LABELS,
  SALE_DOCUMENT_TYPES,
  type DocumentSeries,
  type SaleDocumentType,
} from '@/types'

const DOCUMENT_OPTIONS: SelectOption[] = SALE_DOCUMENT_TYPES.map((type) => ({
  value: type,
  label: SALE_DOCUMENT_LABELS[type],
}))

interface SeriesFormModalProps {
  open: boolean
  series: DocumentSeries | null
  onClose: () => void
}

export function SeriesFormModal({ open, series, onClose }: SeriesFormModalProps) {
  const isEdit = series !== null
  const { createSeries, updateSeries } = useSaleActions()
  const isLoading = createSeries.isPending || updateSeries.isPending

  const [documentType, setDocumentType] = useState<SaleDocumentType>('NOTA_VENTA')
  const [code, setCode] = useState('')
  const [nextNumber, setNextNumber] = useState('1')
  const [isDefault, setIsDefault] = useState(false)
  const [isActive, setIsActive] = useState(true)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setFormError(null)

    if (series) {
      setDocumentType(series.document_type)
      setCode(series.series)
      setNextNumber(String(series.next_number))
      setIsDefault(series.is_default)
      setIsActive(series.is_active)
      return
    }

    setDocumentType('NOTA_VENTA')
    setCode('')
    setNextNumber('1')
    setIsDefault(false)
    setIsActive(true)
  }, [open, series])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    if (code.trim().length < 2) return setFormError('Indique la serie (por ejemplo, B001)')
    const number = Number(nextNumber)
    if (!Number.isInteger(number) || number < 1) {
      return setFormError('El correlativo debe ser un número mayor que cero')
    }

    const payload = {
      document_type: documentType,
      series: code.trim().toUpperCase(),
      next_number: number,
      is_default: isDefault,
      is_active: isActive,
    }

    try {
      if (series) {
        await updateSeries.mutateAsync({ id: series.id, payload })
      } else {
        await createSeries.mutateAsync(payload)
      }
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo guardar la serie'))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Editar serie' : 'Nueva serie'}
      description="Numeración correlativa de los comprobantes emitidos en caja"
      size="sm"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="series-form"
            size="sm"
            isLoading={isLoading}
            leftIcon={<Save className="h-4 w-4" />}
          >
            {isEdit ? 'Guardar cambios' : 'Crear serie'}
          </Button>
        </>
      }
    >
      <form id="series-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        <Select
          label="Tipo de comprobante"
          options={DOCUMENT_OPTIONS}
          value={documentType}
          disabled={isLoading}
          onChange={(event) => setDocumentType(event.target.value as SaleDocumentType)}
        />

        <Input
          label="Serie"
          placeholder="B001"
          value={code}
          disabled={isLoading}
          onChange={(event) => setCode(event.target.value)}
        />

        <Input
          label="Siguiente número"
          type="number"
          hint="Se completa a 8 dígitos al emitir"
          value={nextNumber}
          disabled={isLoading}
          onChange={(event) => setNextNumber(event.target.value)}
        />

        <Switch
          label="Serie por defecto"
          description="Se usa cuando no se elige una serie al emitir"
          checked={isDefault}
          disabled={isLoading}
          onChange={setIsDefault}
        />

        <Switch
          label="Serie activa"
          checked={isActive}
          disabled={isLoading}
          onChange={setIsActive}
        />
      </form>
    </Modal>
  )
}
