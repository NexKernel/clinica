import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { AtSign, IdCard, Save, UserRound } from 'lucide-react'

import { Alert, Button, Card, CardBody, CardFooter, CardHeader, Input } from '@/components/ui'
import { useUpdateProfile } from '@/features/profile/hooks/useProfile'
import type { ProfileUpdatePayload, User } from '@/types'

type Field = keyof ProfileUpdatePayload
type FieldErrors = Partial<Record<Field, string>>

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
const USERNAME_PATTERN = /^[a-zA-Z0-9._-]+$/

function toFormValues(user: User): ProfileUpdatePayload {
  return { full_name: user.full_name, email: user.email, username: user.username }
}

function validate(values: ProfileUpdatePayload): FieldErrors {
  const errors: FieldErrors = {}
  if (values.full_name.trim().length < 3) errors.full_name = 'Ingrese el nombre completo'
  if (!EMAIL_PATTERN.test(values.email.trim())) errors.email = 'Ingrese un correo válido'
  if (values.username.trim().length < 3) errors.username = 'Mínimo 3 caracteres'
  else if (!USERNAME_PATTERN.test(values.username.trim()))
    errors.username = 'Solo letras, números y . _ -'
  return errors
}

interface ProfileDataFormProps {
  user: User
}

export function ProfileDataForm({ user }: ProfileDataFormProps) {
  const [values, setValues] = useState<ProfileUpdatePayload>(() => toFormValues(user))
  const [errors, setErrors] = useState<FieldErrors>({})
  const { updateProfile, isLoading, isSuccess, error, reset } = useUpdateProfile()

  useEffect(() => {
    setValues(toFormValues(user))
  }, [user])

  const initial = toFormValues(user)
  const isDirty = (Object.keys(initial) as Field[]).some(
    (field) => values[field].trim() !== initial[field],
  )

  const handleChange = (field: Field) => (event: ChangeEvent<HTMLInputElement>) => {
    setValues((prev) => ({ ...prev, [field]: event.target.value }))
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
      await updateProfile({
        full_name: values.full_name.trim(),
        email: values.email.trim(),
        username: values.username.trim(),
      })
    } catch {
      /* el error se muestra desde el estado de la mutación */
    }
  }

  return (
    <Card>
      <CardHeader
        title="Datos de la cuenta"
        description="Actualiza tu información personal y credenciales de acceso"
      />
      <form onSubmit={handleSubmit} noValidate>
        <CardBody className="space-y-4">
          {error && <Alert variant="danger">{error}</Alert>}
          {isSuccess && !isDirty && <Alert variant="success">Perfil actualizado correctamente</Alert>}

          <Input
            label="Nombre completo"
            placeholder="Ingrese nombre y apellidos"
            icon={<UserRound className="h-[18px] w-[18px]" />}
            value={values.full_name}
            error={errors.full_name}
            disabled={isLoading}
            autoComplete="name"
            onChange={handleChange('full_name')}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Correo electrónico"
              type="email"
              placeholder="usuario@estabridis.pe"
              icon={<AtSign className="h-[18px] w-[18px]" />}
              value={values.email}
              error={errors.email}
              disabled={isLoading}
              autoComplete="email"
              onChange={handleChange('email')}
            />
            <Input
              label="Usuario"
              placeholder="usuario"
              icon={<IdCard className="h-[18px] w-[18px]" />}
              hint="Con este nombre inicias sesión"
              value={values.username}
              error={errors.username}
              disabled={isLoading}
              autoComplete="username"
              onChange={handleChange('username')}
            />
          </div>
        </CardBody>

        <CardFooter className="flex justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            disabled={!isDirty || isLoading}
            onClick={() => {
              setValues(toFormValues(user))
              setErrors({})
              reset()
            }}
          >
            Descartar
          </Button>
          <Button
            type="submit"
            size="sm"
            isLoading={isLoading}
            disabled={!isDirty}
            leftIcon={<Save className="h-4 w-4" />}
          >
            Guardar cambios
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}
