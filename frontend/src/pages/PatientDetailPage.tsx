import { useState } from 'react'
import {
  AlertTriangle,
  ArrowLeft,
  CalendarDays,
  CalendarPlus,
  ChevronRight,
  ClipboardList,
  FileSignature,
  FlaskConical,
  IdCard,
  LayoutList,
  Pencil,
  ShieldAlert,
  Stethoscope,
  UserX,
} from 'lucide-react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import {
  Alert,
  Avatar,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  LoadingState,
} from '@/components/ui'
import { usePatientAppointments } from '@/features/appointments/hooks/useAppointments'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { DocumentSheetModal } from '@/features/documents/components/DocumentSheetModal'
import { usePatientDocuments } from '@/features/documents/hooks/useDocuments'
import { useMedicalRecord } from '@/features/encounters/hooks/useEncounters'
import {
  PatientAppointmentsPanel,
  PatientDocumentsPanel,
  PatientEncountersPanel,
  PatientHistoryPanel,
  PatientProfilePanel,
  PatientStudiesPanel,
} from '@/features/patients/components/PatientDetailPanels'
import { PatientFormModal } from '@/features/patients/components/PatientFormModal'
import { usePatient } from '@/features/patients/hooks/usePatients'
import { usePatientStudies } from '@/features/studies/hooks/useStudies'
import { cn } from '@/lib/utils'
import { rolesForNavItem } from '@/routes/navigation'
import { ROUTES } from '@/routes/paths'
import { hasRole } from '@/store/auth.store'
import type { LucideIcon } from 'lucide-react'
import type { Role } from '@/types'

/* Cada sección consulta el módulo del que toma sus datos, así que se muestra
   sólo a los perfiles que pueden verlo: caja abre la ficha del paciente pero no
   accede a su historia, sus resultados ni sus documentos. */
interface Section {
  key: string
  label: string
  icon: LucideIcon
  roles?: Role[]
}

const SECTIONS: Section[] = [
  { key: 'resumen', label: 'Resumen', icon: LayoutList },
  { key: 'perfil', label: 'Perfil', icon: IdCard },
  { key: 'citas', label: 'Citas', icon: CalendarDays, roles: rolesForNavItem('appointments') },
  {
    key: 'atenciones',
    label: 'Atenciones',
    icon: ClipboardList,
    roles: rolesForNavItem('medical-records'),
  },
  { key: 'resultados', label: 'Resultados', icon: FlaskConical, roles: rolesForNavItem('studies') },
  {
    key: 'documentos',
    label: 'Documentos',
    icon: FileSignature,
    roles: rolesForNavItem('documents'),
  },
]

/** Forma del identificador opaco que viaja en /pacientes/:patientId. */
const PUBLIC_ID_PATTERN = /^[0-9a-f]{32}$/

export function PatientDetailPage() {
  const navigate = useNavigate()
  // La URL trae el `public_id`; el id interno sale de la ficha ya cargada y
  // es el que consumen los módulos anidados (citas, atenciones, resultados).
  const { patientId } = useParams<{ patientId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const { user } = useAuth()

  // Una ruta con otra forma (un correlativo antiguo, un enlace roto) no llega
  // al servidor: se resuelve aquí como ficha inexistente.
  const publicId = patientId && PUBLIC_ID_PATTERN.test(patientId) ? patientId : null

  const { patient, isLoading, error } = usePatient(publicId)
  const id = patient?.id ?? null

  const sections = SECTIONS.filter((item) => hasRole(user, item.roles))
  const requested = searchParams.get('seccion') ?? 'resumen'
  /* La sección viaja en la URL para que recargar o volver atrás no pierda el
     lugar; si el perfil no la puede ver, se cae al resumen. */
  const section = sections.some((item) => item.key === requested) ? requested : 'resumen'

  const allows = (key: string) => sections.some((item) => item.key === key)
  const loads = (key: string) => (allows(key) ? id : null)

  const { appointments, isLoading: loadingAppointments } = usePatientAppointments(loads('citas'))
  const { record, isLoading: loadingRecord } = useMedicalRecord(loads('atenciones'))
  const { studies, isLoading: loadingStudies } = usePatientStudies(loads('resultados'))
  const { documents, isLoading: loadingDocuments } = usePatientDocuments(loads('documentos'))

  const [editOpen, setEditOpen] = useState(false)
  // La hoja se abre sobre la ficha: se consulta al servidor, que devuelve la
  // versión congelada del documento emitido.
  const [sheetId, setSheetId] = useState<number | null>(null)

  const selectSection = (key: string) => {
    setSearchParams(key === 'resumen' ? {} : { seccion: key }, { replace: true })
  }

  const backLink = (
    <Link
      to={ROUTES.patients}
      className="inline-flex items-center gap-2 text-sm font-medium text-muted transition-colors hover:text-primary-dark"
    >
      <ArrowLeft className="h-4 w-4" />
      Regresar a pacientes
    </Link>
  )

  if (isLoading) {
    return (
      <div className="space-y-5">
        {backLink}
        <LoadingState label="Cargando ficha del paciente" />
      </div>
    )
  }

  if (!patient) {
    return (
      <div className="space-y-5">
        {backLink}
        <Card>
          <EmptyState
            icon={UserX}
            title="Paciente no encontrado"
            description={error ?? 'El paciente solicitado no existe o fue dado de baja.'}
            action={
              <Button size="sm" onClick={() => navigate(ROUTES.patients)}>
                Ir al listado
              </Button>
            }
          />
        </Card>
      </div>
    )
  }

  const encounters = record?.encounters ?? []

  const seeAll = (key: string) =>
    allows(key) ? (
      <button
        type="button"
        onClick={() => selectSection(key)}
        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-primary-dark transition-colors hover:bg-primary/10"
      >
        Ver todo
        <ChevronRight className="h-3.5 w-3.5" />
      </button>
    ) : undefined

  return (
    <div className="space-y-5">
      {backLink}

      <Card>
        <CardBody className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-4">
            <Avatar name={patient.full_name} size="lg" />
            <div className="min-w-0">
              <h1 className="truncate text-xl font-semibold text-foreground sm:text-2xl">
                {patient.full_name}
              </h1>
              <p className="mt-0.5 truncate text-sm text-muted">
                Historia {patient.history_number} · {patient.document_label}
                {patient.age !== null ? ` · ${patient.age} años` : ''}
                {patient.sex_label ? ` · ${patient.sex_label}` : ''}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <Badge variant={patient.is_active ? 'success' : 'neutral'} dot>
              {patient.is_active ? 'Activo' : 'Inactivo'}
            </Badge>
            <Button
              size="sm"
              variant="outline"
              leftIcon={<Pencil className="h-4 w-4" />}
              onClick={() => setEditOpen(true)}
            >
              Editar
            </Button>
            <Button
              size="sm"
              leftIcon={<CalendarPlus className="h-4 w-4" />}
              disabled={!patient.is_active}
              onClick={() => navigate(`${ROUTES.appointments}?patient=${patient.public_id}`)}
            >
              Programar cita
            </Button>
          </div>
        </CardBody>
      </Card>

      {patient.has_alerts && (
        <Alert variant="danger">
          <span className="flex flex-col gap-0.5">
            {patient.allergies && (
              <span>
                <strong>Alergias:</strong> {patient.allergies}
              </span>
            )}
            {patient.current_medication && (
              <span>
                <strong>Medicación actual:</strong> {patient.current_medication}
              </span>
            )}
          </span>
        </Alert>
      )}

      {!patient.is_active && (
        <Alert variant="warning">
          <span className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Este paciente está inactivo y no puede recibir nuevas citas.
          </span>
        </Alert>
      )}

      <div className="grid gap-5 lg:grid-cols-[13.5rem_minmax(0,1fr)]">
        {/* En móvil la navegación es una tira horizontal; desde lg pasa a ser
            la columna lateral fija de la ficha. */}
        <nav className="scrollbar-thin -mx-1 flex gap-1 overflow-x-auto px-1 pb-1 lg:sticky lg:top-20 lg:mx-0 lg:h-fit lg:flex-col lg:overflow-visible lg:px-0 lg:pb-0">
          {sections.map((item) => {
            const Icon = item.icon
            const isActive = item.key === section

            return (
              <button
                key={item.key}
                type="button"
                aria-current={isActive ? 'page' : undefined}
                onClick={() => selectSection(item.key)}
                className={cn(
                  'inline-flex shrink-0 items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-colors lg:w-full',
                  isActive
                    ? 'bg-primary/10 text-primary-dark'
                    : 'text-muted hover:bg-primary/5 hover:text-primary-dark',
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {item.label}
              </button>
            )
          })}
        </nav>

        <div className="min-w-0">
          {section === 'resumen' && (
            <div className="space-y-4">
              <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
                <Card className="flex flex-col xl:row-span-2">
                  <CardHeader title="Perfil" description="Filiación y contacto" />
                  <CardBody className="flex-1">
                    <PatientProfilePanel patient={patient} />
                  </CardBody>
                </Card>

                {allows('atenciones') && (
                  <Card className="flex flex-col">
                    <CardHeader title="Atenciones" action={seeAll('atenciones')} />
                    <CardBody className="flex-1">
                      <PatientEncountersPanel
                        encounters={encounters}
                        isLoading={loadingRecord}
                        limit={4}
                      />
                    </CardBody>
                  </Card>
                )}

                {allows('citas') && (
                  <Card className="flex flex-col">
                    <CardHeader title="Citas" action={seeAll('citas')} />
                    <CardBody className="flex-1">
                      <PatientAppointmentsPanel
                        appointments={appointments}
                        isLoading={loadingAppointments}
                        limit={4}
                      />
                    </CardBody>
                  </Card>
                )}

                {allows('resultados') && (
                  <Card className="flex flex-col">
                    <CardHeader title="Resultados" action={seeAll('resultados')} />
                    <CardBody className="flex-1">
                      <PatientStudiesPanel studies={studies} isLoading={loadingStudies} limit={4} />
                    </CardBody>
                  </Card>
                )}

                {allows('documentos') && (
                  <Card className="flex flex-col">
                    <CardHeader title="Documentos" action={seeAll('documentos')} />
                    <CardBody className="flex-1">
                      <PatientDocumentsPanel
                        documents={documents}
                        isLoading={loadingDocuments}
                        limit={4}
                        onPrint={setSheetId}
                      />
                    </CardBody>
                  </Card>
                )}
              </div>

              <Card>
                <CardHeader title="Antecedentes" description="Registrados en la ficha" />
                <CardBody>
                  <PatientHistoryPanel patient={patient} />
                </CardBody>
              </Card>
            </div>
          )}

          {section === 'perfil' && (
            <div className="space-y-4">
              <Card>
                <CardHeader title="Datos del paciente" />
                <CardBody>
                  <PatientProfilePanel patient={patient} />
                </CardBody>
              </Card>
              <Card>
                <CardHeader title="Antecedentes" />
                <CardBody>
                  <PatientHistoryPanel patient={patient} />
                </CardBody>
              </Card>
            </div>
          )}

          {section === 'citas' && (
            <Card>
              <CardHeader title="Citas del paciente" description="Historial completo de la agenda" />
              <CardBody>
                <PatientAppointmentsPanel
                  appointments={appointments}
                  isLoading={loadingAppointments}
                />
              </CardBody>
            </Card>
          )}

          {section === 'atenciones' && (
            <Card>
              <CardHeader
                title="Atenciones"
                description={
                  record
                    ? `${record.total_encounters} atención(es) registradas`
                    : 'Historia clínica del paciente'
                }
                action={
                  <Button
                    size="sm"
                    variant="ghost"
                    leftIcon={<Stethoscope className="h-4 w-4" />}
                    onClick={() => navigate(`${ROUTES.medicalRecords}?patient=${patient.public_id}`)}
                  >
                    Historia completa
                  </Button>
                }
              />
              <CardBody>
                <PatientEncountersPanel encounters={encounters} isLoading={loadingRecord} />
              </CardBody>
            </Card>
          )}

          {section === 'resultados' && (
            <Card>
              <CardHeader title="Resultados" description="Exámenes y estudios de imagen" />
              <CardBody>
                <PatientStudiesPanel studies={studies} isLoading={loadingStudies} />
              </CardBody>
            </Card>
          )}

          {section === 'documentos' && (
            <Card>
              <CardHeader title="Documentos" description="Informes, fichas y consentimientos" />
              <CardBody>
                <PatientDocumentsPanel
                  documents={documents}
                  isLoading={loadingDocuments}
                  onPrint={setSheetId}
                />
              </CardBody>
            </Card>
          )}

          {sections.length === 1 && section === 'resumen' && (
            <p className="mt-4 flex items-center gap-2 text-xs text-muted">
              <ShieldAlert className="h-3.5 w-3.5" />
              Su perfil sólo tiene acceso a los datos de filiación del paciente.
            </p>
          )}
        </div>
      </div>

      <PatientFormModal open={editOpen} patient={patient} onClose={() => setEditOpen(false)} />

      <DocumentSheetModal
        open={sheetId !== null}
        documentId={sheetId}
        onClose={() => setSheetId(null)}
      />
    </div>
  )
}
