import { useEffect, useRef, useState } from 'react'
import { Printer } from 'lucide-react'

import { Alert, Button, LoadingState, Modal } from '@/components/ui'
import { useCredSheet } from '@/features/cred/hooks/useCred'

/* Mismo tratamiento que la hoja de un documento: el carné va dentro de un
   iframe aislado para que su CSS —con la regla @page del A4— no toque la
   aplicación, y al imprimir salga solo el carné y no el menú de detrás. */
function sheetSource(title: string, html: string): string {
  return `<!doctype html><html lang="es"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${title}</title>
<style>html,body{margin:0;background:#fff}</style>
</head><body>${html}</body></html>`
}

interface CredSheetModalProps {
  open: boolean
  patientId: number | null
  onClose: () => void
}

export function CredSheetModal({ open, patientId, onClose }: CredSheetModalProps) {
  const { sheet, isLoading, error } = useCredSheet(open ? patientId : null)
  const frame = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(600)

  useEffect(() => {
    setHeight(600)
  }, [sheet?.html])

  const fitToContent = () => {
    const body = frame.current?.contentDocument?.body
    if (body) setHeight(Math.max(400, body.scrollHeight + 24))
  }

  const print = () => {
    const view = frame.current?.contentWindow
    if (!view) return
    view.focus()
    view.print()
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={sheet ? sheet.title : 'Carné de atención integral'}
      description={sheet ? sheet.number : undefined}
      size="xl"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cerrar
          </Button>
          <Button
            size="sm"
            leftIcon={<Printer className="h-4 w-4" />}
            disabled={!sheet}
            onClick={print}
          >
            Imprimir
          </Button>
        </>
      }
    >
      {isLoading && <LoadingState label="Armando el carné" />}
      {error && <Alert variant="danger">{error}</Alert>}
      {sheet && (
        <iframe
          ref={frame}
          title={sheet.title}
          srcDoc={sheetSource(sheet.title, sheet.html)}
          onLoad={fitToContent}
          className="w-full rounded-lg border border-border bg-white"
          style={{ height }}
        />
      )}
    </Modal>
  )
}
