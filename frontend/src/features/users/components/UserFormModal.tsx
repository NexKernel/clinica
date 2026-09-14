import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { AtSign, IdCard, KeyRound, Save, UserRound } from 'lucide-react'

import {
  Alert,
  Button,
  Input,
  Modal,
  PasswordInput,
  Select,
  Switch,
  type SelectOption,
} from '@/components/ui'
import { useUserActions } from '@/features/users/hooks/useUsers'
import { getErrorMessage } from '@/services/http'
import type { RoleOption, User } from '@/types'

interface FormValues {
  full_name: string
  username: string
  email: string
  role: string
  password: string
  is_active: boolean
}

type FieldErrors = Partial<Record<keyof FormValues, string>>

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
const USERNAME_PATTERN = /^[a-zA-Z0-9._-]+$/

const emptyValues = (defaultRole: string): FormValues => ({
  full_name: '',
  username: '',
  email: '',
  role: defaultRole,
  password: '',
  is_active: true,
})

function validate(values: FormValues, isEdit: boolean): FieldErrors {
  const errors: FieldErrors = {}

  if (values.full_name.trim().length < 3) errors.full_name = 'Ingrese el nombre completo'

  if (values.username.trim().length < 3) errors.username = 'Mínimo 3 caracteres'
  else if (!USERNAME_PATTERN.test(values.username.trim()))
    errors.username = 'Solo letras, números y . _ -'

  if (!EMAIL_PATTERN.test(values.email.trim())) errors.email = 'Ingrese un correo válido'
  if (!values.role) errors.role = 'Seleccione un perfil'

  if (!isEdit) {
    if (values.password.length < 8) errors.password = 'Mínimo 8 caracteres'
    else if (!/[a-zA-Z]/.test(values.password)) errors.password = 'Debe incluir al menos una letra'
    else if (!/\d/.test(values.password)) errors.password = 'Debe incluir al menos un número'
  }

  return errors
}

interface UserFormModalProps {
  open: boolean
  onClose: () => void
  user: User | null
  roles: RoleOption[]
  isSelf: boolean
}

export function UserFormModal({ open, onClose, user, roles, isSelf }: UserFormModalProps) {
  const isEdit = user !== null
  const defaultRole = roles[0]?.code ?? ''
  const [values, setValues] = useState<FormValues>(() => emptyValues(defaultRole))
  const [errors, setErrors] = useState<FieldErrors>({})
  const [serverError, setServerError] = useState<string | null>(null)

  const { create, update } = useUserActions()
  const isLoading = create.isPending || update.isPending

  useEffect(() => {
    if (!open) return
    setErrors({})
    setServerError(null)
    setValues(
      user
        ? {
            full_name: user.full_name,
            username: user.username,
            email: user.email,
            role: user.role,
            password: '',
            is_active: user.is_active,
          }
        : emptyValues(defaultRole),
    )
  }, [open, user, defaultRole])

  const roleOptions: SelectOption[] = roles.map((role) => ({
    value: role.code,
    label: role.name,
  }))

  const handleChange =
    (field: keyof FormValues) => (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const { value } = event.target
      setValues((prev) => ({ ...prev, [field]: value }))
      if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }))
      if (serverError) setServerError(null)
    }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    const nextErrors = validate(values, isEdit)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    const base = {
      full_name: values.full_name.trim(),
      username: values.username.trim().toLowerCase(),
      email: values.email.trim().toLowerCase(),
      role: values.role,
      is_active: values.is_active,
    }

    try {
      if (user) {
        await update.mutateAsync({ id: user.id, payload: base })
      } else {
        await create.mutateAsync({ ...base, password: values.password })
      }
      onClose()
    } catch (error) {
      setServerError(getErrorMessage(error, 'No se pudo guardar el usuario'))
    }
  }

  const selectedRole = roles.find((role) => role.code === values.role)

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Editar usuario' : 'Nuevo usuario'}
      description={
        isEdit ? 'Actualice los datos y el perfil de acceso' : 'Registre un nuevo usuario del sistema'
      }
      size="md"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="user-form"
            size="sm"
            isLoading={isLoading}
            leftIcon={<Save className="h-4 w-4" />}
          >
            {isEdit ? 'Guardar cambios' : 'Crear usuario'}
          </Button>
        </>
      }
    >
      <form id="user-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {serverError && <Alert variant="danger">{serverError}</Alert>}

        <Input
          label="Nombre completo"
          placeholder="Nombres y apellidos"
          icon={<UserRound className="h-[18px] w-[18px]" />}
          value={values.full_name}
          error={errors.full_name}
          disabled={isLoading}
          onChange={handleChange('full_name')}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Usuario"
            placeholder="c.paredes"
            icon={<IdCard className="h-[18px] w-[18px]" />}
            value={values.username}
            error={errors.username}
            disabled={isLoading}
            onChange={handleChange('username')}
          />
          <Input
            label="Correo"
            type="email"
            placeholder="usuario@estabridis.pe"
            icon={<AtSign className="h-[18px] w-[18px]" />}
            value={values.email}
            error={errors.email}
            disabled={isLoading}
            onChange={handleChange('email')}
          />
        </div>

        <div>
          <Select
            label="Perfil de acceso"
            options={roleOptions}
            value={values.role}
            error={errors.role}
            disabled={isLoading || isSelf}
            onChange={handleChange('role')}
          />
          {selectedRole?.description && (
            <p className="mt-1.5 text-xs text-muted">{selectedRole.description}</p>
          )}
          {isSelf && (
            <p className="mt-1.5 text-xs text-muted">
              No puede cambiar su propio perfil de acceso.
            </p>
          )}
        </div>

        {!isEdit && (
          <PasswordInput
            label="Contraseña inicial"
            placeholder="Mínimo 8 caracteres"
            icon={<KeyRound className="h-[18px] w-[18px]" />}
            hint="Debe incluir letras y números"
            autoComplete="new-password"
            value={values.password}
            error={errors.password}
            disabled={isLoading}
            onChange={handleChange('password')}
          />
        )}

        <Switch
          label="Usuario activo"
          description="Los usuarios inactivos no pueden iniciar sesión"
          checked={values.is_active}
          disabled={isLoading || isSelf}
          onChange={(checked) => setValues((prev) => ({ ...prev, is_active: checked }))}
        />
      </form>
    </Modal>
  )
}
