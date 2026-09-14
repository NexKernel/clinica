import { useEffect, useState, type FormEvent } from 'react'
import { KeyRound } from 'lucide-react'

import { Alert, Button, Modal, PasswordInput } from '@/components/ui'
import { useUserActions } from '@/features/users/hooks/useUsers'
import { getErrorMessage } from '@/services/http'
import type { User } from '@/types'

interface ResetPasswordModalProps {
  open: boolean
  onClose: () => void
  user: User | null
}

export function ResetPasswordModal({ open, onClose, user }: ResetPasswordModalProps) {
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<{ password?: string; confirm?: string }>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  const { resetPassword } = useUserActions()

  useEffect(() => {
    if (!open) return
    setPassword('')
    setConfirm('')
    setErrors({})
    setServerError(null)
    setDone(false)
  }, [open])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!user || resetPassword.isPending) return

    const nextErrors: typeof errors = {}
    if (password.length < 8) nextErrors.password = 'Mínimo 8 caracteres'
    else if (!/[a-zA-Z]/.test(password)) nextErrors.password = 'Debe incluir al menos una letra'
    else if (!/\d/.test(password)) nextErrors.password = 'Debe incluir al menos un número'
    if (confirm !== password) nextErrors.confirm = 'Las contraseñas no coinciden'

    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    try {
      await resetPassword.mutateAsync({ id: user.id, password })
      setDone(true)
    } catch (error) {
      setServerError(getErrorMessage(error, 'No se pudo restablecer la contraseña'))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Restablecer contraseña"
      description={user ? `Usuario: ${user.full_name}` : undefined}
      size="sm"
      footer={
        <>
          <Button
            variant="ghost"
            size="sm"
            disabled={resetPassword.isPending}
            onClick={onClose}
          >
            Cancelar
          </Button>
          <Button type="submit" form="reset-password-form" size="sm" isLoading={resetPassword.isPending}>
            Restablecer
          </Button>
        </>
      }
    >
      {done ? (
        <div className="space-y-4">
          <Alert variant="success">
            Contraseña actualizada. Comuníquela al usuario para su primer ingreso.
          </Alert>
          <div className="flex justify-end">
            <Button size="sm" onClick={onClose}>
              Entendido
            </Button>
          </div>
        </div>
      ) : (
        <form id="reset-password-form" onSubmit={handleSubmit} noValidate className="space-y-4">
          {serverError && <Alert variant="danger">{serverError}</Alert>}

          <PasswordInput
            label="Nueva contraseña"
            placeholder="Mínimo 8 caracteres"
            icon={<KeyRound className="h-[18px] w-[18px]" />}
            hint="Debe incluir letras y números"
            autoComplete="new-password"
            value={password}
            error={errors.password}
            disabled={resetPassword.isPending}
            onChange={(event) => {
              setPassword(event.target.value)
              setErrors((prev) => ({ ...prev, password: undefined }))
            }}
          />
          <PasswordInput
            label="Confirmar contraseña"
            placeholder="Repita la contraseña"
            icon={<KeyRound className="h-[18px] w-[18px]" />}
            autoComplete="new-password"
            value={confirm}
            error={errors.confirm}
            disabled={resetPassword.isPending}
            onChange={(event) => {
              setConfirm(event.target.value)
              setErrors((prev) => ({ ...prev, confirm: undefined }))
            }}
          />
        </form>
      )}
    </Modal>
  )
}
