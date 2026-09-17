import { useEffect, useMemo, useState } from 'react'
import {
  BellRing,
  CheckCircle2,
  FileText,
  MoreVertical,
  Pencil,
  Search,
  Stethoscope,
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
  Table,
  type BadgeVariant,
  type Column,
  type SelectOption,
} from '@/components/ui'
import { useActivePractitioners } from '@/features/catalog/hooks/useCatalog'
import { EncounterFormModal } from '@/features/encounters/components/EncounterFormModal'
import { PractitionerAgendaCard } from '@/features/encounters/components/PractitionerAgendaCard'
import { encountersApi } from '@/features/encounters/api/encounters.api'
import {
  useEncounterActions,
  useEncountersList,
} from '@/features/encounters/hooks/useEncounters'
import { useReminderActions } from '@/features/reminders/hooks/useReminders'
import { useModuleAccess } from '@/hooks/useModuleAccess'
import { useOwnPractitioner } from '@/hooks/useOwnPractitioner'
import { formatDateTime, toDateInput } from '@/lib/datetime'
import { cn } from '@/lib/utils'
import { getErrorMessage } from '@/services/http'
import type {
  Appointment,
  Encounter,
  EncounterFilters,
  EncounterListItem,
  EncounterStatus,
} from '@/types'

const PAGE_SIZE = 10

const STATUS_VARIANT: Record<EncounterStatus, BadgeVariant> = {
  EN_CURSO: 'warning',
  FINALIZADA: 'success',
  ANULADA: 'danger',
}

const STATUS_OPTIONS: SelectOption[] = [
  { value: 'EN_CURSO', label: 'En curso' },
  { value: 'FINALIZADA', label: 'Finalizadas' },
  { value: 'ANULADA', label: 'Anuladas' },
]

export function ConsultationsPage() {
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [practitionerFilter, setPractitionerFilter] = useState('')
  const [day, setDay] = useState(() => toDateInput())
  const [page, setPage] = useState(1)

  const [formOpen, setFormOpen] = useState(false)
  const [selected, setSelected] = useState<Encounter | null>(null)
  // Cita desde la que se abre la atención: fija el paciente y deja la cita
  // enlazada, de modo que al finalizar quede como atendida.
  const [fromAppointment, setFromAppointment] = useState<Appointment | null>(null)
  const [cancelTarget, setCancelTarget] = useState<EncounterListItem | null>(null)
  const [feedback, setFeedback] = useState<{ tone: 'success' | 'danger'; text: string } | null>(null)

  // Quien solo consulta la historia —administración incluida— no debe ver
  // acciones que la API va a rechazar.
  const { canManage } = useModuleAccess()
  const canWrite = canManage('ENCOUNTERS')
  const { practitioners } = useActivePractitioners()
  /* Quien atiende trabaja sobre lo suyo: con ficha propia, el módulo muestra
     su agenda y sus atenciones, y el profesional deja de ser algo que elegir.
     El selector sigue ahí para los perfiles que consultan la historia sin
     firmarla —administración— y necesitan mirar la de cualquier profesional. */
  const ownPractitioner = useOwnPractitioner(practitioners)
  const ownPractitionerId = ownPractitioner?.id ?? null
  const { finish, cancel } = useEncounterActions()
  const { fromEncounter } = useReminderActions()

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const filters: EncounterFilters = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      ...(search ? { search } : {}),
      ...(statusFilter ? { status: statusFilter } : {}),
      ...(ownPractitionerId
        ? { practitioner_id: ownPractitionerId }
        : practitionerFilter
          ? { practitioner_id: Number(practitionerFilter) }
          : {}),
      ...(day ? { day } : {}),
    }),
    [page, search, statusFilter, practitionerFilter, ownPractitionerId, day],
  )

  const { data, isLoading, isFetching, error } = useEncountersList(filters)

  const openCreate = () => {
    setSelected(null)
    setFromAppointment(null)
    setFeedback(null)
    setFormOpen(true)
  }

  /** Abre la atención de una cita, con el paciente y la cita ya puestos. */
  const openFromAppointment = (appointment: Appointment) => {
    setSelected(null)
    setFromAppointment(appointment)
    setFeedback(null)
    setFormOpen(true)
  }

  const openEdit = async (row: EncounterListItem) => {
    setFeedback(null)
    try {
      setSelected(await encountersApi.get(row.id))
      setFromAppointment(null)
      setFormOpen(true)
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo abrir la atención') })
    }
  }

  const finishEncounter = async (row: EncounterListItem) => {
    setFeedback(null)
    try {
      await finish.mutateAsync(row.id)
      setFeedback({
        tone: 'success',
        text: `Atención de ${row.patient_name} finalizada. La cita asociada quedó como atendida.`,
      })
    } catch (err) {
      setFeedback({
        tone: 'danger',
        text: getErrorMessage(err, 'No se pudo finalizar la atención'),
      })
    }
  }

  const scheduleReminders = async (row: EncounterListItem) => {
    setFeedback(null)
    try {
      const batch = await fromEncounter.mutateAsync({
        encounterId: row.id,
        channel: 'WHATSAPP',
      })
      setFeedback({
        tone: 'success',
        text: `Se programaron ${batch.created} recordatorios de medicación para ${row.patient_name}.`,
      })
    } catch (err) {
      setFeedback({
        tone: 'danger',
        text: getErrorMessage(err, 'No se pudieron programar los recordatorios'),
      })
    }
  }

  const confirmCancel = async (reason: string) => {
    if (!cancelTarget) return
    try {
      await cancel.mutateAsync({ id: cancelTarget.id, reason })
      setCancelTarget(null)
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo anular la atención') })
    }
  }

  const practitionerOptions: SelectOption[] = practitioners.map((item) => ({
    value: String(item.id),
    label: item.full_name,
  }))

  const columns: Column<EncounterListItem>[] = [
    {
      key: 'started',
      header: 'Inicio',
      className: 'w-40 text-muted',
      render: (row) => formatDateTime(row.started_at),
    },
    {
      key: 'patient',
      header: 'Paciente',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.patient_name}</p>
          <p className="truncate text-xs text-muted">{row.chief_complaint ?? 'Sin motivo registrado'}</p>
        </div>
      ),
    },
    // Con la lista ceñida a la ficha propia, la columna repetiría el mismo
    // nombre en todas las filas.
    ...(ownPractitioner
      ? []
      : [
          {
            key: 'practitioner',
            header: 'Profesional',
            className: 'text-muted',
            render: (row: EncounterListItem) => (
              <div className="min-w-0">
                <p className="truncate text-foreground">{row.practitioner_name}</p>
                <p className="truncate text-xs">{row.specialty_name ?? '—'}</p>
              </div>
            ),
          },
        ]),
    {
      key: 'diagnosis',
      header: 'Diagnóstico',
      className: 'text-muted',
      render: (row) => row.main_diagnosis ?? '—',
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
              aria-label={`Acciones de la atención de ${row.patient_name}`}
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
                  void openEdit(row)
                }}
              >
                {canWrite && row.status === 'EN_CURSO' ? 'Continuar atención' : 'Ver atención'}
              </DropdownItem>
              {canWrite && row.status === 'EN_CURSO' && (
                <>
                  <DropdownItem
                    icon={<CheckCircle2 className="h-4 w-4" />}
                    onClick={() => {
                      close()
                      void finishEncounter(row)
                    }}
                  >
                    Finalizar atención
                  </DropdownItem>
                  <DropdownItem
                    icon={<XCircle className="h-4 w-4" />}
                    variant="danger"
                    onClick={() => {
                      close()
                      setCancelTarget(row)
                    }}
                  >
                    Anular atención
                  </DropdownItem>
                </>
              )}
              {row.status === 'FINALIZADA' && (
                <DropdownItem
                  icon={<BellRing className="h-4 w-4" />}
                  onClick={() => {
                    close()
                    void scheduleReminders(row)
                  }}
                >
                  Programar recordatorios
                </DropdownItem>
              )}
            </>
          )}
        </Dropdown>
      ),
    },
  ]

  const total = data?.total ?? 0

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Atención"
        title="Atenciones médicas"
        subtitle={
          ownPractitioner
            ? `Sus citas y atenciones · ${ownPractitioner.full_name}`
            : 'Consultas, diagnósticos, indicaciones y recetas'
        }
        actions={
          canWrite ? (
            <Button size="sm" leftIcon={<Stethoscope className="h-4 w-4" />} onClick={openCreate}>
              Nueva atención
            </Button>
          ) : null
        }
      />

      {feedback && <Alert variant={feedback.tone}>{feedback.text}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}

      {ownPractitionerId !== null && (
        <PractitionerAgendaCard
          practitionerId={ownPractitionerId}
          day={day}
          canWrite={canWrite}
          onStart={openFromAppointment}
        />
      )}

      <Card>
        <CardBody
          className={cn(
            'grid gap-3 sm:grid-cols-2',
            ownPractitioner ? 'lg:grid-cols-3' : 'lg:grid-cols-4',
          )}
        >
          <Input
            placeholder="Buscar por paciente o documento"
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
          {!ownPractitioner && (
            <Select
              options={practitionerOptions}
              placeholder="Todos los profesionales"
              value={practitionerFilter}
              onChange={(event) => {
                setPractitionerFilter(event.target.value)
                setPage(1)
              }}
            />
          )}
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
              icon={FileText}
              title={
                ownPractitioner
                  ? 'No ha registrado atenciones en esta fecha'
                  : 'Sin atenciones en esta fecha'
              }
              description={
                !canWrite
                  ? 'No hay atenciones registradas en esta fecha.'
                  : ownPractitioner
                    ? 'Inicie una atención desde sus citas del día o registre una nueva.'
                    : 'Inicie una atención desde la agenda del día o registre una nueva.'
              }
              action={
                canWrite ? (
                  <Button
                    size="sm"
                    leftIcon={<Stethoscope className="h-4 w-4" />}
                    onClick={openCreate}
                  >
                    Nueva atención
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
          labels={['atención', 'atenciones']}
          onChange={setPage}
        />
      </Card>

      <EncounterFormModal
        open={formOpen}
        encounter={selected}
        appointmentId={fromAppointment?.id ?? null}
        initialPatient={fromAppointment?.patient ?? null}
        initialPractitionerId={fromAppointment?.practitioner_id ?? ownPractitionerId}
        onClose={() => setFormOpen(false)}
      />

      <ConfirmDialog
        open={cancelTarget !== null}
        title="Anular atención"
        description={cancelTarget?.patient_name}
        reasonLabel="Motivo de la anulación"
        confirmLabel="Anular"
        variant="danger"
        isLoading={cancel.isPending}
        onClose={() => setCancelTarget(null)}
        onConfirm={confirmCancel}
      />
    </div>
  )
}
