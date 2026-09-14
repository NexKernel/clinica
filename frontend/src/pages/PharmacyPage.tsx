import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Boxes,
  CalendarClock,
  MoreVertical,
  PackageSearch,
  Pencil,
  Pill,
  Plus,
  Search,
  ShieldOff,
  ShieldCheck,
  Wallet,
} from 'lucide-react'

import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
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
  type Column,
  type SelectOption,
  type TabItem,
} from '@/components/ui'
import { MovementModal } from '@/features/inventory/components/MovementModal'
import { ProductFormModal } from '@/features/inventory/components/ProductFormModal'
import {
  useCategories,
  useInventoryActions,
  useInventoryStats,
  useMovementsList,
  useExpiringStock,
  useProductsList,
  useStockAlerts,
} from '@/features/inventory/hooks/useInventory'
import { formatDate, formatDateTime } from '@/lib/datetime'
import { formatMoney } from '@/lib/utils'
import { getErrorMessage } from '@/services/http'
import {
  EXPIRY_ALERT_DAYS,
  PRODUCT_KIND_LABELS,
  PRODUCT_KINDS,
  type ExpiringItem,
  type LowStockItem,
  type Movement,
  type MovementFilters,
  type Product,
  type ProductFilters,
} from '@/types'

const PAGE_SIZE = 10

const TABS: TabItem[] = [
  { key: 'products', label: 'Productos', icon: Pill },
  { key: 'alerts', label: 'Reposición', icon: AlertTriangle },
  { key: 'expiring', label: 'Vencimientos', icon: CalendarClock },
  { key: 'kardex', label: 'Kardex', icon: Boxes },
]

const KIND_OPTIONS: SelectOption[] = PRODUCT_KINDS.map((kind) => ({
  value: kind,
  label: PRODUCT_KIND_LABELS[kind],
}))

export function PharmacyPage() {
  const [tab, setTab] = useState('products')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [kindFilter, setKindFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [page, setPage] = useState(1)
  const [kardexPage, setKardexPage] = useState(1)

  const [productOpen, setProductOpen] = useState(false)
  const [movementOpen, setMovementOpen] = useState(false)
  const [selected, setSelected] = useState<Product | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const { stats } = useInventoryStats()
  const { categories } = useCategories()
  const { alerts } = useStockAlerts()
  const { items: expiring } = useExpiringStock()
  const { setProductStatus } = useInventoryActions()

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const productFilters: ProductFilters = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      ...(search ? { search } : {}),
      ...(kindFilter ? { kind: kindFilter } : {}),
      ...(categoryFilter ? { category_id: Number(categoryFilter) } : {}),
    }),
    [page, search, kindFilter, categoryFilter],
  )

  const movementFilters: MovementFilters = useMemo(
    () => ({ page: kardexPage, page_size: PAGE_SIZE }),
    [kardexPage],
  )

  const products = useProductsList(productFilters)
  const movements = useMovementsList(movementFilters)

  const toggleStatus = async (product: Product) => {
    setActionError(null)
    try {
      await setProductStatus.mutateAsync({ id: product.id, isActive: !product.is_active })
    } catch (err) {
      setActionError(getErrorMessage(err, 'No se pudo cambiar el estado del producto'))
    }
  }

  const productColumns: Column<Product>[] = [
    {
      key: 'product',
      header: 'Producto',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.full_name}</p>
          <p className="truncate text-xs text-muted">
            {row.code}
            {row.category_name ? ` · ${row.category_name}` : ''}
            {row.laboratory ? ` · ${row.laboratory}` : ''}
          </p>
        </div>
      ),
    },
    {
      key: 'kind',
      header: 'Tipo',
      className: 'w-40 text-muted',
      render: (row) => row.kind_label,
    },
    {
      key: 'stock',
      header: 'Stock',
      className: 'w-36',
      render: (row) => (
        <div>
          <p className="font-semibold text-foreground">
            {row.stock} <span className="text-xs font-normal text-muted">{row.unit.toLowerCase()}</span>
          </p>
          <p className="text-xs text-muted">
            mín. {row.min_stock} · máx. {row.max_stock}
          </p>
        </div>
      ),
    },
    {
      key: 'expiry',
      header: 'Vencimiento',
      className: 'w-40',
      render: (row) =>
        row.expiry_date ? (
          <div>
            <p className={row.is_expired ? 'font-medium text-danger' : 'text-foreground'}>
              {formatDate(row.expiry_date)}
            </p>
            {(row.is_expired || row.expires_soon) && (
              <p className={`text-xs ${row.is_expired ? 'text-danger' : 'text-warning-dark'}`}>
                {row.expiry_label}
              </p>
            )}
          </div>
        ) : (
          <span className="text-xs text-muted">—</span>
        ),
    },
    {
      key: 'price',
      header: 'Precio',
      className: 'w-28 text-right',
      render: (row) => (
        <div className="text-right">
          <p className="font-medium text-foreground">{formatMoney(row.sale_price)}</p>
          <p className="text-xs text-muted">compra {formatMoney(row.purchase_price)}</p>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Estado',
      className: 'w-36',
      render: (row) =>
        !row.is_active ? (
          <Badge variant="neutral" dot>
            Inactivo
          </Badge>
        ) : row.is_expired ? (
          <Badge variant="danger" dot>
            Vencido
          </Badge>
        ) : row.is_out_of_stock ? (
          <Badge variant="danger" dot>
            Sin stock
          </Badge>
        ) : row.expires_soon ? (
          <Badge variant="warning" dot>
            Por vencer
          </Badge>
        ) : row.needs_restock ? (
          <Badge variant="warning" dot>
            Reponer
          </Badge>
        ) : (
          <Badge variant="success" dot>
            Disponible
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
              aria-label={`Acciones de ${row.name}`}
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
                  setSelected(row)
                  setProductOpen(true)
                }}
              >
                Editar
              </DropdownItem>
              <DropdownItem
                icon={<Boxes className="h-4 w-4" />}
                onClick={() => {
                  close()
                  setSelected(row)
                  setMovementOpen(true)
                }}
              >
                Registrar movimiento
              </DropdownItem>
              <DropdownItem
                icon={
                  row.is_active ? (
                    <ShieldOff className="h-4 w-4" />
                  ) : (
                    <ShieldCheck className="h-4 w-4" />
                  )
                }
                variant={row.is_active ? 'danger' : 'default'}
                onClick={() => {
                  close()
                  void toggleStatus(row)
                }}
              >
                {row.is_active ? 'Desactivar' : 'Activar'}
              </DropdownItem>
            </>
          )}
        </Dropdown>
      ),
    },
  ]

  const alertColumns: Column<LowStockItem>[] = [
    {
      key: 'product',
      header: 'Producto',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.full_name}</p>
          <p className="truncate text-xs text-muted">
            {row.code}
            {row.category_name ? ` · ${row.category_name}` : ''}
          </p>
        </div>
      ),
    },
    {
      key: 'stock',
      header: 'Stock actual',
      className: 'w-32',
      render: (row) => (
        <span className={row.is_out_of_stock ? 'font-semibold text-danger' : 'text-foreground'}>
          {row.stock} {row.unit.toLowerCase()}
        </span>
      ),
    },
    { key: 'min', header: 'Mínimo', className: 'w-24 text-muted', render: (row) => row.min_stock },
    { key: 'max', header: 'Máximo', className: 'w-24 text-muted', render: (row) => row.max_stock },
    {
      key: 'suggested',
      header: 'Compra sugerida',
      className: 'w-36',
      render: (row) => (
        <Badge variant={row.suggested_purchase > 0 ? 'warning' : 'neutral'}>
          {row.suggested_purchase > 0 ? `${row.suggested_purchase} ${row.unit.toLowerCase()}` : '—'}
        </Badge>
      ),
    },
  ]

  const expiringColumns: Column<ExpiringItem>[] = [
    {
      key: 'product',
      header: 'Producto',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.full_name}</p>
          <p className="truncate text-xs text-muted">
            {row.code}
            {row.lot ? ` · lote ${row.lot}` : ''}
            {row.category_name ? ` · ${row.category_name}` : ''}
          </p>
        </div>
      ),
    },
    {
      key: 'stock',
      header: 'En existencia',
      className: 'w-32 text-muted',
      render: (row) => `${row.stock} ${row.unit.toLowerCase()}`,
    },
    {
      key: 'expiry',
      header: 'Vence',
      className: 'w-32',
      render: (row) => (row.expiry_date ? formatDate(row.expiry_date) : '—'),
    },
    {
      key: 'state',
      header: 'Situación',
      className: 'w-48',
      render: (row) => (
        <Badge variant={row.is_expired ? 'danger' : 'warning'} dot>
          {row.expiry_label}
        </Badge>
      ),
    },
  ]

  const movementColumns: Column<Movement>[] = [
    {
      key: 'date',
      header: 'Fecha',
      className: 'w-44 text-muted',
      render: (row) => formatDateTime(row.occurred_at),
    },
    {
      key: 'product',
      header: 'Producto',
      render: (row) => row.product_name,
    },
    {
      key: 'reason',
      header: 'Motivo',
      className: 'text-muted',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate">{row.reason_label}</p>
          {row.notes && <p className="truncate text-xs">{row.notes}</p>}
        </div>
      ),
    },
    {
      key: 'quantity',
      header: 'Cantidad',
      className: 'w-32',
      render: (row) => (
        <span
          className={`inline-flex items-center gap-1 font-semibold ${
            row.signed_quantity >= 0 ? 'text-primary-dark' : 'text-danger'
          }`}
        >
          {row.signed_quantity >= 0 ? (
            <ArrowUpRight className="h-3.5 w-3.5" />
          ) : (
            <ArrowDownRight className="h-3.5 w-3.5" />
          )}
          {Math.abs(row.signed_quantity)}
        </span>
      ),
    },
    {
      key: 'stock',
      header: 'Saldo',
      className: 'w-28 text-muted',
      render: (row) => `${row.stock_before} → ${row.stock_after}`,
    },
  ]

  const categoryOptions: SelectOption[] = categories.map((item) => ({
    value: String(item.id),
    label: item.name,
  }))

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operación"
        title="Farmacia y almacén"
        subtitle="Catálogo, existencias, kardex y alertas de reposición"
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Boxes className="h-4 w-4" />}
              onClick={() => {
                setSelected(null)
                setMovementOpen(true)
              }}
            >
              Movimiento
            </Button>
            <Button
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => {
                setSelected(null)
                setProductOpen(true)
              }}
            >
              Nuevo producto
            </Button>
          </div>
        }
      />

      {actionError && <Alert variant="danger">{actionError}</Alert>}
      {products.error && <Alert variant="danger">{products.error}</Alert>}

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
        <StatCard label="Productos activos" value={stats?.active_products ?? 0} icon={Pill} />
        <StatCard
          label="Bajo el mínimo"
          value={stats?.low_stock ?? 0}
          icon={AlertTriangle}
          tone="warning"
          hint="requieren reposición"
        />
        <StatCard
          label="Por vencer"
          value={stats?.expiring_soon ?? 0}
          icon={CalendarClock}
          tone="warning"
          hint={`próximos ${EXPIRY_ALERT_DAYS} días`}
        />
        <StatCard
          label="Vencidos / sin stock"
          value={(stats?.expired ?? 0) + (stats?.out_of_stock ?? 0)}
          icon={PackageSearch}
          tone="danger"
          hint={`${stats?.expired ?? 0} vencidos`}
        />
        <StatCard
          label="Valor del inventario"
          value={formatMoney(stats?.inventory_value ?? 0)}
          icon={Wallet}
          hint="a precio de compra"
        />
      </section>

      <Tabs items={TABS} active={tab} onChange={setTab} />

      {tab === 'products' && (
        <Card>
          <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Input
              placeholder="Buscar por nombre, código o laboratorio"
              icon={<Search className="h-[18px] w-[18px]" />}
              value={searchInput}
              containerClassName="lg:col-span-2"
              onChange={(event) => setSearchInput(event.target.value)}
            />
            <Select
              options={KIND_OPTIONS}
              placeholder="Todos los tipos"
              value={kindFilter}
              onChange={(event) => {
                setKindFilter(event.target.value)
                setPage(1)
              }}
            />
            <Select
              options={categoryOptions}
              placeholder="Todas las categorías"
              value={categoryFilter}
              onChange={(event) => {
                setCategoryFilter(event.target.value)
                setPage(1)
              }}
            />
          </CardBody>

          <Table
            columns={productColumns}
            data={products.data?.items ?? []}
            keyExtractor={(row) => row.id}
            isLoading={products.isLoading}
            emptyState={
              <EmptyState
                icon={Pill}
                title="Sin productos"
                description="Registre los medicamentos e insumos que maneja el policlínico."
              />
            }
          />

          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={products.data?.total ?? 0}
            labels={['producto', 'productos']}
            onChange={setPage}
          />
        </Card>
      )}

      {tab === 'alerts' && (
        <Card>
          <Table
            columns={alertColumns}
            data={alerts}
            keyExtractor={(row) => row.id}
            emptyState={
              <EmptyState
                icon={AlertTriangle}
                title="Sin alertas de reposición"
                description="Todos los productos con stock mínimo configurado están por encima del umbral."
              />
            }
          />
        </Card>
      )}

      {tab === 'expiring' && (
        <Card>
          <Table
            columns={expiringColumns}
            data={expiring}
            keyExtractor={(row) => row.id}
            emptyState={
              <EmptyState
                icon={CalendarClock}
                title="Sin vencimientos próximos"
                description={`Ningún producto con existencias vence en los próximos ${EXPIRY_ALERT_DAYS} días.`}
              />
            }
          />
        </Card>
      )}

      {tab === 'kardex' && (
        <Card>
          <Table
            columns={movementColumns}
            data={movements.data?.items ?? []}
            keyExtractor={(row) => row.id}
            isLoading={movements.isLoading}
            emptyState={
              <EmptyState
                icon={Boxes}
                title="Sin movimientos"
                description="Las entradas, salidas y ajustes aparecerán en este kardex."
              />
            }
          />

          <Pagination
            page={kardexPage}
            pageSize={PAGE_SIZE}
            total={movements.data?.total ?? 0}
            labels={['movimiento', 'movimientos']}
            onChange={setKardexPage}
          />
        </Card>
      )}

      <ProductFormModal
        open={productOpen}
        product={selected}
        onClose={() => setProductOpen(false)}
      />

      <MovementModal
        open={movementOpen}
        product={
          selected
            ? {
                id: selected.id,
                code: selected.code,
                name: selected.name,
                full_name: selected.full_name,
                unit: selected.unit,
                stock: selected.stock,
                sale_price: selected.sale_price,
                purchase_price: selected.purchase_price,
                requires_prescription: selected.requires_prescription,
                needs_restock: selected.needs_restock,
                expiry_date: selected.expiry_date,
                is_expired: selected.is_expired,
                expires_soon: selected.expires_soon,
              }
            : null
        }
        onClose={() => setMovementOpen(false)}
      />
    </div>
  )
}
