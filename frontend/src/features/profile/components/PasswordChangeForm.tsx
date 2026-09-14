import { useState, type ChangeEvent, type FormEvent } from 'react'
import { KeyRound, Lock, ShieldCheck } from 'lucide-react'

import {
  Alert,
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  PasswordInput,
} from '@/components/ui'
import { useChangePassword } from '@/features/profile/hooks/useProfile'

interface FormValues {
  current: string
  next: string
  confirm: string
}

type FieldErrors = Partial<Record<keyof FormValues, string>>

const EMPTY: FormValues = { current: '', next: '', confirm: '' }

function validate(values: FormValues): FieldErrors {
  const errors: FieldErrors = {}
  if (!values.current) errors.current = 'Ingrese su contraseña actual'

  if (values.next.length < 8) errors.next = 'Mínimo 8 caracteres'
  else if (!/[a-zA-Z]/.test(values.next)) errors.next = 'Debe incluir al menos una letra'
  else if (!/\d/.test(values.next)) errors.next = 'Debe incluir al menos un número'
  else if (values.next === values.current)
    errors.next = 'La nueva contraseña debe ser distinta a la actual'

  if (!values.confirm) errors.confirm = 'Repita la nueva contraseña'
  else if (values.confirm !== values.next) errors.confirm = 'Las contraseñas no coinciden'

  return errors
}

export function PasswordChangeForm() {
  const [values, setValues] = useState<FormValues>(EMPTY)
  const [errors, setErrors] = useState<FieldErrors>({})
  const { changePassword, isLoading, isSuccess, error, reset } = useChangePassword()

  const handleChange = (field: keyof FormValues) => (event: ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target
    setValues((prev) => ({ ...prev, [field]: value }))
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }))
    if (isSuccess || error) reset()
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    const nextErrors = validate(values)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    try {
      await changePassword({ current_password: values.current, new_password: values.next })
      setValues(EMPTY)
    } catch {
      /* el error se muestra desde el estado de la mutación */
    }
  }

  return (
    <Card>
      <CardHeader
        title="Seguridad"
        description="Cambia tu contraseña de acceso al sistema"
        action={
          <span className="hidden h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary sm:flex">
            <ShieldCheck className="h-[18px] w-[18px]" />
          </span>
        }
      />
      <form onSubmit={handleSubmit} noValidate>
        <CardBody className="space-y-4">
          {error && <Alert variant="danger">{error}</Alert>}
          {isSuccess && <Alert variant="success">Contraseña actualizada correctamente</Alert>}

          <PasswordInput
            label="Contraseña actual"
            placeholder="Ingrese su contraseña actual"
            icon={<Lock className="h-[18px] w-[18px]" />}
            autoComplete="current-password"
            value={values.current}
            error={errors.current}
            disabled={isLoading}
            onChange={handleChange('current')}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <PasswordInput
              label="Nueva contraseña"
              placeholder="Mínimo 8 caracteres"
              icon={<KeyRound className="h-[18px] w-[18px]" />}
              hint="Debe incluir letras y números"
              autoComplete="new-password"
              value={values.next}
              error={errors.next}
              disabled={isLoading}
              onChange={handleChange('next')}
            />
            <PasswordInput
              label="Confirmar contraseña"
              placeholder="Repita la nueva contraseña"
              icon={<KeyRound className="h-[18px] w-[18px]" />}
              autoComplete="new-password"
              value={values.confirm}
              error={errors.confirm}
              disabled={isLoading}
              onChange={handleChange('confirm')}
            />
          </div>
        </CardBody>

        <CardFooter className="flex justify-end">
          <Button type="submit" size="sm" isLoading={isLoading} leftIcon={<KeyRound className="h-4 w-4" />}>
            Actualizar contraseña
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}
