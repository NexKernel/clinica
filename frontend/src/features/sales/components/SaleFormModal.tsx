import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Plus, Receipt, Trash2 } from 'lucide-react'

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
import { ServicePicker } from '@/features/catalog/components/ServicePicker'
import { ProductPicker } from '@/features/inventory/components/ProductPicker'
import { PatientPicker } from '@/features/patients/components/PatientPicker'
import { useDocumentSeries, useSaleActions } from '@/features/sales/hooks/useSales'
import { useTaxRate } from '@/features/settings/hooks/useSettings'
import { formatMoney, formatPercent } from '@/lib/utils'
import { getErrorMessage } from '@/services/http'
import {
  PAYMENT_METHOD_LABELS,
  PAYMENT_METHODS,
  SALE_DOCUMENT_LABELS,
  SALE_DOCUMENT_TYPES,
  type MedicalService,
  type PatientSummary,
  type PaymentMethod,
  type ProductSummary,
  type SaleDocumentType,
  type SaleItemPayload,
} from '@/types'

const DOCUMENT_OPTIONS: SelectOption[] = SALE_DOCUMENT_TYPES.map((type) => ({
  value: type,
  label: SALE_DOCUMENT_LABELS[type],
}))

const PAYMENT_OPTIONS: SelectOption[] = PAYMENT_METHODS.map((method) => ({
  value: method,
  label: PAYMENT_METHOD_LABELS[method],
}))

type LineKind = 'PRODUCT' | 'SERVICE'

interface LineDraft {
  kind: LineKind
  product: ProductSummary | null
  service: MedicalService | null
  description: string
  quantity: string
  unitPrice: string
  discount: string
}

const emptyLine = (kind: LineKind = 'SERVICE'): LineDraft => ({
  kind,
  product: null,
  service: null,
  description: '',
  quantity: '1',
  unitPrice: '',
  discount: '0',
})

const lineTotal = (line: LineDraft): number => {
  const quantity = Number(line.quantity) || 0
  const price = Number(line.unitPrice) || 0
  const discount = Number(line.discount) || 0
  return Math.max(quantity * price - discount, 0)
}

interface SaleFormModalProps {
  open: boolean
  onClose: () => void
  onIssued?: (saleId: number) => void
}

export function SaleFormModal({ open, onClose, onIssued }: SaleFormModalProps) {
  const { series } = useDocumentSeries(true)
  const { create } = useSaleActions()
  const configuredTaxRate = useTaxRate()

  const [documentType, setDocumentType] = useState<SaleDocumentType>('NOTA_VENTA')
  const [seriesCode, setSeriesCode] = useState('')
  const [patient, setPatient] = useState<PatientSummary | null>(null)
  const [customerName, setCustomerName] = useState('')
  const [customerDocument, setCustomerDocument] = useState('')
  const [customerAddress, setCustomerAddress] = useState('')
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('EFECTIVO')
  const [applyTax, setApplyTax] = useState(true)
  const [notes, setNotes] = useState('')
  const [lines, setLines] = useState<LineDraft[]>([emptyLine()])
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setDocumentType('NOTA_VENTA')
    setSeriesCode('')
    setPatient(null)
    setCustomerName('')
    setCustomerDocument('')
    setCustomerAddress('')
    setPaymentMethod('EFECTIVO')
    setApplyTax(true)
    setNotes('')
    setLines([emptyLine()])
    setFormError(null)
  }, [open])

  const seriesOptions: SelectOption[] = useMemo(
    () =>
      series
        .filter((item) => item.document_type === documentType)
        .map((item) => ({ value: item.series, label: item.series })),
    [series, documentType],
  )

  const updateLine = (index: number, patch: Partial<LineDraft>) =>
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)))

  const total = lines.reduce((sum, line) => sum + lineTotal(line), 0)
  const taxRate = applyTax ? configuredTaxRate : 0
  const base = taxRate ? total / (1 + taxRate) : total
  const isFactura = documentType === 'FACTURA'

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (create.isPending) return

    const validLines = lines.filter(
      (line) => line.product !== null || line.service !== null || line.description.trim() !== '',
    )
    if (validLines.length === 0) return setFormError('Agregue al menos un ítem al comprobante')
    if (validLines.some((line) => Number(line.quantity) <= 0)) {
      return setFormError('Las cantidades deben ser mayores que cero')
    }
    if (!patient && customerName.trim() === '') {
      return setFormError('Indique el paciente o el nombre del cliente')
    }
    if (isFactura && customerDocument.trim().length !== 11) {
      return setFormError('La factura requiere el RUC del cliente (11 dígitos)')
    }

    const items: SaleItemPayload[] = validLines.map((line) => ({
      product_id: line.product?.id ?? null,
      service_id: line.kind === 'SERVICE' ? (line.service?.id ?? null) : null,
      description: line.description.trim() || null,
      quantity: Number(line.quantity),
      unit_price: line.unitPrice.trim() || null,
      discount: line.discount.trim() || '0',
    }))

    try {
      const sale = await create.mutateAsync({
        document_type: documentType,
        series: seriesCode || null,
        patient_id: patient?.id ?? null,
        encounter_id: null,
        customer_document_type: isFactura ? 'RUC' : null,
        customer_document_number: customerDocument.trim() || null,
        customer_name: customerName.trim() || null,
        customer_address: customerAddress.trim() || null,
        payment_method: paymentMethod,
        issued_at: null,
        apply_tax: applyTax,
        notes: notes.trim() || null,
        items,
      })
      onIssued?.(sale.id)
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo emitir el comprobante'))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Nuevo comprobante"
      description="Nota de venta, boleta o factura. El stock se descuenta al emitir."
      size="xl"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={create.isPending} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="sale-form"
            size="sm"
            isLoading={create.isPending}
            leftIcon={<Receipt className="h-4 w-4" />}
          >
            Emitir comprobante
          </Button>
        </>
      }
    >
      <form id="sale-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        <div className="grid gap-4 sm:grid-cols-3">
          <Select
            label="Tipo de comprobante"
            options={DOCUMENT_OPTIONS}
            value={documentType}
            disabled={create.isPending}
            onChange={(event) => {
              setDocumentType(event.target.value as SaleDocumentType)
              setSeriesCode('')
            }}
          />
          <Select
            label="Serie"
            options={seriesOptions}
            placeholder="Serie por defecto"
            value={seriesCode}
            disabled={create.isPending}
            onChange={(event) => setSeriesCode(event.target.value)}
          />
          <Select
            label="Medio de pago"
            options={PAYMENT_OPTIONS}
            value={paymentMethod}
            disabled={create.isPending}
            onChange={(event) => setPaymentMethod(event.target.value as PaymentMethod)}
          />
        </div>

        <PatientPicker
          label="Paciente (opcional)"
          value={patient}
          disabled={create.isPending}
          onChange={(value) => {
            setPatient(value)
            if (value) setCustomerName(value.full_name)
          }}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label={isFactura ? 'Razón social' : 'Nombre del cliente'}
            placeholder="Cliente varios"
            value={customerName}
            disabled={create.isPending}
            onChange={(event) => setCustomerName(event.target.value)}
          />
          <Input
            label={isFactura ? 'RUC' : 'Documento'}
            placeholder={isFactura ? '20481234567' : 'DNI o RUC'}
            value={customerDocument}
            disabled={create.isPending}
            onChange={(event) => setCustomerDocument(event.target.value)}
          />
        </div>

        {isFactura && (
          <Input
            label="Dirección fiscal"
            value={customerAddress}
            disabled={create.isPending}
            onChange={(event) => setCustomerAddress(event.target.value)}
          />
        )}

        <div className="space-y-3">
          <p className="caption uppercase tracking-wide">Detalle</p>

          {lines.map((line, index) => (
            <div key={index} className="space-y-3 rounded-xl border border-border p-3">
              <div className="flex items-start gap-3">
                <Select
                  options={[
                    { value: 'SERVICE', label: 'Servicio' },
                    { value: 'PRODUCT', label: 'Producto' },
                  ]}
                  value={line.kind}
                  containerClassName="w-36"
                  disabled={create.isPending}
                  onChange={(event) =>
                    updateLine(index, {
                      ...emptyLine(event.target.value as LineKind),
                      quantity: line.quantity,
                    })
                  }
                />

                {line.kind === 'SERVICE' ? (
                  <ServicePicker
                    label=""
                    value={line.service}
                    disabled={create.isPending}
                    onChange={(service) =>
                      updateLine(index, {
                        service,
                        description: service?.name ?? '',
                        unitPrice: service ? service.price : '',
                      })
                    }
                  />
                ) : (
                  <ProductPicker
                    label=""
                    value={line.product}
                    disabled={create.isPending}
                    onChange={(product) =>
                      updateLine(index, {
                        product,
                        description: product?.full_name ?? '',
                        unitPrice: product ? product.sale_price : '',
                      })
                    }
                  />
                )}

                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Quitar ítem"
                  disabled={create.isPending || lines.length === 1}
                  onClick={() => setLines((prev) => prev.filter((_, i) => i !== index))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>

              <div className="grid gap-3 sm:grid-cols-4">
                <Input
                  label="Cantidad"
                  type="number"
                  value={line.quantity}
                  disabled={create.isPending}
                  onChange={(event) => updateLine(index, { quantity: event.target.value })}
                />
                <Input
                  label="Precio unitario"
                  type="number"
                  step="0.01"
                  value={line.unitPrice}
                  disabled={create.isPending}
                  onChange={(event) => updateLine(index, { unitPrice: event.target.value })}
                />
                <Input
                  label="Descuento"
                  type="number"
                  step="0.01"
                  value={line.discount}
                  disabled={create.isPending}
                  onChange={(event) => updateLine(index, { discount: event.target.value })}
                />
                <div className="flex items-end pb-3">
                  <span className="text-sm font-semibold text-foreground">
                    {formatMoney(lineTotal(line))}
                  </span>
                </div>
              </div>

              {line.product && Number(line.quantity) > line.product.stock && (
                <Alert variant="danger">
                  Stock insuficiente: quedan {line.product.stock} {line.product.unit.toLowerCase()}.
                </Alert>
              )}

              {line.product?.is_expired && (
                <Alert variant="danger">
                  El lote en existencia de {line.product.name} está vencido: retírelo del stock
                  antes de dispensarlo.
                </Alert>
              )}
            </div>
          ))}

          <Button
            variant="outline"
            size="sm"
            leftIcon={<Plus className="h-4 w-4" />}
            disabled={create.isPending}
            onClick={() => setLines((prev) => [...prev, emptyLine()])}
          >
            Agregar ítem
          </Button>
        </div>

        <Switch
          label="Desglosar IGV"
          description="Los precios de lista incluyen IGV; el impuesto se desglosa del total"
          checked={applyTax}
          disabled={create.isPending}
          onChange={setApplyTax}
        />

        <div className="rounded-xl bg-background/70 px-4 py-3 text-sm">
          <div className="flex justify-between text-muted">
            <span>Valor de venta</span>
            <span>{formatMoney(base)}</span>
          </div>
          <div className="flex justify-between text-muted">
            <span>IGV{applyTax ? ` (${formatPercent(configuredTaxRate)})` : ''}</span>
            <span>{formatMoney(total - base)}</span>
          </div>
          <div className="mt-1 flex justify-between border-t border-border pt-1 text-base font-semibold text-foreground">
            <span>Total a pagar</span>
            <span>{formatMoney(total)}</span>
          </div>
        </div>

        <Textarea
          label="Observaciones"
          value={notes}
          disabled={create.isPending}
          onChange={(event) => setNotes(event.target.value)}
        />
      </form>
    </Modal>
  )
}
