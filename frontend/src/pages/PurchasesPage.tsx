import { useEffect, useMemo, useState } from 'react'
import {
  Building2,
  FileText,
  MoreVertical,
  PackageCheck,
  Pencil,
  Plus,
  Search,
  Truck,
  Wallet,
  XCircle,
} from 'lucide-react'

import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
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
  Tabs,
  type BadgeVariant,
  type Column,
  type SelectOption,
  type TabItem,
} from '@/components/ui'
import { purchasesApi } from '@/features/purchases/api/purchases.api'
import { PurchaseFormModal } from '@/features/purchases/components/PurchaseFormModal'
import { SupplierFormModal } from '@/features/purchases/components/SupplierFormModal'
import {
  usePurchaseActions,
  usePurchasesList,
  usePurchaseStats,
  useSuppliersList,
} from '@/features/purchases/hooks/usePurchases'
import { formatDate } from '@/lib/datetime'
import { formatMoney } from '@/lib/utils'
import { getErrorMessage } from '@/services/http'
import {
  PURCHASE_STATUS_LABELS,
  PURCHASE_STATUSES,
  type Purchase,
  type PurchaseFilters,
  type PurchaseListItem,
  type PurchaseStatus,
  type Supplier,
} from '@/types'

const PAGE_SIZE = 10

const TABS: TabItem[] = [
  { key: 'purchases', label: 'Compras', icon: Truck },
  { key: 'suppliers', label: 'Proveedores', icon: Building2 },
]

const STATUS_VARIANT: Record<PurchaseStatus, BadgeVariant> = {
  BORRADOR: 'warning',
  RECIBIDA: 'success',
  ANULADA: 'neutral',
}

const STATUS_OPTIONS: SelectOption[] = PURCHASE_STATUSES.map((status) => ({
  value: status,
  label: PURCHASE_STATUS_LABELS[status],
}))

export function PurchasesPage() {
  const [tab, setTab] = useState('purchases')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [supplierPage, setSupplierPage] = useState(1)

  const [purchaseOpen, setPurchaseOpen] = useState(false)
  const [supplierOpen, setSupplierOpen] = useState(false)
  const [editingPurchase, setEditingPurchase] = useState<Purchase | null>(null)
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null)
  const [cancelTarget, setCancelTarget] = useState<PurchaseListItem | null>(null)
  const [feedback, setFeedback] = useState<{ tone: 'success' | 'danger'; text: string } | null>(null)

  const { stats } = usePurchaseStats()
  const { receive, cancel } = usePurchaseActions()

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const filters: PurchaseFilters = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      ...(search ? { search } : {}),
      ...(statusFilter ? { status: statusFilter } : {}),
    }),
    [page, search, statusFilter],
  )

  const purchases = usePurchasesList(filters)
  const suppliers = useSuppliersList({ page: supplierPage, page_size: PAGE_SIZE })

  const openPurchase = async (row: PurchaseListItem) => {
    setFeedback(null)
    try {
      setEditingPurchase(await purchasesApi.get(row.id))
      setPurchaseOpen(true)
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo abrir la compra') })
    }
  }

  const receivePurchase = async (row: PurchaseListItem) => {
    setFeedback(null)
    try {
      await receive.mutateAsync(row.id)
      setFeedback({
        tone: 'success',
        text: `Compra ingresada al inventario: se actualizó el stock de ${row.item_count} producto(s).`,
      })
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo recibir la compra') })
    }
  }

  const confirmCancel = async (reason: string) => {
    if (!cancelTarget) return
    try {
      await cancel.mutateAsync({ id: cancelTarget.id, reason })
      setCancelTarget(null)
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo anular la compra') })
    }
  }

  const purchaseColumns: Column<PurchaseListItem>[] = [
    {
      key: 'date',
      header: 'Fecha',
      className: 'w-32 text-muted',
      render: (row) => formatDate(row.issue_date),
    },
    {
      key: 'supplier',
      header: 'Proveedor',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.supplier_name}</p>
          <p className="truncate text-xs text-muted">
            {row.document_label}
            {row.document_number ? ` ${row.document_number}` : ''}
          </p>
        </div>
      ),
    },
    {
      key: 'items',
      header: 'Ítems',
      className: 'w-20 text-muted',
      render: (row) => row.item_count,
    },
    {
      key: 'total',
      header: 'Total',
      className: 'w-32 text-right font-semibold text-foreground',
      render: (row) => formatMoney(row.total),
    },
    {
      key: 'status',
      header: 'Estado',
      className: 'w-32',
      render: (row) => (
        <Badge variant={STATUS_VARIANT[row.status]} dot>
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
              aria-label={`Acciones de la compra a ${row.supplier_name}`}
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
                icon={<Pencil className="h-4 w-4" />}
                onClick={() => {
                  close()
                  void openPurchase(row)
                }}
              >
                {row.status === 'BORRADOR' ? 'Editar compra' : 'Ver detalle'}
              </DropdownItem>
              {row.status === 'BORRADOR' && (
                <DropdownItem
                  icon={<PackageCheck className="h-4 w-4" />}
                  onClick={() => {
                    close()
                    void receivePurchase(row)
                  }}
                >
                  Recibir e ingresar stock
                </DropdownItem>
              )}
              {row.status !== 'ANULADA' && (
                <DropdownItem
                  icon={<XCircle className="h-4 w-4" />}
                  variant="danger"
                  onClick={() => {
                    close()
                    setCancelTarget(row)
                  }}
                >
                  Anular compra
                </DropdownItem>
              )}
            </>
          )}
        </Dropdown>
      ),
    },
  ]

  const supplierColumns: Column<Supplier>[] = [
    {
      key: 'supplier',
      header: 'Proveedor',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.display_name}</p>
          <p className="truncate text-xs text-muted">{row.tax_id ?? 'Sin RUC registrado'}</p>
        </div>
      ),
    },
    {
      key: 'contact',
      header: 'Contacto',
      className: 'text-muted',
      render: (row) => [row.contact_name, row.phone].filter(Boolean).join(' · ') || '—',
    },
    {
      key: 'email',
      header: 'Correo',
      className: 'text-muted',
      render: (row) => row.email ?? '—',
    },
    {
      key: 'status',
      header: 'Estado',
      className: 'w-28',
      render: (row) => (
        <Badge variant={row.is_active ? 'success' : 'neutral'} dot>
          {row.is_active ? 'Activo' : 'Inactivo'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'w-12',
      render: (row) => (
        <Button
          variant="ghost"
          size="icon"
          aria-label={`Editar ${row.display_name}`}
          onClick={() => {
            setEditingSupplier(row)
            setSupplierOpen(true)
          }}
        >
          <Pencil className="h-4 w-4" />
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operación"
        title="Compras"
        subtitle="Proveedores, documentos de compra e ingreso al inventario"
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Building2 className="h-4 w-4" />}
              onClick={() => {
                setEditingSupplier(null)
                setSupplierOpen(true)
              }}
            >
              Proveedor
            </Button>
            <Button
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => {
                setEditingPurchase(null)
                setPurchaseOpen(true)
              }}
            >
              Nueva compra
            </Button>
          </div>
        }
      />

      {feedback && <Alert variant={feedback.tone}>{feedback.text}</Alert>}
      {purchases.error && <Alert variant="danger">{purchases.error}</Alert>}

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
        <StatCard label="Compras en borrador" value={stats?.drafts ?? 0} icon={FileText} tone="warning" />
        <StatCard
          label="Recibidas este mes"
          value={stats?.received_this_month ?? 0}
          icon={PackageCheck}
        />
        <StatCard
          label="Monto del mes"
          value={formatMoney(stats?.amount_this_month ?? 0)}
          icon={Wallet}
        />
        <StatCard
          label="Proveedores activos"
          value={stats?.active_suppliers ?? 0}
          icon={Building2}
          tone="info"
        />
      </section>

      <Tabs items={TABS} active={tab} onChange={setTab} />

      {tab === 'purchases' && (
        <Card>
          <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Input
              placeholder="Buscar por proveedor o número"
              icon={<Search className="h-[18px] w-[18px]" />}
              value={searchInput}
              containerClassName="lg:col-span-3"
              onChange={(event) => setSearchInput(event.target.value)}
            />
            <Select
              options={STATUS_OPTIONS}
              placeholder="Todos los estados"
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value)
                setPage(1)
              }}
            />
          </CardBody>

          <Table
            columns={purchaseColumns}
            data={purchases.data?.items ?? []}
            keyExtractor={(row) => row.id}
            isLoading={purchases.isLoading}
            emptyState={
              <EmptyState
                icon={Truck}
                title="Sin compras registradas"
                description="Registre la compra y márquela como recibida para actualizar el stock."
              />
            }
          />

          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={purchases.data?.total ?? 0}
            labels={['compra', 'compras']}
            onChange={setPage}
          />
        </Card>
      )}

      {tab === 'suppliers' && (
        <Card>
          <Table
            columns={supplierColumns}
            data={suppliers.data?.items ?? []}
            keyExtractor={(row) => row.id}
            isLoading={suppliers.isLoading}
            emptyState={
              <EmptyState
                icon={Building2}
                title="Sin proveedores"
                description="Registre a los proveedores con los que trabaja el policlínico."
              />
            }
          />

          <Pagination
            page={supplierPage}
            pageSize={PAGE_SIZE}
            total={suppliers.data?.total ?? 0}
            labels={['proveedor', 'proveedores']}
            onChange={setSupplierPage}
          />
        </Card>
      )}

      <PurchaseFormModal
        open={purchaseOpen}
        purchase={editingPurchase}
        onClose={() => setPurchaseOpen(false)}
      />

      <SupplierFormModal
        open={supplierOpen}
        supplier={editingSupplier}
        onClose={() => setSupplierOpen(false)}
      />

      <ConfirmDialog
        open={cancelTarget !== null}
        title="Anular compra"
        description={
          cancelTarget?.status === 'RECIBIDA'
            ? 'El stock ingresado por esta compra será revertido.'
            : cancelTarget?.supplier_name
        }
        reasonLabel="Motivo de la anulación"
        confirmLabel="Anular compra"
        variant="danger"
        isLoading={cancel.isPending}
        onClose={() => setCancelTarget(null)}
        onConfirm={confirmCancel}
      />
    </div>
  )
}
