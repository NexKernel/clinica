import { useState } from 'react'
import { CalendarDays, ClipboardList, FileText, FlaskConical, Pill, Search } from 'lucide-react'

import {
  Alert,
  Badge,
  Card,
  CardBody,
  CardHeader,
  DataSummary,
  EmptyState,
  LoadingState,
  PageHeader,
  StatCard,
} from '@/components/ui'
import { encountersApi } from '@/features/encounters/api/encounters.api'
import { useMedicalRecord } from '@/features/encounters/hooks/useEncounters'
import { PatientPicker } from '@/features/patients/components/PatientPicker'
import { usePatientStudies } from '@/features/studies/hooks/useStudies'
import { formatDate, formatDateTime } from '@/lib/datetime'
import { getErrorMessage } from '@/services/http'
import type { Encounter, PatientSummary } from '@/types'

export function MedicalRecordsPage() {
  const [patient, setPatient] = useState<PatientSummary | null>(null)
  const [expanded, setExpanded] = useState<Encounter | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)

  const patientId = patient?.id ?? null
  const { record, isLoading, error } = useMedicalRecord(patientId)
  const { studies } = usePatientStudies(patientId)

  const openEncounter = async (encounterId: number) => {
    setDetailError(null)
    if (expanded?.id === encounterId) {
      setExpanded(null)
      return
    }
    try {
      setExpanded(await encountersApi.get(encounterId))
    } catch (err) {
      setDetailError(getErrorMessage(err, 'No se pudo cargar la atención'))
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Atención"
        title="Historia clínica"
        subtitle="Consulta consolidada de atenciones, diagnósticos y resultados"
      />

      <Card>
        <CardBody>
          <PatientPicker
            label="Buscar paciente"
            value={patient}
            onChange={(value) => {
              setPatient(value)
              setExpanded(null)
            }}
            hint="Escriba el nombre, documento o número de historia"
          />
        </CardBody>
      </Card>

      {!patient && (
        <Card>
          <EmptyState
            icon={Search}
            title="Seleccione un paciente"
            description="La historia clínica se muestra al elegir un paciente registrado."
          />
        </Card>
      )}

      {error && <Alert variant="danger">{error}</Alert>}
      {detailError && <Alert variant="danger">{detailError}</Alert>}

      {patient && isLoading && <LoadingState label="Cargando historia clínica" />}

      {patient && record && !isLoading && (
        <>
          <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
            <StatCard label="Atenciones" value={record.total_encounters} icon={ClipboardList} />
            <StatCard
              label="Última atención"
              value={record.last_encounter_at ? formatDate(record.last_encounter_at) : '—'}
              icon={CalendarDays}
              tone="info"
            />
            <StatCard label="Estudios" value={studies.length} icon={FlaskConical} tone="info" />
            <StatCard
              label="Historia"
              value={record.patient.history_number}
              icon={FileText}
              hint={record.patient.full_name}
            />
          </section>

          <Card>
            <CardHeader
              title="Atenciones registradas"
              description="Seleccione una atención para ver su detalle clínico"
            />
            {record.encounters.length === 0 ? (
              <EmptyState
                icon={ClipboardList}
                title="Sin atenciones"
                description="Este paciente aún no tiene atenciones registradas."
              />
            ) : (
              <ul className="divide-y divide-border">
                {record.encounters.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => void openEncounter(item.id)}
                      className="flex w-full items-start justify-between gap-3 px-5 py-4 text-left transition-colors hover:bg-primary/5"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground">
                          {formatDateTime(item.started_at)}
                        </p>
                        <p className="truncate text-xs text-muted">
                          {item.practitioner_name}
                          {item.specialty_name ? ` · ${item.specialty_name}` : ''}
                        </p>
                        {item.main_diagnosis && (
                          <p className="mt-1 text-sm text-foreground">{item.main_diagnosis}</p>
                        )}
                      </div>
                      <Badge
                        variant={item.status === 'FINALIZADA' ? 'success' : 'warning'}
                        dot
                      >
                        {item.status_label}
                      </Badge>
                    </button>

                    {expanded?.id === item.id && (
                      <div className="space-y-5 border-t border-border bg-background/50 px-5 py-4">
                        <DataSummary
                          items={[
                            { label: 'Motivo', value: expanded.chief_complaint },
                            { label: 'Presión arterial', value: expanded.blood_pressure },
                            {
                              label: 'Frecuencia cardiaca',
                              value: expanded.heart_rate ? `${expanded.heart_rate} lpm` : null,
                            },
                            {
                              label: 'Temperatura',
                              value: expanded.temperature ? `${expanded.temperature} °C` : null,
                            },
                            {
                              label: 'Peso / Talla',
                              value: [
                                expanded.weight_kg ? `${expanded.weight_kg} kg` : null,
                                expanded.height_cm ? `${expanded.height_cm} cm` : null,
                              ]
                                .filter(Boolean)
                                .join(' · '),
                            },
                            { label: 'IMC', value: expanded.bmi },
                          ]}
                        />

                        <DataSummary
                          columns={2}
                          items={[
                            { label: 'Enfermedad actual', value: expanded.current_illness },
                            { label: 'Examen físico', value: expanded.physical_exam },
                            { label: 'Plan de tratamiento', value: expanded.treatment_plan },
                            { label: 'Indicaciones', value: expanded.indications },
                          ]}
                        />

                        {expanded.diagnoses.length > 0 && (
                          <div>
                            <p className="caption mb-2 uppercase tracking-wide">Diagnósticos</p>
                            <ul className="space-y-1.5">
                              {expanded.diagnoses.map((diagnosis) => (
                                <li
                                  key={diagnosis.id}
                                  className="flex items-center gap-2 text-sm text-foreground"
                                >
                                  <Badge variant="primary">{diagnosis.kind_label}</Badge>
                                  {diagnosis.summary}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {expanded.prescriptions.length > 0 && (
                          <div>
                            <p className="caption mb-2 flex items-center gap-1.5 uppercase tracking-wide">
                              <Pill className="h-3.5 w-3.5" />
                              Receta
                            </p>
                            <ul className="space-y-1.5">
                              {expanded.prescriptions.map((prescription) => (
                                <li key={prescription.id} className="text-sm text-foreground">
                                  <span className="font-medium">{prescription.medication}</span>
                                  {prescription.schedule_label
                                    ? ` — ${prescription.schedule_label}`
                                    : ''}
                                  {prescription.instructions && (
                                    <span className="block text-xs text-muted">
                                      {prescription.instructions}
                                    </span>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader
              title="Resultados y estudios"
              description="Exámenes de laboratorio, Rayos X y otros apoyos al diagnóstico"
            />
            {studies.length === 0 ? (
              <EmptyState
                icon={FlaskConical}
                title="Sin estudios"
                description="Los resultados registrados aparecerán aquí."
              />
            ) : (
              <ul className="divide-y divide-border">
                {studies.map((study) => (
                  <li key={study.id} className="flex items-start justify-between gap-3 px-5 py-3.5">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">{study.name}</p>
                      <p className="truncate text-xs text-muted">
                        {study.type_label} · {formatDate(study.requested_at)}
                      </p>
                      {study.result_summary && (
                        <p className="mt-1 text-sm text-foreground">{study.result_summary}</p>
                      )}
                    </div>
                    <Badge variant={study.status === 'COMPLETADO' ? 'success' : 'warning'} dot>
                      {study.status_label}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  )
}
