import { useMemo, useState } from 'react'
import { Check, FileClock, Minus, Pencil, Plus, ShieldCheck } from 'lucide-react'

import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  Input,
  Pagination,
  Select,
  Table,
  type Column,
  type SelectOption,
} from '@/components/ui'
import { useAuditLogs, useAuditModules, usePermissionMatrix } from '@/features/admin/hooks/useAdmin'
import { SeriesFormModal } from '@/features/sales/components/SeriesFormModal'
import { useDocumentSeries } from '@/features/sales/hooks/useSales'
import { formatDateTime } from '@/lib/datetime'
import type { AuditFilters, AuditLog, DocumentSeries, ModuleAccess } from '@/types'

const PAGE_SIZE = 15

const ACTION_OPTIONS: SelectOption[] = [
  { value: 'POST', label: 'Creación (POST)' },
  { value: 'PUT', label: 'Actualización (PUT)' },
  { value: 'PATCH', label: 'Cambio parcial (PATCH)' },
  { value: 'DELETE', label: 'Eliminación (DELETE)' },
]

export function AuditPanel() {
  const [search, setSearch] = useState('')
  const [moduleFilter, setModuleFilter] = useState('')
  const [actionFilter, setActionFilter] = useState('')
  const [page, setPage] = useState(1)

  const { modules } = useAuditModules()

  const filters: AuditFilters = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      ...(search.trim() ? { search: search.trim() } : {}),
      ...(moduleFilter ? { module: moduleFilter } : {}),
      ...(actionFilter ? { action: actionFilter } : {}),
    }),
    [page, search, moduleFilter, actionFilter],
  )

  const { data, isLoading, error } = useAuditLogs(filters)

  const columns: Column<AuditLog>[] = [
    {
      key: 'date',
      header: 'Fecha',
      className: 'w-44 text-muted',
      render: (row) => formatDateTime(row.created_at),
    },
    {
      key: 'user',
      header: 'Usuario',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.username ?? 'Sin sesión'}</p>
          <p className="truncate text-xs text-muted">{row.role ?? '—'}</p>
        </div>
      ),
    },
    { key: 'module', header: 'Módulo', className: 'text-muted', render: (row) => row.module },
    {
      key: 'action',
      header: 'Acción',
      className: 'w-28',
      render: (row) => <Badge variant="primary">{row.action}</Badge>,
    },
    {
      key: 'result',
      header: 'Resultado',
      className: 'w-28',
      render: (row) => (
        <Badge variant={row.succeeded ? 'success' : 'danger'} dot>
          {row.status_code}
        </Badge>
      ),
    },
    { key: 'ip', header: 'Origen', className: 'w-32 text-muted', render: (row) => row.ip_address ?? '—' },
  ]

  const moduleOptions: SelectOption[] = modules.map((module) => ({ value: module, label: module }))

  return (
    <>
      {error && <Alert variant="danger">{error}</Alert>}

      <Card>
        <CardHeader
          title="Bitácora de acciones"
          description="Registro de las operaciones que modifican información del sistema"
        />

        <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Input
            placeholder="Buscar por usuario o módulo"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
          />
          <Select
            options={moduleOptions}
            placeholder="Todos los módulos"
            value={moduleFilter}
            onChange={(event) => {
              setModuleFilter(event.target.value)
              setPage(1)
            }}
          />
          <Select
            options={ACTION_OPTIONS}
            placeholder="Todas las acciones"
            value={actionFilter}
            onChange={(event) => {
              setActionFilter(event.target.value)
              setPage(1)
            }}
          />
        </CardBody>

        <Table
          columns={columns}
          data={data?.items ?? []}
          keyExtractor={(row) => row.id}
          isLoading={isLoading}
          emptyState={
            <EmptyState
              icon={FileClock}
              title="Sin registros"
              description="Las acciones realizadas en el sistema quedarán registradas aquí."
            />
          }
        />

        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={data?.total ?? 0}
          labels={['acción', 'acciones']}
          onChange={setPage}
        />
      </Card>
    </>
  )
}

export function PermissionsPanel() {
  const { matrix, isLoading } = usePermissionMatrix()

  const columns: Column<ModuleAccess>[] = [
    {
      key: 'module',
      header: 'Módulo',
      className: 'font-medium text-foreground',
      render: (row) => row.name,
    },
    {
      key: 'view',
      header: 'Consulta',
      className: 'w-28',
      render: (row) => <AccessMark granted={row.can_view} />,
    },
    {
      key: 'manage',
      header: 'Registro',
      className: 'w-28',
      render: (row) => <AccessMark granted={row.can_manage} />,
    },
  ]

  return (
    <div className="space-y-4">
      <Alert variant="info">
        La matriz de permisos es la que aplica el servidor en cada operación. Para cambiar el acceso
        de una persona, asígnele otro perfil desde el módulo de usuarios.
      </Alert>

      {isLoading && <Card><CardBody>Cargando matriz de permisos…</CardBody></Card>}

      {matrix.map((role) => (
        <Card key={role.role}>
          <CardHeader
            title={role.role_name}
            description={`Perfil ${role.role}`}
            action={<ShieldCheck className="h-5 w-5 text-primary" />}
          />
          <Table
            columns={columns}
            data={role.modules}
            keyExtractor={(row) => `${role.role}-${row.code}`}
          />
        </Card>
      ))}
    </div>
  )
}

function AccessMark({ granted }: { granted: boolean }) {
  return granted ? (
    <span className="inline-flex items-center gap-1 text-sm font-medium text-primary-dark">
      <Check className="h-4 w-4" />
      Sí
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-sm text-muted">
      <Minus className="h-4 w-4" />
      No
    </span>
  )
}

export function SeriesPanel() {
  const { series, isLoading } = useDocumentSeries()
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<DocumentSeries | null>(null)

  const columns: Column<DocumentSeries>[] = [
    {
      key: 'series',
      header: 'Serie',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.series}</p>
          <p className="truncate text-xs text-muted">{row.document_label}</p>
        </div>
      ),
    },
    {
      key: 'next',
      header: 'Siguiente número',
      className: 'w-40 text-muted',
      render: (row) => String(row.next_number).padStart(8, '0'),
    },
    {
      key: 'default',
      header: 'Por defecto',
      className: 'w-32',
      render: (row) =>
        row.is_default ? <Badge variant="primary">Por defecto</Badge> : <span className="text-muted">—</span>,
    },
    {
      key: 'status',
      header: 'Estado',
      className: 'w-28',
      render: (row) => (
        <Badge variant={row.is_active ? 'success' : 'neutral'} dot>
          {row.is_active ? 'Activa' : 'Inactiva'}
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
          aria-label={`Editar serie ${row.series}`}
          onClick={() => {
            setSelected(row)
            setOpen(true)
          }}
        >
          <Pencil className="h-4 w-4" />
        </Button>
      ),
    },
  ]

  return (
    <>
      <Card>
        <CardHeader
          title="Series y correlativos"
          description="Numeración de notas de venta, boletas y facturas"
          action={
            <Button
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => {
                setSelected(null)
                setOpen(true)
              }}
            >
              Nueva serie
            </Button>
          }
        />

        <Table
          columns={columns}
          data={series}
          keyExtractor={(row) => row.id}
          isLoading={isLoading}
          emptyState={
            <EmptyState
              icon={FileClock}
              title="Sin series configuradas"
              description="Al emitir el primer comprobante se crea automáticamente una serie por defecto."
            />
          }
        />
      </Card>

      <SeriesFormModal open={open} series={selected} onClose={() => setOpen(false)} />
    </>
  )
}
