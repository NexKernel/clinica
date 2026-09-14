import { useEffect, useState, type ReactNode } from 'react'

import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Textarea } from '@/components/ui/Textarea'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description?: string
  /** Solicita un motivo obligatorio antes de confirmar (anulaciones). */
  reasonLabel?: string
  confirmLabel?: string
  variant?: 'primary' | 'danger'
  isLoading?: boolean
  error?: string | null
  children?: ReactNode
  onClose: () => void
  onConfirm: (reason: string) => void
}

export function ConfirmDialog({
  open,
  title,
  description,
  reasonLabel,
  confirmLabel = 'Confirmar',
  variant = 'primary',
  isLoading = false,
  error,
  children,
  onClose,
  onConfirm,
}: ConfirmDialogProps) {
  const [reason, setReason] = useState('')
  const [touched, setTouched] = useState(false)

  useEffect(() => {
    if (open) {
      setReason('')
      setTouched(false)
    }
  }, [open])

  const missingReason = Boolean(reasonLabel) && reason.trim().length < 3

  const handleConfirm = () => {
    setTouched(true)
    if (missingReason) return
    onConfirm(reason.trim())
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      size="sm"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            Cancelar
          </Button>
          <Button size="sm" variant={variant} isLoading={isLoading} onClick={handleConfirm}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <Alert variant="danger">{error}</Alert>}
        {children}
        {reasonLabel && (
          <Textarea
            label={reasonLabel}
            value={reason}
            disabled={isLoading}
            error={touched && missingReason ? 'Indique el motivo (mínimo 3 caracteres)' : null}
            onChange={(event) => setReason(event.target.value)}
          />
        )}
      </div>
    </Modal>
  )
}
