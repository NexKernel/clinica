import { HeartPulse, ShieldCheck, Stethoscope } from 'lucide-react'

import { BrandMark } from '@/components/common/BrandMark'
import { Card } from '@/components/ui'
import { LoginForm } from '@/features/auth/components/LoginForm'
import { useClinicIdentity } from '@/features/settings/hooks/useClinicIdentity'

const HIGHLIGHTS = [
  { icon: Stethoscope, text: 'Atención clínica organizada en un solo lugar' },
  { icon: HeartPulse, text: 'Historia del paciente siempre disponible' },
  { icon: ShieldCheck, text: 'Acceso seguro por perfil de usuario' },
]

export function LoginPage() {
  const clinic = useClinicIdentity()

  return (
    <div className="grid min-h-screen bg-background lg:grid-cols-[1.05fr_1fr]">
      {/* Panel institucional */}
      <section className="relative hidden overflow-hidden bg-primary px-12 py-14 text-white lg:flex lg:flex-col lg:justify-between">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-white/10"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-32 -left-20 h-96 w-96 rounded-full bg-white/10"
        />

        <div className="relative flex items-center gap-3">
          <BrandMark className="h-11 w-11 bg-white/15" src={clinic.logoUrl} alt={clinic.name} />
          <div>
            <p className="text-sm font-bold tracking-[0.18em]">{clinic.shortName}</p>
            <p className="text-xs text-white/75">{clinic.location}</p>
          </div>
        </div>

        <div className="relative max-w-md">
          <h1 className="text-3xl font-semibold leading-tight text-white">
            Sistema de gestión clínica
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-white/85">{clinic.tagline}</p>

          <ul className="mt-9 space-y-4">
            {HIGHLIGHTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-sm text-white/90">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white/15">
                  <Icon className="h-[18px] w-[18px]" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/70">
          {clinic.name} · Uso exclusivo del personal autorizado
        </p>
      </section>

      {/* Formulario */}
      <section className="flex items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-md">
          <div className="mb-7 flex flex-col items-center text-center lg:hidden">
            <BrandMark
              className="h-12 w-12"
              iconClassName="h-6 w-6"
              src={clinic.logoUrl}
              alt={clinic.name}
            />
            <p className="mt-3 text-sm font-bold tracking-[0.16em] text-primary-dark">
              {clinic.shortName}
            </p>
            <p className="text-xs text-muted">{clinic.location}</p>
          </div>

          <Card className="p-6 sm:p-8">
            <div className="mb-7">
              <h1 className="text-2xl font-semibold">Bienvenido</h1>
              <p className="mt-1 text-sm text-muted">Ingresa tus credenciales para continuar</p>
            </div>

            <LoginForm />
          </Card>

          <p className="mt-6 text-center text-xs text-muted">
            ¿Problemas para ingresar? Comuníquese con el administrador del sistema.
          </p>
        </div>
      </section>
    </div>
  )
}
