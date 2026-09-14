import {
  AlertTriangle,
  BellRing,
  CalendarClock,
  CalendarDays,
  Clock3,
  FlaskConical,
  Truck,
  UserCheck,
  Wallet,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import {
  Alert,
  Badge,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  LoadingState,
  StatCard,
  Table,
  type BadgeVariant,
  type Column,
} from '@/components/ui'
import { useAuth } from '@/features/auth/hooks/useAuth'
import {
  AppointmentStatusChart,
  AttentionsChart,
  RevenueChart,
} from '@/features/dashboard/components/DashboardCharts'
import { useDashboardSummary } from '@/features/dashboard/hooks/useDashboard'
import { useClinicIdentity } from '@/features/settings/hooks/useClinicIdentity'
import { formatLongDate, formatTime, greetingByHour } from '@/lib/datetime'
import { cn, formatCurrency, trendBetween } from '@/lib/utils'
import { ROUTES } from '@/routes/paths'
import type { Appointment, AppointmentStatus, LowStockItem } from '@/types'

const STATUS_VARIANT: Record<AppointmentStatus, BadgeVariant> = {
  PROGRAMADA: 'warning',
  CONFIRMADA: 'info',
  EN_ATENCION: 'primary',
  ATENDIDA: 'success',
  CANCELADA: 'danger',
  NO_ASISTIO: 'neutral',
}

const APPOINTMENT_COLUMNS: Column<Appointment>[] = [
  {
    key: 'time',
    header: 'Hora',
    className: 'w-20 font-semibold text-foreground',
    render: (row) => formatTime(row.scheduled_at),
  },
  {
    key: 'patient',
    header: 'Paciente',
    className: 'font-medium text-foreground',
    render: (row) => row.patient_name,
  },
  {
    key: 'specialty',
    header: 'Especialidad',
    className: 'text-muted',
    render: (row) => row.specialty_name ?? row.service_name ?? '—',
  },
  {
    key: 'professional',
    header: 'Profesional',
    className: 'text-muted',
    render: (row) => row.practitioner_name,
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
]

const RESTOCK_COLUMNS: Column<LowStockItem>[] = [
  {
    key: 'product',
    header: 'Producto',
    className: 'font-medium text-foreground',
    render: (row) => row.full_name,
  },
  {
    key: 'stock',
    header: 'Stock',
    className: 'w-24',
    render: (row) => (
      <span className={row.is_out_of_stock ? 'font-semibold text-danger' : 'text-foreground'}>
        {row.stock}
      </span>
    ),
  },
  { key: 'min', header: 'Mínimo', className: 'w-24 text-muted', render: (row) => row.min_stock },
  {
    key: 'suggested',
    header: 'Sugerido',
    className: 'w-28',
    render: (row) => (row.suggested_purchase > 0 ? `${row.suggested_purchase} u.` : '—'),
  },
]

export function DashboardPage() {
  const { user } = useAuth()
  const clinic = useClinicIdentity()
  const { summary, isLoading, error } = useDashboardSummary()
  const firstName = user?.full_name.split(' ')[0] ?? ''

  const totals = summary?.totals
  const alerts = summary?.alerts

  /* El servidor omite la caja para los perfiles que no consultan ventas: el
     panel se arma sin esa tarjeta ni el gráfico de ingresos. */
  const showsRevenue = totals?.revenue_today != null

  const alertCards = [
    {
      key: 'stock',
      label: 'Productos por reponer',
      value: alerts?.low_stock ?? 0,
      icon: AlertTriangle,
      to: ROUTES.pharmacy,
    },
    {
      key: 'expired',
      label: 'Productos vencidos',
      value: alerts?.expired ?? 0,
      icon: CalendarClock,
      to: ROUTES.pharmacy,
    },
    {
      key: 'expiring',
      label: 'Productos por vencer',
      value: alerts?.expiring_soon ?? 0,
      icon: CalendarClock,
      to: ROUTES.pharmacy,
    },
    {
      key: 'studies',
      label: 'Resultados pendientes',
      value: alerts?.pending_studies ?? 0,
      icon: FlaskConical,
      to: ROUTES.studies,
    },
    {
      key: 'reminders',
      label: 'Recordatorios vencidos',
      value: alerts?.pending_reminders ?? 0,
      icon: BellRing,
      to: ROUTES.reminders,
    },
    {
      key: 'purchases',
      label: 'Compras en borrador',
      value: alerts?.draft_purchases ?? 0,
      icon: Truck,
      to: ROUTES.purchases,
    },
  ].filter((item) => item.value > 0)

  return (
    <div className="space-y-6">
      <header>
        <p className="caption uppercase tracking-wide">{formatLongDate()}</p>
        <h1 className="mt-1">
          {greetingByHour()}
          {firstName ? `, ${firstName}` : ''}
        </h1>
        <p className="mt-1 text-sm text-muted">Resumen de atención del {clinic.name}</p>
      </header>

      {error && <Alert variant="danger">{error}</Alert>}
      {isLoading && !summary && <LoadingState label="Cargando indicadores" />}

      {summary && totals && (
        <>
          <section
            className={cn(
              'grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4',
              showsRevenue ? 'xl:grid-cols-4' : 'xl:grid-cols-3',
            )}
          >
            <StatCard
              label="Citas de hoy"
              value={totals.appointments_today}
              icon={CalendarDays}
              tone="primary"
              trend={trendBetween(totals.appointments_today, totals.appointments_yesterday)}
              hint="vs. ayer"
            />
            <StatCard
              label="Pacientes atendidos"
              value={totals.attended_today}
              icon={UserCheck}
              tone="info"
              hint="citas cerradas"
            />
            <StatCard
              label="Pacientes en espera"
              value={totals.pending_today}
              icon={Clock3}
              tone="warning"
              hint="programadas o confirmadas"
            />
            {showsRevenue && (
              <StatCard
                label="Ingresos del día"
                value={formatCurrency(totals.revenue_today ?? 0)}
                icon={Wallet}
                tone="primary"
                trend={trendBetween(totals.revenue_today ?? 0, totals.revenue_yesterday ?? 0)}
                hint="caja general"
              />
            )}
          </section>

          {alertCards.length > 0 && (
            <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {alertCards.map(({ key, label, value, icon: Icon, to }) => (
                <Link
                  key={key}
                  to={to}
                  className="flex items-center gap-3 rounded-2xl border border-warning/40 bg-warning/10 px-4 py-3 transition-colors hover:bg-warning/20"
                >
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-warning/20 text-warning-dark">
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-foreground">{value}</p>
                    <p className="truncate text-xs text-warning-dark">{label}</p>
                  </div>
                </Link>
              ))}
            </section>
          )}

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <div className="space-y-4 xl:col-span-2">
              <AttentionsChart points={summary.attentions_series} />
              {showsRevenue && <RevenueChart points={summary.revenue_series} />}
            </div>

            <div className="space-y-4">
              <AppointmentStatusChart slices={summary.appointment_status} />

              <Card>
                <CardHeader
                  title="Reposición de stock"
                  description="Productos en o por debajo del mínimo"
                />
                {summary.restock_items.length === 0 ? (
                  <CardBody>
                    <p className="text-sm text-muted">
                      Ningún producto requiere reposición en este momento.
                    </p>
                  </CardBody>
                ) : (
                  <Table
                    columns={RESTOCK_COLUMNS}
                    data={summary.restock_items}
                    keyExtractor={(row) => row.id}
                  />
                )}
              </Card>
            </div>
          </section>

          <Card>
            <CardHeader
              title="Próximas citas"
              description="Agenda pendiente del día en curso"
              action={
                <Link
                  to={ROUTES.appointments}
                  className="inline-flex items-center rounded-xl px-3.5 py-2 text-sm font-medium text-muted transition-colors hover:bg-primary/10 hover:text-primary-dark"
                >
                  Ver agenda
                </Link>
              }
            />
            <Table
              columns={APPOINTMENT_COLUMNS}
              data={summary.upcoming_appointments}
              keyExtractor={(row) => row.id}
              emptyState={
                <EmptyState
                  icon={CalendarDays}
                  title="Sin citas pendientes"
                  description="Las citas por atender del día aparecerán aquí."
                />
              }
            />
          </Card>
        </>
      )}
    </div>
  )
}
