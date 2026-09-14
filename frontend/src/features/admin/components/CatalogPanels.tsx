import { useState } from 'react'
import { Pencil, Plus, Stethoscope, Tag } from 'lucide-react'

import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Pagination,
  Table,
  type Column,
} from '@/components/ui'
import { PractitionerFormModal } from '@/features/catalog/components/PractitionerFormModal'
import { ServiceFormModal } from '@/features/catalog/components/ServiceFormModal'
import {
  usePractitionersList,
  useServicesList,
} from '@/features/catalog/hooks/useCatalog'
import { formatMoney } from '@/lib/utils'
import { WEEKDAYS, type MedicalService, type Practitioner } from '@/types'

const PAGE_SIZE = 10

/** Resume la agenda semanal: "Lun, Mar, Mié · 08:00–13:00". */
function scheduleSummary(practitioner: Practitioner): string {
  if (practitioner.schedules.length === 0) return 'Sin horario configurado'
  const days = [...new Set(practitioner.schedules.map((block) => block.weekday))]
    .sort((a, b) => a - b)
    .map((weekday) => WEEKDAYS[weekday]?.slice(0, 3))
    .join(', ')
  const first = practitioner.schedules[0]
  const range = first ? `${first.start_time.slice(0, 5)}–${first.end_time.slice(0, 5)}` : ''
  const extra = practitioner.schedules.length > 1 ? ` +${practitioner.schedules.length - 1}` : ''
  return `${days} · ${range}${extra}`
}

export function PractitionersPanel() {
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<Practitioner | null>(null)

  const { data, isLoading, error } = usePractitionersList({ page, page_size: PAGE_SIZE })

  const columns: Column<Practitioner>[] = [
    {
      key: 'practitioner',
      header: 'Profesional',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.full_name}</p>
          <p className="truncate text-xs text-muted">
            {row.specialty_name ?? 'Sin especialidad'}
            {row.license_number ? ` · ${row.license_number}` : ''}
          </p>
        </div>
      ),
    },
    {
      key: 'schedule',
      header: 'Horario',
      className: 'text-muted',
      render: (row) => scheduleSummary(row),
    },
    {
      key: 'slot',
      header: 'Cita',
      className: 'w-24 text-muted',
      render: (row) => `${row.slot_minutes} min`,
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
          aria-label={`Editar ${row.full_name}`}
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
      {error && <Alert variant="danger">{error}</Alert>}

      <Card>
        <CardHeader
          title="Profesionales"
          description="Personal que atiende y su disponibilidad semanal"
          action={
            <Button
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => {
                setSelected(null)
                setOpen(true)
              }}
            >
              Nuevo
            </Button>
          }
        />

        <Table
          columns={columns}
          data={data?.items ?? []}
          keyExtractor={(row) => row.id}
          isLoading={isLoading}
          emptyState={
            <EmptyState
              icon={Stethoscope}
              title="Sin profesionales"
              description="Registre a los médicos y profesionales que atienden en el policlínico."
            />
          }
        />

        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={data?.total ?? 0}
          labels={['profesional', 'profesionales']}
          onChange={setPage}
        />
      </Card>

      <PractitionerFormModal
        open={open}
        practitioner={selected}
        onClose={() => setOpen(false)}
      />
    </>
  )
}

export function ServicesPanel() {
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<MedicalService | null>(null)

  const { data, isLoading, error } = useServicesList({ page, page_size: PAGE_SIZE })

  const columns: Column<MedicalService>[] = [
    {
      key: 'service',
      header: 'Servicio',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.name}</p>
          <p className="truncate text-xs text-muted">
            {row.code} · {row.kind_label}
            {row.specialty_name ? ` · ${row.specialty_name}` : ''}
          </p>
        </div>
      ),
    },
    {
      key: 'duration',
      header: 'Duración',
      className: 'w-28 text-muted',
      render: (row) => `${row.duration_minutes} min`,
    },
    {
      key: 'price',
      header: 'Precio',
      className: 'w-28 text-right font-semibold text-foreground',
      render: (row) => formatMoney(row.price),
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
          aria-label={`Editar ${row.name}`}
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
      {error && <Alert variant="danger">{error}</Alert>}

      <Card>
        <CardHeader
          title="Tarifario de servicios"
          description="Precios usados en citas, atenciones y caja"
          action={
            <Button
              size="sm"
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => {
                setSelected(null)
                setOpen(true)
              }}
            >
              Nuevo
            </Button>
          }
        />

        <Table
          columns={columns}
          data={data?.items ?? []}
          keyExtractor={(row) => row.id}
          isLoading={isLoading}
          emptyState={
            <EmptyState
              icon={Tag}
              title="Sin servicios"
              description="Registre los servicios que ofrece el policlínico y su precio."
            />
          }
        />

        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={data?.total ?? 0}
          labels={['servicio', 'servicios']}
          onChange={setPage}
        />
      </Card>

      <ServiceFormModal open={open} service={selected} onClose={() => setOpen(false)} />
    </>
  )
}
