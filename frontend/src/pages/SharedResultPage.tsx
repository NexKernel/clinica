import { useParams } from 'react-router-dom'
import { Download, FileText, Image as ImageIcon, ShieldCheck } from 'lucide-react'

import { Alert, Badge, Card, CardBody, CardHeader, LoadingState } from '@/components/ui'
import { useSharedStudy } from '@/features/studies/hooks/useStudies'
import { formatDateTime } from '@/lib/datetime'
import { apiOrigin, resolveMediaUrl } from '@/services/http'

/**
 * Consulta pública del resultado, abierta por el paciente desde el enlace que
 * el policlínico le envía por WhatsApp. No requiere iniciar sesión: el acceso
 * lo otorga el token temporal incluido en la dirección.
 */
export function SharedResultPage() {
  const { token } = useParams<{ token: string }>()
  const { study, isLoading, error } = useSharedStudy(token)

  return (
    <div className="min-h-screen bg-background px-4 py-10">
      <div className="mx-auto w-full max-w-2xl space-y-5">
        {isLoading && <LoadingState label="Cargando resultado" />}

        {error && (
          <Card>
            <CardBody className="space-y-3 text-center">
              <h1 className="text-xl">Enlace no disponible</h1>
              <p className="text-sm text-muted">{error}</p>
              <p className="text-sm text-muted">
                Comuníquese con el policlínico para solicitar un enlace nuevo.
              </p>
            </CardBody>
          </Card>
        )}

        {study && (
          <>
            <header className="flex items-center gap-3">
              {study.clinic_logo_url ? (
                <img
                  src={resolveMediaUrl(study.clinic_logo_url) ?? ''}
                  alt={study.clinic_name}
                  className="h-12 w-12 rounded-xl object-contain"
                />
              ) : (
                <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <FileText className="h-5 w-5" />
                </span>
              )}
              <div className="min-w-0">
                <h1 className="truncate text-xl">{study.clinic_name}</h1>
                <p className="text-sm text-muted">Resultado de examen</p>
              </div>
            </header>

            <Alert variant="info">
              Este enlace es personal y vence el {formatDateTime(study.expires_at)}. No lo comparta
              con terceros.
            </Alert>

            <Card>
              <CardHeader
                title={study.study_name}
                description={`${study.type_label} · ${study.patient_name}`}
                action={<Badge variant="success" dot>Completado</Badge>}
              />
              <CardBody className="space-y-4">
                {study.performed_at && (
                  <p className="text-sm text-muted">
                    Realizado el {formatDateTime(study.performed_at)}
                    {study.performed_by ? ` por ${study.performed_by}` : ''}
                  </p>
                )}

                {study.result_summary && (
                  <div>
                    <p className="caption uppercase tracking-wide">Conclusión</p>
                    <p className="mt-1 text-sm text-foreground">{study.result_summary}</p>
                  </div>
                )}

                {study.report && (
                  <div>
                    <p className="caption uppercase tracking-wide">Informe</p>
                    <p className="mt-1 whitespace-pre-line text-sm text-foreground">
                      {study.report}
                    </p>
                  </div>
                )}
              </CardBody>
            </Card>

            {study.attachments.length > 0 && (
              <Card>
                <CardHeader title="Archivos" description="Descargue el resultado en su equipo" />
                <ul className="divide-y divide-border">
                  {study.attachments.map((attachment) => (
                    <li key={attachment.id} className="flex items-center gap-3 px-5 py-3.5">
                      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                        {attachment.is_image ? (
                          <ImageIcon className="h-4 w-4" />
                        ) : (
                          <FileText className="h-4 w-4" />
                        )}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground">
                          {attachment.filename}
                        </p>
                        <p className="text-xs text-muted">{attachment.size_label}</p>
                      </div>
                      <a
                        href={`${apiOrigin}${attachment.url}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-xl border border-primary/40 px-3.5 py-2 text-sm font-medium text-primary-dark transition-colors hover:bg-primary/10"
                      >
                        <Download className="h-4 w-4" />
                        Abrir
                      </a>
                    </li>
                  ))}
                </ul>
              </Card>
            )}

            <p className="flex items-center justify-center gap-1.5 text-xs text-muted">
              <ShieldCheck className="h-3.5 w-3.5" />
              Información confidencial del paciente
            </p>
          </>
        )}
      </div>
    </div>
  )
}
