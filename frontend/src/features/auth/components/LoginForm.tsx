import { useState, type FormEvent } from 'react'
import { ArrowRight, Lock, User } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

import { Alert, Button, Input, PasswordInput } from '@/components/ui'
import { useLogin } from '@/features/auth/hooks/useAuth'
import { ROUTES } from '@/routes/paths'

interface FieldErrors {
  username?: string
  password?: string
}

export function LoginForm() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const { login, isLoading, error, reset } = useLogin()

  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? ROUTES.dashboard

  const validate = (): boolean => {
    const errors: FieldErrors = {}
    if (!username.trim()) errors.username = 'Ingrese su usuario o correo'
    else if (username.trim().length < 3) errors.username = 'Debe tener al menos 3 caracteres'
    if (!password) errors.password = 'Ingrese su contraseña'
    else if (password.length < 4) errors.password = 'Debe tener al menos 4 caracteres'
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return
    if (!validate()) return
    try {
      await login({ username: username.trim(), password })
      navigate(from, { replace: true })
    } catch {
      /* el error se muestra desde el estado de la mutación */
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {error && <Alert variant="danger">{error}</Alert>}

      <Input
        label="Usuario o correo"
        placeholder="Ingrese su usuario"
        autoComplete="username"
        autoFocus
        icon={<User className="h-[18px] w-[18px]" />}
        value={username}
        error={fieldErrors.username}
        disabled={isLoading}
        onChange={(event) => {
          setUsername(event.target.value)
          if (fieldErrors.username) setFieldErrors((prev) => ({ ...prev, username: undefined }))
          if (error) reset()
        }}
      />

      <PasswordInput
        label="Contraseña"
        placeholder="Ingrese su contraseña"
        autoComplete="current-password"
        icon={<Lock className="h-[18px] w-[18px]" />}
        value={password}
        error={fieldErrors.password}
        disabled={isLoading}
        onChange={(event) => {
          setPassword(event.target.value)
          if (fieldErrors.password) setFieldErrors((prev) => ({ ...prev, password: undefined }))
          if (error) reset()
        }}
      />

      <Button
        type="submit"
        size="lg"
        fullWidth
        isLoading={isLoading}
        rightIcon={<ArrowRight className="h-4 w-4" />}
      >
        {isLoading ? 'Verificando…' : 'Iniciar sesión'}
      </Button>
    </form>
  )
}
