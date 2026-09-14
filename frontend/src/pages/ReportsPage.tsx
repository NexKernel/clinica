import { useMemo, useState } from 'react'
import { BarChart3, Download, FileText, Receipt, Wallet, XCircle } from 'lucide-react'

import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  Input,
  PageHeader,
  StatCard,
  Table,
  type Column,
} from '@/components/ui'
import { useSalesList, useSalesSummary } from '@/features/sales/hooks/useSales'
import { formatDate, formatDateTime, shiftDays, toDateInput } from '@/lib/datetime'
import { formatMoney } from '@/lib/utils'
import type { SaleFilters, SaleListItem } from '@/types'

const MAX_ROWS = 100

interface BreakdownRow {
  label: string
  amount: number
}

const BREAKDOWN_COLUMNS: Column<BreakdownRow>[] = [
  { key: 'label', header: 'Concepto', className: 'font-medium text-foreground', render: (row) => row.label },
  {
    key: 'amount',
    header: 'Importe',
    className: 'w-40 text-right font-semibold text-foreground',
    render: (row) => formatMoney(row.amount),
  },
]

const SALE_COLUMNS: Column<SaleListItem>[] = [
  {
    key: 'document',
    header: 'Comprobante',
    render: (row) => (
      <div className="min-w-0">
        <p className="truncate font-medium text-foreground">{row.full_number}</p>
        <p className="truncate text-xs text-muted">{row.document_label}</p>
      </div>
    ),
  },
  { key: 'customer', header: 'Cliente', className: 'text-muted', render: (row) => row.customer_name },
  {
    key: 'issued',
    header: 'Emitido',
    className: 'w-44 text-muted',
    render: (row) => formatDateTime(row.issued_at),
  },
  { key: 'payment', header: 'Pago', className: 'w-32 text-muted', render: (row) => row.payment_label },
  {
    key: 'total',
    header: 'Total',
    className: 'w-28 text-right font-semibold text-foreground',
    render: (row) => formatMoney(row.total),
  },
]

/** Exporta las filas a CSV, formato estándar para hojas de cálculo. */
function downloadCsv(filename: string, headers: string[], rows: (string | number)[][]): void {
  const escape = (value: string | number) => `"${String(value).replace(/"/g, '""')}"`
  const content = [headers, ...rows].map((row) => row.map(escape).join(';')).join('\n')
  const blob = new Blob([`﻿${content}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function ReportsPage() {
  const [dateFrom, setDateFrom] = useState(() => shiftDays(-29))
  const [dateTo, setDateTo] = useState(() => toDateInput())

  const { summary, isLoading, error } = useSalesSummary(dateFrom, dateTo)

  const filters: SaleFilters = useMemo(
    () => ({ page: 1, page_size: MAX_ROWS, date_from: dateFrom, date_to: dateTo }),
    [dateFrom, dateTo],
  )
  const sales = useSalesList(filters)

  const paymentRows: BreakdownRow[] = Object.entries(summary?.by_payment_method ?? {}).map(
    ([label, amount]) => ({ label, amount }),
  )
  const documentRows: BreakdownRow[] = Object.entries(summary?.by_document_type ?? {}).map(
    ([label, amount]) => ({ label, amount }),
  )

  const exportSales = () => {
    const items = sales.data?.items ?? []
    downloadCsv(
      `ventas_${dateFrom}_${dateTo}.csv`,
      ['Comprobante', 'Tipo', 'Cliente', 'Emitido', 'Medio de pago', 'Total', 'Estado'],
      items.map((item) => [
        item.full_number,
        item.document_label,
        item.customer_name,
        formatDateTime(item.issued_at),
        item.payment_label,
        item.total,
        item.status_label,
      ]),
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Gestión"
        title="Reportes"
        subtitle="Indicadores de caja y comprobantes emitidos por periodo"
        actions={
          <Button
            variant="outline"
            size="sm"
            leftIcon={<Download className="h-4 w-4" />}
            disabled={(sales.data?.items.length ?? 0) === 0}
            onClick={exportSales}
          >
            Exportar CSV
          </Button>
        }
      />

      {error && <Alert variant="danger">{error}</Alert>}

      <Card>
        <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            label="Desde"
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
          />
          <Input
            label="Hasta"
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
          />
          <div className="flex items-end gap-2 sm:col-span-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setDateFrom(toDateInput())
                setDateTo(toDateInput())
              }}
            >
              Hoy
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setDateFrom(shiftDays(-6))
                setDateTo(toDateInput())
              }}
            >
              Últimos 7 días
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setDateFrom(shiftDays(-29))
                setDateTo(toDateInput())
              }}
            >
              Últimos 30 días
            </Button>
          </div>
        </CardBody>
      </Card>

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
        <StatCard
          label="Total del periodo"
          value={formatMoney(summary?.total ?? 0)}
          icon={Wallet}
          isLoading={isLoading}
        />
        <StatCard
          label="Valor de venta"
          value={formatMoney(summary?.subtotal ?? 0)}
          icon={BarChart3}
          tone="info"
          isLoading={isLoading}
        />
        <StatCard
          label="IGV"
          value={formatMoney(summary?.tax ?? 0)}
          icon={FileText}
          tone="info"
          isLoading={isLoading}
        />
        <StatCard
          label="Comprobantes"
          value={summary?.documents ?? 0}
          icon={Receipt}
          hint={`${summary?.cancelled ?? 0} anulados`}
          isLoading={isLoading}
        />
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Por medio de pago" description="Cobros del periodo consultado" />
          <Table
            columns={BREAKDOWN_COLUMNS}
            data={paymentRows}
            keyExtractor={(row) => row.label}
            emptyState={
              <EmptyState
                icon={Wallet}
                title="Sin cobros"
                description="No se registraron comprobantes en el periodo."
              />
            }
          />
        </Card>

        <Card>
          <CardHeader title="Por tipo de comprobante" description="Distribución de la facturación" />
          <Table
            columns={BREAKDOWN_COLUMNS}
            data={documentRows}
            keyExtractor={(row) => row.label}
            emptyState={
              <EmptyState
                icon={Receipt}
                title="Sin comprobantes"
                description="No se emitieron documentos en el periodo."
              />
            }
          />
        </Card>
      </section>

      <Card>
        <CardHeader
          title="Comprobantes del periodo"
          description={`Del ${formatDate(dateFrom)} al ${formatDate(dateTo)} · máximo ${MAX_ROWS} registros`}
        />
        <Table
          columns={SALE_COLUMNS}
          data={sales.data?.items ?? []}
          keyExtractor={(row) => row.id}
          isLoading={sales.isLoading}
          emptyState={
            <EmptyState
              icon={XCircle}
              title="Sin movimientos"
              description="Ajuste el rango de fechas para ver otros periodos."
            />
          }
        />
      </Card>
    </div>
  )
}
