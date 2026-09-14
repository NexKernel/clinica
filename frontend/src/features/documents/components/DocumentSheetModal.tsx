import { useEffect, useRef, useState } from 'react'
import { Printer } from 'lucide-react'

import { Alert, Badge, Button, LoadingState, Modal } from '@/components/ui'
import { useDocumentSheet } from '@/features/documents/hooks/useDocuments'

/* La hoja se muestra dentro de un iframe aislado: el CSS del documento (que
   incluye la regla @page del A4) no toca la aplicación, y al imprimir sale
   sólo el documento, sin el menú ni la tabla que quedan detrás. */
function sheetSource(title: string, html: string): string {
  return `<!doctype html><html lang="es"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${title}</title>
<style>html,body{margin:0;background:#fff}</style>
</head><body>${html}</body></html>`
}

interface DocumentSheetModalProps {
  open: boolean
  documentId: number | null
  onClose: () => void
}

export function DocumentSheetModal({ open, documentId, onClose }: DocumentSheetModalProps) {
  const { sheet, isLoading, error } = useDocumentSheet(open ? documentId : null)
  const frame = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(600)

  // El alto se ajusta al contenido para que el modal, y no el iframe, sea lo
  // que se desplace: dos barras de scroll anidadas son incómodas de leer.
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
      title={sheet ? sheet.title : 'Documento'}
      description={sheet ? sheet.number : undefined}
      size="xl"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cerrar
          </Button>
          <Button
            size="sm"
            disabled={!sheet}
            leftIcon={<Printer className="h-4 w-4" />}
            onClick={print}
          >
            Imprimir
          </Button>
        </>
      }
    >
      {isLoading && <LoadingState label="Generando la hoja" />}
      {error && <Alert variant="danger">{error}</Alert>}

      {sheet && (
        <div className="space-y-3">
          {!sheet.is_issued && (
            <Alert variant="info">
              Vista previa de un borrador. El documento aún no está emitido y su contenido puede
              cambiar; emítalo para que valga como constancia.
            </Alert>
          )}
          {sheet.status === 'ANULADO' && (
            <Badge variant="danger" dot>
              Documento anulado
            </Badge>
          )}

          <div className="overflow-x-auto rounded-xl border border-border bg-white">
            <iframe
              ref={frame}
              title={`${sheet.title} · ${sheet.number}`}
              srcDoc={sheetSource(`${sheet.title} · ${sheet.number}`, sheet.html)}
              onLoad={fitToContent}
              className="block w-full border-0"
              style={{ height }}
            />
          </div>
        </div>
      )}
    </Modal>
  )
}
