import { AtSign, CalendarDays, CircleUser, ShieldCheck } from 'lucide-react'

import { Avatar, Badge, Card, CardBody, FullScreenLoader, PageHeader } from '@/components/ui'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { PasswordChangeForm } from '@/features/profile/components/PasswordChangeForm'
import { ProfileDataForm } from '@/features/profile/components/ProfileDataForm'
import { formatDate } from '@/lib/datetime'

export function ProfilePage() {
  const { user } = useAuth()

  if (!user) return <FullScreenLoader label="Cargando perfil…" />

  const details = [
    { icon: CircleUser, label: 'Usuario', value: user.username },
    { icon: AtSign, label: 'Correo', value: user.email },
    { icon: ShieldCheck, label: 'Perfil', value: user.role_name },
    { icon: CalendarDays, label: 'Registrado', value: formatDate(user.created_at) },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Mi cuenta"
        title="Mi perfil"
        subtitle="Administra tus datos personales y la seguridad de tu acceso"
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="h-fit lg:sticky lg:top-20">
          <CardBody className="flex flex-col items-center py-6 text-center">
            <Avatar name={user.full_name} size="lg" className="h-16 w-16 text-xl" />
            <h2 className="mt-3 text-base font-semibold text-foreground">{user.full_name}</h2>
            <div className="mt-2 flex items-center gap-2">
              <Badge variant="primary">{user.role_name}</Badge>
              <Badge variant={user.is_active ? 'success' : 'neutral'} dot>
                {user.is_active ? 'Activo' : 'Inactivo'}
              </Badge>
            </div>
          </CardBody>

          <div className="border-t border-border">
            <dl className="divide-y divide-border">
              {details.map(({ icon: Icon, label, value }) => (
                <div key={label} className="flex items-center gap-3 px-5 py-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0">
                    <dt className="caption">{label}</dt>
                    <dd className="truncate text-sm font-medium text-foreground">{value}</dd>
                  </div>
                </div>
              ))}
            </dl>
          </div>
        </Card>

        <div className="space-y-4 lg:col-span-2">
          <ProfileDataForm user={user} />
          <PasswordChangeForm />
        </div>
      </div>
    </div>
  )
}
