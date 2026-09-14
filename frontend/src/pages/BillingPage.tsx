import { useEffect, useMemo, useState } from 'react'
import {
  Eye,
  FileText,
  MoreVertical,
  Receipt,
  Search,
  Wallet,
  XCircle,
} from 'lucide-react'

import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  ConfirmDialog,
  Dropdown,
  DropdownItem,
  EmptyState,
  Input,
  PageHeader,
  Pagination,
  Select,
  StatCard,
  Table,
  type Column,
  type SelectOption,
} from '@/components/ui'
import { SaleDetailModal } from '@/features/sales/components/SaleDetailModal'
import { SaleFormModal } from '@/features/sales/components/SaleFormModal'
import { useSaleActions, useSalesList, useSalesSummary } from '@/features/sales/hooks/useSales'
import { formatDateTime, toDateInput } from '@/lib/datetime'
import { formatMoney } from '@/lib/utils'
import { getErrorMessage } from '@/services/http'
import {
  PAYMENT_METHOD_LABELS,
  PAYMENT_METHODS,
  SALE_DOCUMENT_LABELS,
  SALE_DOCUMENT_TYPES,
  type SaleFilters,
  type SaleListItem,
} from '@/types'

const PAGE_SIZE = 10

const DOCUMENT_OPTIONS: SelectOption[] = SALE_DOCUMENT_TYPES.map((type) => ({
  value: type,
  label: SALE_DOCUMENT_LABELS[type],
}))

const PAYMENT_OPTIONS: SelectOption[] = PAYMENT_METHODS.map((method) => ({
  value: method,
  label: PAYMENT_METHOD_LABELS[method],
}))

export function BillingPage() {
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [documentFilter, setDocumentFilter] = useState('')
  const [paymentFilter, setPaymentFilter] = useState('')
  const [day, setDay] = useState(() => toDateInput())
  const [page, setPage] = useState(1)

  const [formOpen, setFormOpen] = useState(false)
  const [detailId, setDetailId] = useState<number | null>(null)
  const [cancelTarget, setCancelTarget] = useState<SaleListItem | null>(null)
  const [feedback, setFeedback] = useState<{ tone: 'success' | 'danger'; text: string } | null>(null)

  const { summary } = useSalesSummary(day, day)
  const { cancel } = useSaleActions()

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const filters: SaleFilters = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      date_from: day,
      date_to: day,
      ...(search ? { search } : {}),
      ...(documentFilter ? { document_type: documentFilter } : {}),
      ...(paymentFilter ? { payment_method: paymentFilter } : {}),
    }),
    [page, day, search, documentFilter, paymentFilter],
  )

  const { data, isLoading, isFetching, error } = useSalesList(filters)

  const confirmCancel = async (reason: string) => {
    if (!cancelTarget) return
    try {
      await cancel.mutateAsync({ id: cancelTarget.id, reason })
      setCancelTarget(null)
      setFeedback({
        tone: 'success',
        text: `Comprobante ${cancelTarget.full_number} anulado; el stock fue repuesto.`,
      })
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo anular el comprobante') })
    }
  }

  const columns: Column<SaleListItem>[] = [
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
    {
      key: 'customer',
      header: 'Cliente',
      className: 'text-muted',
      render: (row) => row.customer_name,
    },
    {
      key: 'issued',
      header: 'Emitido',
      className: 'w-44 text-muted',
      render: (row) => formatDateTime(row.issued_at),
    },
    {
      key: 'payment',
      header: 'Pago',
      className: 'w-32 text-muted',
      render: (row) => row.payment_label,
    },
    {
      key: 'total',
      header: 'Total',
      className: 'w-28 text-right font-semibold text-foreground',
      render: (row) => formatMoney(row.total),
    },
    {
      key: 'status',
      header: 'Estado',
      className: 'w-28',
      render: (row) => (
        <Badge variant={row.status === 'EMITIDA' ? 'success' : 'danger'} dot>
          {row.status_label}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'w-12',
      render: (row) => (
        <Dropdown
          trigger={({ toggle }) => (
            <button
              type="button"
              aria-label={`Acciones de ${row.full_number}`}
              onClick={toggle}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-muted transition-colors hover:bg-primary/10 hover:text-primary-dark"
            >
              <MoreVertical className="h-4 w-4" />
            </button>
          )}
        >
          {({ close }) => (
            <>
              <DropdownItem
                icon={<Eye className="h-4 w-4" />}
                onClick={() => {
                  close()
                  setDetailId(row.id)
                }}
              >
                Ver comprobante
              </DropdownItem>
              {row.status === 'EMITIDA' && (
                <DropdownItem
                  icon={<XCircle className="h-4 w-4" />}
                  variant="danger"
                  onClick={() => {
                    close()
                    setCancelTarget(row)
                  }}
                >
                  Anular
                </DropdownItem>
              )}
            </>
          )}
        </Dropdown>
      ),
    },
  ]

  const paymentBreakdown = Object.entries(summary?.by_payment_method ?? {})

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operación"
        title="Caja"
        subtitle="Notas de venta, boletas y facturas del establecimiento"
        actions={
          <Button size="sm" leftIcon={<Receipt className="h-4 w-4" />} onClick={() => setFormOpen(true)}>
            Nuevo comprobante
          </Button>
        }
      />

      {feedback && <Alert variant={feedback.tone}>{feedback.text}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
        <StatCard
          label="Ingresos del día"
          value={formatMoney(summary?.total ?? 0)}
          icon={Wallet}
          hint="comprobantes emitidos"
        />
        <StatCard label="Comprobantes" value={summary?.documents ?? 0} icon={Receipt} tone="info" />
        <StatCard
          label="IGV del periodo"
          value={formatMoney(summary?.tax ?? 0)}
          icon={FileText}
          tone="info"
        />
        <StatCard
          label="Anulados"
          value={summary?.cancelled ?? 0}
          icon={XCircle}
          tone="danger"
        />
      </section>

      {paymentBreakdown.length > 0 && (
        <Card>
          <CardHeader title="Cobros por medio de pago" description={`Movimiento del ${day}`} />
          <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {paymentBreakdown.map(([method, amount]) => (
              <div key={method} className="rounded-xl border border-border px-4 py-3">
                <p className="caption uppercase tracking-wide">{method}</p>
                <p className="mt-1 text-lg font-semibold text-foreground">{formatMoney(amount)}</p>
              </div>
            ))}
          </CardBody>
        </Card>
      )}

      <Card>
        <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            placeholder="Buscar por cliente o número"
            icon={<Search className="h-[18px] w-[18px]" />}
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />
          <Input
            type="date"
            value={day}
            onChange={(event) => {
              setDay(event.target.value)
              setPage(1)
            }}
          />
          <Select
            options={DOCUMENT_OPTIONS}
            placeholder="Todos los comprobantes"
            value={documentFilter}
            onChange={(event) => {
              setDocumentFilter(event.target.value)
              setPage(1)
            }}
          />
          <Select
            options={PAYMENT_OPTIONS}
            placeholder="Todos los medios de pago"
            value={paymentFilter}
            onChange={(event) => {
              setPaymentFilter(event.target.value)
              setPage(1)
            }}
          />
        </CardBody>

        <Table
          columns={columns}
          data={data?.items ?? []}
          keyExtractor={(row) => row.id}
          isLoading={isLoading}
          className={isFetching && !isLoading ? 'opacity-60 transition-opacity' : undefined}
          emptyState={
            <EmptyState
              icon={Receipt}
              title="Sin comprobantes en esta fecha"
              description="Emita una nota de venta o comprobante desde el botón superior."
              action={
                <Button
                  size="sm"
                  leftIcon={<Receipt className="h-4 w-4" />}
                  onClick={() => setFormOpen(true)}
                >
                  Nuevo comprobante
                </Button>
              }
            />
          }
        />

        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={data?.total ?? 0}
          labels={['comprobante', 'comprobantes']}
          onChange={setPage}
        />
      </Card>

      <SaleFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onIssued={(saleId) => setDetailId(saleId)}
      />

      <SaleDetailModal
        open={detailId !== null}
        saleId={detailId}
        onClose={() => setDetailId(null)}
      />

      <ConfirmDialog
        open={cancelTarget !== null}
        title="Anular comprobante"
        description={
          cancelTarget
            ? `${cancelTarget.full_number} · ${formatMoney(cancelTarget.total)}. El stock de los productos será repuesto.`
            : undefined
        }
        reasonLabel="Motivo de la anulación"
        confirmLabel="Anular comprobante"
        variant="danger"
        isLoading={cancel.isPending}
        onClose={() => setCancelTarget(null)}
        onConfirm={confirmCancel}
      />
    </div>
  )
}
