import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import {
  Copy,
  Download,
  FileText,
  Image as ImageIcon,
  Link2,
  Paperclip,
  Save,
  Send,
  Trash2,
} from 'lucide-react'

import {
  Alert,
  Badge,
  Button,
  Input,
  LoadingState,
  Modal,
  Switch,
  Textarea,
} from '@/components/ui'
import { studiesApi } from '@/features/studies/api/studies.api'
import { useStudy, useStudyActions } from '@/features/studies/hooks/useStudies'
import { formatDateTime } from '@/lib/datetime'
import { getErrorMessage } from '@/services/http'
import type { ShareLink } from '@/types'

const ACCEPTED_TYPES = '.pdf,.png,.jpg,.jpeg,.webp,.tif,.tiff'

interface StudyResultModalProps {
  open: boolean
  studyId: number | null
  onClose: () => void
}

export function StudyResultModal({ open, studyId, onClose }: StudyResultModalProps) {
  const { study, isLoading, error } = useStudy(open ? studyId : null)
  const { registerResult, upload, removeAttachment, share, revokeShare } = useStudyActions()
  const fileInput = useRef<HTMLInputElement>(null)

  const [summary, setSummary] = useState('')
  const [report, setReport] = useState('')
  const [performedBy, setPerformedBy] = useState('')
  const [complete, setComplete] = useState(true)
  const [shareLink, setShareLink] = useState<ShareLink | null>(null)
  const [feedback, setFeedback] = useState<{ tone: 'success' | 'danger'; text: string } | null>(null)

  useEffect(() => {
    if (!open || !study) return
    setSummary(study.result_summary ?? '')
    setReport(study.report ?? '')
    setPerformedBy(study.performed_by ?? '')
    setComplete(study.status !== 'COMPLETADO')
    setShareLink(null)
    setFeedback(null)
  }, [open, study])

  const saveResult = async () => {
    if (!study) return
    setFeedback(null)
    try {
      await registerResult.mutateAsync({
        id: study.id,
        payload: {
          result_summary: summary.trim() || null,
          report: report.trim() || null,
          performed_by: performedBy.trim() || null,
          performed_at: null,
          complete,
        },
      })
      setFeedback({ tone: 'success', text: 'Resultado registrado correctamente.' })
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo guardar el resultado') })
    }
  }

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !study) return

    setFeedback(null)
    try {
      await upload.mutateAsync({ id: study.id, file })
      setFeedback({ tone: 'success', text: `Se adjuntó ${file.name}.` })
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo adjuntar el archivo') })
    }
  }

  const download = async (attachmentId: number, filename: string) => {
    try {
      const blob = await studiesApi.downloadAttachment(attachmentId)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo descargar el archivo') })
    }
  }

  const createShareLink = async () => {
    if (!study) return
    setFeedback(null)
    try {
      setShareLink(await share.mutateAsync(study.id))
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo generar el enlace') })
    }
  }

  const copyLink = async () => {
    if (!shareLink) return
    try {
      await navigator.clipboard.writeText(shareLink.url)
      setFeedback({ tone: 'success', text: 'Enlace copiado al portapapeles.' })
    } catch {
      setFeedback({ tone: 'danger', text: 'El navegador no permitió copiar el enlace.' })
    }
  }

  const revoke = async () => {
    if (!study) return
    try {
      await revokeShare.mutateAsync(study.id)
      setShareLink(null)
      setFeedback({ tone: 'success', text: 'El enlace anterior quedó sin efecto.' })
    } catch (err) {
      setFeedback({ tone: 'danger', text: getErrorMessage(err, 'No se pudo anular el enlace') })
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={study ? study.name : 'Resultado del estudio'}
      description={study ? `${study.type_label} · ${study.patient_name}` : undefined}
      size="xl"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cerrar
          </Button>
          {study && (
            <Button
              size="sm"
              isLoading={registerResult.isPending}
              leftIcon={<Save className="h-4 w-4" />}
              onClick={() => void saveResult()}
            >
              Guardar resultado
            </Button>
          )}
        </>
      }
    >
      {isLoading && <LoadingState label="Cargando estudio" />}
      {error && <Alert variant="danger">{error}</Alert>}

      {study && (
        <div className="space-y-5">
          {feedback && <Alert variant={feedback.tone}>{feedback.text}</Alert>}

          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={study.is_completed ? 'success' : 'warning'} dot>
              {study.status_label}
            </Badge>
            {study.requested_by_name && (
              <span className="text-xs text-muted">Solicitado por {study.requested_by_name}</span>
            )}
            {study.performed_at && (
              <span className="text-xs text-muted">
                Realizado el {formatDateTime(study.performed_at)}
              </span>
            )}
          </div>

          {study.clinical_notes && (
            <p className="rounded-xl bg-background/70 px-4 py-3 text-sm text-foreground">
              <span className="caption block uppercase tracking-wide">Indicación clínica</span>
              {study.clinical_notes}
            </p>
          )}

          <Input
            label="Resumen del resultado"
            placeholder="Conclusión breve que se muestra en el listado"
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
          />

          <Textarea
            label="Informe"
            rows={6}
            placeholder="Informe completo del estudio"
            value={report}
            onChange={(event) => setReport(event.target.value)}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Realizado por"
              placeholder="Tecnólogo, laboratorista o médico"
              value={performedBy}
              onChange={(event) => setPerformedBy(event.target.value)}
            />
            <div className="flex items-end">
              <Switch
                label="Marcar como completado"
                description="Solo los estudios completados se pueden enviar al paciente"
                checked={complete}
                onChange={setComplete}
              />
            </div>
          </div>

          <div className="border-t border-border pt-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <p className="caption flex items-center gap-1.5 uppercase tracking-wide">
                <Paperclip className="h-3.5 w-3.5" />
                Archivos adjuntos
              </p>
              <input
                ref={fileInput}
                type="file"
                accept={ACCEPTED_TYPES}
                className="hidden"
                onChange={(event) => void handleUpload(event)}
              />
              <Button
                variant="outline"
                size="sm"
                isLoading={upload.isPending}
                leftIcon={<Paperclip className="h-4 w-4" />}
                onClick={() => fileInput.current?.click()}
              >
                Adjuntar archivo
              </Button>
            </div>

            {study.attachments.length === 0 ? (
              <p className="text-sm text-muted">
                Aún no hay archivos. Se aceptan PDF e imágenes de hasta 10 MB.
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {study.attachments.map((attachment) => (
                  <li key={attachment.id} className="flex items-center gap-3 py-2.5">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
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
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Descargar ${attachment.filename}`}
                      onClick={() => void download(attachment.id, attachment.filename)}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Eliminar ${attachment.filename}`}
                      onClick={() => void removeAttachment.mutateAsync(attachment.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="border-t border-border pt-4">
            <p className="caption mb-3 flex items-center gap-1.5 uppercase tracking-wide">
              <Send className="h-3.5 w-3.5" />
              Envío al paciente
            </p>

            {!study.is_completed ? (
              <p className="text-sm text-muted">
                Marque el estudio como completado para poder compartir el resultado.
              </p>
            ) : (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    isLoading={share.isPending}
                    leftIcon={<Link2 className="h-4 w-4" />}
                    onClick={() => void createShareLink()}
                  >
                    Generar enlace
                  </Button>
                  {shareLink?.whatsapp_url && (
                    <Button
                      variant="outline"
                      size="sm"
                      leftIcon={<Send className="h-4 w-4" />}
                      onClick={() => window.open(shareLink.whatsapp_url as string, '_blank')}
                    >
                      Enviar por WhatsApp
                    </Button>
                  )}
                  {shareLink && (
                    <Button
                      variant="ghost"
                      size="sm"
                      leftIcon={<Copy className="h-4 w-4" />}
                      onClick={() => void copyLink()}
                    >
                      Copiar enlace
                    </Button>
                  )}
                  {study.shared_at && (
                    <Button variant="ghost" size="sm" onClick={() => void revoke()}>
                      Anular enlace
                    </Button>
                  )}
                </div>

                {shareLink && (
                  <div className="rounded-xl border border-border bg-background/70 px-4 py-3">
                    <p className="break-all text-sm text-foreground">{shareLink.url}</p>
                    <p className="mt-1 text-xs text-muted">
                      Vigente hasta {formatDateTime(shareLink.expires_at)}
                    </p>
                  </div>
                )}

                {!shareLink && study.shared_at && (
                  <p className="text-xs text-muted">
                    Se compartió por última vez el {formatDateTime(study.shared_at)}. Genere un
                    enlace nuevo para volver a enviarlo.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  )
}
