import { Printer } from 'lucide-react'

import {
  Alert,
  Badge,
  Button,
  DataSummary,
  LoadingState,
  Modal,
  Table,
  type Column,
} from '@/components/ui'
import { useSale } from '@/features/sales/hooks/useSales'
import { formatDateTime } from '@/lib/datetime'
import { formatMoney } from '@/lib/utils'
import type { SaleItem } from '@/types'

const ITEM_COLUMNS: Column<SaleItem>[] = [
  {
    key: 'description',
    header: 'Descripción',
    render: (row) => (
      <div className="min-w-0">
        <p className="truncate text-foreground">{row.description}</p>
        <p className="text-xs text-muted">{row.unit.toLowerCase()}</p>
      </div>
    ),
  },
  { key: 'quantity', header: 'Cant.', className: 'w-20 text-muted', render: (row) => row.quantity },
  {
    key: 'price',
    header: 'P. unitario',
    className: 'w-28 text-right text-muted',
    render: (row) => formatMoney(row.unit_price),
  },
  {
    key: 'discount',
    header: 'Dscto.',
    className: 'w-24 text-right text-muted',
    render: (row) => formatMoney(row.discount),
  },
  {
    key: 'subtotal',
    header: 'Importe',
    className: 'w-28 text-right font-semibold text-foreground',
    render: (row) => formatMoney(row.subtotal),
  },
]

interface SaleDetailModalProps {
  open: boolean
  saleId: number | null
  onClose: () => void
}

export function SaleDetailModal({ open, saleId, onClose }: SaleDetailModalProps) {
  const { sale, isLoading, error } = useSale(open ? saleId : null)

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={sale ? `${sale.document_label} ${sale.full_number}` : 'Comprobante'}
      description={sale ? formatDateTime(sale.issued_at) : undefined}
      size="lg"
      footer={
        sale ? (
          <Button
            variant="outline"
            size="sm"
            leftIcon={<Printer className="h-4 w-4" />}
            onClick={() => window.print()}
          >
            Imprimir
          </Button>
        ) : undefined
      }
    >
      {isLoading && <LoadingState label="Cargando comprobante" />}
      {error && <Alert variant="danger">{error}</Alert>}

      {sale && (
        <div className="space-y-5">
          {sale.is_cancelled && (
            <Alert variant="danger">
              Comprobante anulado{sale.cancel_reason ? `: ${sale.cancel_reason}` : ''}
            </Alert>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={sale.is_cancelled ? 'danger' : 'success'} dot>
              {sale.status_label}
            </Badge>
            <Badge variant="primary">{sale.payment_label}</Badge>
            {sale.is_electronic && <Badge variant="info">Comprobante electrónico</Badge>}
          </div>

          <DataSummary
            items={[
              { label: 'Cliente', value: sale.customer_name },
              {
                label: 'Documento',
                value: [sale.customer_document_type, sale.customer_document_number]
                  .filter(Boolean)
                  .join(' '),
              },
              { label: 'Dirección', value: sale.customer_address },
            ]}
          />

          <Table columns={ITEM_COLUMNS} data={sale.items} keyExtractor={(row) => row.id} />

          <div className="ml-auto w-full max-w-xs space-y-1 text-sm">
            <div className="flex justify-between text-muted">
              <span>Valor de venta</span>
              <span>{formatMoney(sale.subtotal)}</span>
            </div>
            <div className="flex justify-between text-muted">
              <span>IGV ({sale.tax_rate}%)</span>
              <span>{formatMoney(sale.tax)}</span>
            </div>
            {Number(sale.discount) > 0 && (
              <div className="flex justify-between text-muted">
                <span>Descuentos</span>
                <span>{formatMoney(sale.discount)}</span>
              </div>
            )}
            <div className="flex justify-between border-t border-border pt-1 text-base font-semibold text-foreground">
              <span>Total</span>
              <span>{formatMoney(sale.total)}</span>
            </div>
          </div>

          {sale.notes && (
            <p className="rounded-xl bg-background/70 px-4 py-3 text-sm text-foreground">
              {sale.notes}
            </p>
          )}
        </div>
      )}
    </Modal>
  )
}
