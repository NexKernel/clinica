import { useEffect, useMemo, useState } from 'react'
import { FileCheck2, FlaskConical, MoreVertical, Paperclip, Pencil, Plus, Search, Send } from 'lucide-react'

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
  Table,
  type BadgeVariant,
  type Column,
  type SelectOption,
} from '@/components/ui'
import { studiesApi } from '@/features/studies/api/studies.api'
import { StudyFormModal } from '@/features/studies/components/StudyFormModal'
import { StudyResultModal } from '@/features/studies/components/StudyResultModal'
import { useStudiesList } from '@/features/studies/hooks/useStudies'
import { formatDate } from '@/lib/datetime'
import { useModuleAccess } from '@/hooks/useModuleAccess'
import { getErrorMessage } from '@/services/http'
import {
  STUDY_STATUS_LABELS,
  STUDY_STATUSES,
  STUDY_TYPE_LABELS,
  STUDY_TYPES,
  type Study,
  type StudyFilters,
  type StudyListItem,
  type StudyStatus,
} from '@/types'

const PAGE_SIZE = 10

const STATUS_VARIANT: Record<StudyStatus, BadgeVariant> = {
  SOLICITADO: 'warning',
  EN_PROCESO: 'info',
  COMPLETADO: 'success',
  ANULADO: 'neutral',
}

const TYPE_OPTIONS: SelectOption[] = STUDY_TYPES.map((type) => ({
  value: type,
  label: STUDY_TYPE_LABELS[type],
}))

const STATUS_OPTIONS: SelectOption[] = STUDY_STATUSES.map((status) => ({
  value: status,
  label: STUDY_STATUS_LABELS[status],
}))

export function StudiesPage() {
  // Quien solo consulta la historia no debe ver acciones que la API rechaza.
  const { canManage } = useModuleAccess()
  const canWrite = canManage('STUDIES')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)

  const [formOpen, setFormOpen] = useState(false)
  const [resultId, setResultId] = useState<number | null>(null)
  const [editing, setEditing] = useState<Study | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const filters: StudyFilters = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      ...(search ? { search } : {}),
      ...(typeFilter ? { study_type: typeFilter } : {}),
      ...(statusFilter ? { status: statusFilter } : {}),
    }),
    [page, search, typeFilter, statusFilter],
  )

  const { data, isLoading, isFetching, error } = useStudiesList(filters)

  const openCreate = () => {
    setEditing(null)
    setActionError(null)
    setFormOpen(true)
  }

  const openEdit = async (row: StudyListItem) => {
    setActionError(null)
    try {
      setEditing(await studiesApi.get(row.id))
      setFormOpen(true)
    } catch (err) {
      setActionError(getErrorMessage(err, 'No se pudo abrir el estudio'))
    }
  }

  const columns: Column<StudyListItem>[] = [
    {
      key: 'requested',
      header: 'Solicitado',
      className: 'w-32 text-muted',
      render: (row) => formatDate(row.requested_at),
    },
    {
      key: 'study',
      header: 'Estudio',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.name}</p>
          <p className="truncate text-xs text-muted">{row.type_label}</p>
        </div>
      ),
    },
    {
      key: 'patient',
      header: 'Paciente',
      className: 'text-muted',
      render: (row) => row.patient_name,
    },
    {
      key: 'result',
      header: 'Resultado',
      className: 'text-muted',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate">{row.result_summary ?? '—'}</p>
          {row.attachment_count > 0 && (
            <p className="flex items-center gap-1 text-xs">
              <Paperclip className="h-3 w-3" />
              {row.attachment_count} archivo{row.attachment_count === 1 ? '' : 's'}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Estado',
      className: 'w-36',
      render: (row) => (
        <div className="flex flex-col items-start gap-1">
          <Badge variant={STATUS_VARIANT[row.status]} dot>
            {row.status_label}
          </Badge>
          {row.shared_at && (
            <span className="flex items-center gap-1 text-[11px] text-muted">
              <Send className="h-3 w-3" />
              Enviado
            </span>
          )}
        </div>
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
              {canWrite && (
                <DropdownItem
                  icon={<FileCheck2 className="h-4 w-4" />}
                  onClick={() => {
                    close()
                    setResultId(row.id)
                  }}
                >
                  Registrar resultado
                </DropdownItem>
              )}
              <DropdownItem
                icon={<Pencil className="h-4 w-4" />}
                onClick={() => {
                  close()
                  void openEdit(row)
                }}
              >
                {canWrite ? 'Editar solicitud' : 'Ver solicitud'}
              </DropdownItem>
            </>
          )}
        </Dropdown>
      ),
    },
  ]

  const total = data?.total ?? 0
  const hasFilters = Boolean(search || typeFilter || statusFilter)

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Apoyo al diagnóstico"
        title="Resultados y Rayos X"
        subtitle="Solicitudes, informes, archivos y envío al paciente"
        actions={
          canWrite ? (
            <Button size="sm" leftIcon={<Plus className="h-4 w-4" />} onClick={openCreate}>
              Nueva solicitud
            </Button>
          ) : null
        }
      />

      {actionError && <Alert variant="danger">{actionError}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}

      <Card>
        <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            placeholder="Buscar por paciente o estudio"
            icon={<Search className="h-[18px] w-[18px]" />}
            value={searchInput}
            containerClassName="lg:col-span-2"
            onChange={(event) => setSearchInput(event.target.value)}
          />
          <Select
            options={TYPE_OPTIONS}
            placeholder="Todos los tipos"
            value={typeFilter}
            onChange={(event) => {
              setTypeFilter(event.target.value)
              setPage(1)
            }}
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
          columns={columns}
          data={data?.items ?? []}
          keyExtractor={(row) => row.id}
          isLoading={isLoading}
          className={isFetching && !isLoading ? 'opacity-60 transition-opacity' : undefined}
          emptyState={
            <EmptyState
              icon={FlaskConical}
              title={hasFilters ? 'Sin resultados' : 'Aún no hay estudios'}
              description={
                hasFilters
                  ? 'Pruebe con otros criterios de búsqueda.'
                  : 'Registre la primera solicitud de laboratorio o Rayos X.'
              }
              action={
                !hasFilters && canWrite ? (
                  <Button size="sm" leftIcon={<Plus className="h-4 w-4" />} onClick={openCreate}>
                    Nueva solicitud
                  </Button>
                ) : undefined
              }
            />
          }
        />

        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          labels={['estudio', 'estudios']}
          onChange={setPage}
        />
      </Card>

      <StudyFormModal open={formOpen} study={editing} onClose={() => setFormOpen(false)} />

      <StudyResultModal
        open={resultId !== null}
        studyId={resultId}
        onClose={() => setResultId(null)}
      />
    </div>
  )
}
