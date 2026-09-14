import { useRef, useState, type ChangeEvent } from 'react'
import { ImageUp, Trash2 } from 'lucide-react'

import { Alert, Button, Card, CardBody, CardHeader, Modal } from '@/components/ui'
import { BrandMark } from '@/components/common/BrandMark'
import { useDeleteLogo, useUploadLogo } from '@/features/settings/hooks/useSettings'
import { resolveMediaUrl } from '@/services/http'

const ACCEPTED = ['image/png', 'image/jpeg', 'image/webp']
const MAX_BYTES = 2 * 1024 * 1024

interface LogoUploaderProps {
  logoUrl: string | null
  name: string
}

export function LogoUploader({ logoUrl, name }: LogoUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [localError, setLocalError] = useState<string | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const upload = useUploadLogo()
  const remove = useDeleteLogo()

  const src = resolveMediaUrl(logoUrl)
  const isBusy = upload.isLoading || remove.isLoading
  const error = localError ?? upload.error ?? remove.error

  const handleFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    setLocalError(null)
    upload.reset()
    remove.reset()

    if (!ACCEPTED.includes(file.type)) {
      setLocalError('Formato no permitido. Use PNG, JPG o WEBP')
      return
    }
    if (file.size > MAX_BYTES) {
      setLocalError('El logo no debe superar 2 MB')
      return
    }

    try {
      await upload.mutate(file)
    } catch {
      /* el error se muestra desde el estado de la mutación */
    }
  }

  const handleRemove = async () => {
    setConfirmOpen(false)
    setLocalError(null)
    try {
      await remove.mutate(undefined)
    } catch {
      /* el error se muestra desde el estado de la mutación */
    }
  }

  return (
    <Card>
      <CardHeader
        title="Logotipo"
        description="Se muestra en el inicio de sesión, el menú y los documentos impresos"
      />
      <CardBody className="space-y-4">
        {error && <Alert variant="danger">{error}</Alert>}

        <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center">
          <div className="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-border bg-background">
            {src ? (
              <img src={src} alt={`Logo de ${name}`} className="h-full w-full object-contain p-2" />
            ) : (
              <BrandMark className="h-12 w-12" iconClassName="h-6 w-6" />
            )}
          </div>

          <div className="flex-1 text-center sm:text-left">
            <p className="text-sm text-muted">
              Formatos PNG, JPG o WEBP · hasta 2 MB. Se recomienda una imagen cuadrada con fondo
              transparente.
            </p>
            <div className="mt-3 flex flex-wrap justify-center gap-2 sm:justify-start">
              <Button
                size="sm"
                variant="outline"
                isLoading={upload.isLoading}
                disabled={isBusy}
                leftIcon={<ImageUp className="h-4 w-4" />}
                onClick={() => inputRef.current?.click()}
              >
                {src ? 'Cambiar logo' : 'Subir logo'}
              </Button>
              {src && (
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={isBusy}
                  leftIcon={<Trash2 className="h-4 w-4" />}
                  onClick={() => setConfirmOpen(true)}
                >
                  Quitar
                </Button>
              )}
            </div>
          </div>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(',')}
          className="hidden"
          onChange={handleFile}
        />
      </CardBody>

      <Modal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Quitar logotipo"
        description="El sistema volverá a mostrar el isotipo por defecto."
        size="sm"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setConfirmOpen(false)}>
              Cancelar
            </Button>
            <Button variant="danger" size="sm" isLoading={remove.isLoading} onClick={handleRemove}>
              Quitar logo
            </Button>
          </>
        }
      >
        <p className="text-sm text-muted">
          ¿Confirma que desea eliminar el logotipo actual del establecimiento?
        </p>
      </Modal>
    </Card>
  )
}
