import { useMemo, useState } from 'react'
import {
  AlarmClock,
  BellRing,
  CalendarClock,
  Check,
  MessageCircle,
  MoreVertical,
  Pencil,
  Plus,
  Send,
  XCircle,
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
  type BadgeVariant,
  type Column,
  type SelectOption,
} from '@/components/ui'
import { remindersApi } from '@/features/reminders/api/reminders.api'
import { ReminderFormModal } from '@/features/reminders/components/ReminderFormModal'
import { useReminderActions, useRemindersList, useReminderStats } from '@/features/reminders/hooks/useReminders'
import { formatDateTime, toDateInput } from '@/lib/datetime'
import { getErrorMessage } from '@/services/http'
import {
  REMINDER_KIND_LABELS,
  REMINDER_KINDS,
  REMINDER_STATUS_LABELS,
  REMINDER_STATUSES,
  type Reminder,
  type ReminderFilters,
  type ReminderStatus,
} from '@/types'

const PAGE_SIZE = 10

const STATUS_VARIANT: Record<ReminderStatus, BadgeVariant> = {
  PENDIENTE: 'warning',
  ENVIADO: 'success',
  CANCELADO: 'neutral',
}

const KIND_OPTIONS: SelectOption[] = REMINDER_KINDS.map((kind) => ({
  value: kind,
  label: REMINDER_KIND_LABELS[kind],
}))

const STATUS_OPTIONS: SelectOption[] = REMINDER_STATUSES.map((status) => ({
  value: status,
  label: REMINDER_STATUS_LABELS[status],
}))

export function RemindersPage() {
  const [kindFilter, setKindFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('PENDIENTE')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState(() => toDateInput())
  const [page, setPage] = useState(1)

  const [formOpen, setFormOpen] = useState(false)
  const [selected, setSelected] = useState<Reminder | null>(null)
  const [feedback, setFeedback] = useState<{ tone: 'success' | 'danger'; text: string } | null>(null)

  const { stats } = useReminderStats()
  const { markSent, cancel } = useReminderActions()

  const filters: ReminderFilters = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      ...(kindFilter ? { kind: kindFilter } : {}),
      ...(statusFilter ? { status: statusFilter } : {}),
      ...(dateFrom ? { date_from: dateFrom } : {}),
      ...(dateTo ? { date_to: dateTo } : {}),
    }),
    [page, kindFilter, statusFilter, dateFrom, dateTo],
  )

  const { data, isLoading, isFetching, error } = useRemindersList(filters)

  const sendWhatsApp = async (reminder: Reminder) => {
    setFeedback(null)
    try {
      const message = await remindersApi.whatsapp(reminder.id)
      if (!message.whatsapp_url) {
        setFeedback({
          tone: 'danger',
          text: `${reminder.patient_name} no tiene un número de WhatsApp registrado.`,
        })
        return
      }
      window.open(message.whatsapp_url, '_blank')
      await markSent.mutateAsync(reminder.id)
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo abrir WhatsApp') })
    }
  }

  const applyAction = async (action: Promise<unknown>, fallback: string) => {
    setFeedback(null)
    try {
      await action
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, fallback) })
    }
  }

  const columns: Column<Reminder>[] = [
    {
      key: 'scheduled',
      header: 'Programado',
      className: 'w-44 text-muted',
      render: (row) => formatDateTime(row.scheduled_for),
    },
    {
      key: 'patient',
      header: 'Paciente',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.patient_name}</p>
          <p className="truncate text-xs text-muted">{row.patient_phone ?? 'Sin teléfono'}</p>
        </div>
      ),
    },
    {
      key: 'reminder',
      header: 'Recordatorio',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate text-foreground">{row.title}</p>
          <p className="truncate text-xs text-muted">
            {row.kind_label} · {row.channel_label}
          </p>
        </div>
      ),
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
              aria-label={`Acciones del recordatorio de ${row.patient_name}`}
              onClick={toggle}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-muted transition-colors hover:bg-primary/10 hover:text-primary-dark"
            >
              <MoreVertical className="h-4 w-4" />
            </button>
          )}
        >
          {({ close }) => (
            <>
              {row.is_pending && (
                <>
                  <DropdownItem
                    icon={<MessageCircle className="h-4 w-4" />}
                    onClick={() => {
                      close()
                      void sendWhatsApp(row)
                    }}
                  >
                    Enviar por WhatsApp
                  </DropdownItem>
                  <DropdownItem
                    icon={<Check className="h-4 w-4" />}
                    onClick={() => {
                      close()
                      void applyAction(
                        markSent.mutateAsync(row.id),
                        'No se pudo marcar como enviado',
                      )
                    }}
                  >
                    Marcar como enviado
                  </DropdownItem>
                  <DropdownItem
                    icon={<Pencil className="h-4 w-4" />}
                    onClick={() => {
                      close()
                      setSelected(row)
                      setFormOpen(true)
                    }}
                  >
                    Editar
                  </DropdownItem>
                  <DropdownItem
                    icon={<XCircle className="h-4 w-4" />}
                    variant="danger"
                    onClick={() => {
                      close()
                      void applyAction(cancel.mutateAsync(row.id), 'No se pudo cancelar')
                    }}
                  >
                    Cancelar
                  </DropdownItem>
                </>
              )}
              {!row.is_pending && (
                <DropdownItem icon={<Send className="h-4 w-4" />} onClick={close}>
                  {row.sent_at ? `Enviado ${formatDateTime(row.sent_at)}` : row.status_label}
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
        eyebrow="Seguimiento"
        title="Recordatorios"
        subtitle="Avisos de toma de medicamentos y de citas programadas"
        actions={
          <Button
            size="sm"
            leftIcon={<Plus className="h-4 w-4" />}
            onClick={() => {
              setSelected(null)
              setFormOpen(true)
            }}
          >
            Nuevo recordatorio
          </Button>
        }
      />

      {feedback && <Alert variant={feedback.tone}>{feedback.text}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
        <StatCard label="Pendientes hoy" value={stats?.pending_today ?? 0} icon={BellRing} />
        <StatCard
          label="Vencidos"
          value={stats?.overdue ?? 0}
          icon={AlarmClock}
          tone="danger"
          hint="requieren envío"
        />
        <StatCard label="Enviados hoy" value={stats?.sent_today ?? 0} icon={Send} />
        <StatCard
          label="Próximos 7 días"
          value={stats?.upcoming_week ?? 0}
          icon={CalendarClock}
          tone="info"
        />
      </section>

      <Card>
        <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
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
            options={STATUS_OPTIONS}
            placeholder="Todos los estados"
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(event.target.value)
              setPage(1)
            }}
          />
          <Input
            label="Desde"
            type="date"
            value={dateFrom}
            onChange={(event) => {
              setDateFrom(event.target.value)
              setPage(1)
            }}
          />
          <Input
            label="Hasta"
            type="date"
            value={dateTo}
            onChange={(event) => {
              setDateTo(event.target.value)
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
              icon={BellRing}
              title="Sin recordatorios"
              description="Los avisos se generan desde la agenda de citas y desde las recetas de cada atención."
            />
          }
        />

        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          labels={['recordatorio', 'recordatorios']}
          onChange={setPage}
        />
      </Card>

      <ReminderFormModal
        open={formOpen}
        reminder={selected}
        onClose={() => setFormOpen(false)}
      />
    </div>
  )
}
