import { useEffect, useMemo, useState } from 'react'
import {
  CalendarPlus,
  Eye,
  MoreVertical,
  Pencil,
  Search,
  ShieldCheck,
  ShieldOff,
  UserPlus,
  Users as UsersIcon,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import {
  Alert,
  Avatar,
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
  type Column,
  type SelectOption,
} from '@/components/ui'
import { PatientFormModal } from '@/features/patients/components/PatientFormModal'
import {
  usePatientActions,
  usePatientStats,
  usePatientsList,
} from '@/features/patients/hooks/usePatients'
import { patientDetailPath, ROUTES } from '@/routes/paths'
import { getErrorMessage } from '@/services/http'
import type { Patient, PatientFilters } from '@/types'

const PAGE_SIZE = 10

const STATUS_OPTIONS: SelectOption[] = [
  { value: 'active', label: 'Activos' },
  { value: 'inactive', label: 'Inactivos' },
]

export function PatientsPage() {
  const navigate = useNavigate()
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)

  const [formOpen, setFormOpen] = useState(false)
  const [selected, setSelected] = useState<Patient | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const { setStatus } = usePatientActions()
  const { stats } = usePatientStats()

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const filters: PatientFilters = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      ...(search ? { search } : {}),
      ...(statusFilter ? { is_active: statusFilter === 'active' } : {}),
    }),
    [page, search, statusFilter],
  )

  const { data, isLoading, isFetching, error } = usePatientsList(filters)

  const openCreate = () => {
    setSelected(null)
    setActionError(null)
    setFormOpen(true)
  }

  const openEdit = (patient: Patient) => {
    setSelected(patient)
    setActionError(null)
    setFormOpen(true)
  }

  const openDetail = (patient: Patient) => {
    navigate(patientDetailPath(patient.public_id))
  }

  const toggleStatus = async (patient: Patient) => {
    setActionError(null)
    try {
      await setStatus.mutateAsync({ publicId: patient.public_id, isActive: !patient.is_active })
    } catch (err) {
      setActionError(getErrorMessage(err, 'No se pudo cambiar el estado del paciente'))
    }
  }

  const columns: Column<Patient>[] = [
    {
      key: 'patient',
      header: 'Paciente',
      render: (row) => (
        <div className="flex items-center gap-3">
          <Avatar name={row.full_name} size="sm" />
          <div className="min-w-0">
            <button
              type="button"
              onClick={() => openDetail(row)}
              className="block max-w-full truncate rounded font-medium text-foreground transition-colors hover:text-primary-dark hover:underline"
            >
              {row.full_name}
            </button>
            <p className="truncate text-xs text-muted">
              {row.history_number} · {row.document_label}
            </p>
          </div>
        </div>
      ),
    },
    {
      key: 'age',
      header: 'Edad / Sexo',
      className: 'w-32 text-muted',
      render: (row) =>
        [row.age !== null ? `${row.age} años` : null, row.sex_label].filter(Boolean).join(' · ') ||
        '—',
    },
    {
      key: 'contact',
      header: 'Contacto',
      className: 'text-muted',
      render: (row) => row.phone ?? row.whatsapp ?? '—',
    },
    {
      key: 'alerts',
      header: 'Alertas',
      className: 'w-32',
      render: (row) =>
        row.has_alerts ? (
          <Badge variant="warning" dot>
            Antecedentes
          </Badge>
        ) : (
          <span className="text-xs text-muted">—</span>
        ),
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
        <Dropdown
          trigger={({ toggle }) => (
            <button
              type="button"
              aria-label={`Acciones de ${row.full_name}`}
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
                  openDetail(row)
                }}
              >
                Ver ficha
              </DropdownItem>
              <DropdownItem
                icon={<Pencil className="h-4 w-4" />}
                onClick={() => {
                  close()
                  openEdit(row)
                }}
              >
                Editar
              </DropdownItem>
              <DropdownItem
                icon={<CalendarPlus className="h-4 w-4" />}
                onClick={() => {
                  close()
                  navigate(`${ROUTES.appointments}?patient=${row.public_id}`)
                }}
              >
                Programar cita
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

  const total = data?.total ?? 0
  const hasFilters = Boolean(search || statusFilter)

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Atención"
        title="Pacientes"
        subtitle="Registro, ficha e historia clínica del paciente"
        actions={
          <Button size="sm" leftIcon={<UserPlus className="h-4 w-4" />} onClick={openCreate}>
            Nuevo paciente
          </Button>
        }
      />

      {actionError && <Alert variant="danger">{actionError}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
        <StatCard label="Pacientes activos" value={stats?.active ?? 0} icon={UsersIcon} />
        <StatCard
          label="Registrados hoy"
          value={stats?.registered_today ?? 0}
          icon={UserPlus}
          tone="info"
        />
        <StatCard
          label="Registrados este mes"
          value={stats?.registered_this_month ?? 0}
          icon={CalendarPlus}
          tone="info"
        />
        <StatCard label="Total histórico" value={stats?.total ?? 0} icon={UsersIcon} tone="primary" />
      </section>

      <Card>
        <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            placeholder="Buscar por nombre, documento o historia"
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
          columns={columns}
          data={data?.items ?? []}
          keyExtractor={(row) => row.id}
          isLoading={isLoading}
          className={isFetching && !isLoading ? 'opacity-60 transition-opacity' : undefined}
          emptyState={
            <EmptyState
              icon={UsersIcon}
              title={hasFilters ? 'Sin resultados' : 'Aún no hay pacientes'}
              description={
                hasFilters
                  ? 'Pruebe con otros criterios de búsqueda.'
                  : 'Registre al primer paciente para comenzar a programar citas.'
              }
              action={
                !hasFilters ? (
                  <Button size="sm" leftIcon={<UserPlus className="h-4 w-4" />} onClick={openCreate}>
                    Nuevo paciente
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
          labels={['paciente', 'pacientes']}
          onChange={setPage}
        />
      </Card>

      <PatientFormModal
        open={formOpen}
        patient={selected}
        onClose={() => setFormOpen(false)}
      />
    </div>
  )
}
