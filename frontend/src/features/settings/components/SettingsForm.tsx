import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { Building2, CalendarClock, MapPin, Receipt, Save } from 'lucide-react'

import {
  Alert,
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  Input,
  Select,
  Tabs,
  type TabItem,
} from '@/components/ui'
import { useUpdateSettings } from '@/features/settings/hooks/useSettings'
import type { ClinicSettings, ClinicSettingsPayload } from '@/types'

type FormValues = Record<keyof ClinicSettingsPayload, string>
type FieldErrors = Partial<Record<keyof FormValues, string>>

const TAB_FIELDS = {
  establecimiento: ['name', 'short_name', 'tagline', 'legal_name', 'tax_id'],
  contacto: [
    'address',
    'district',
    'province',
    'department',
    'phone',
    'whatsapp',
    'email',
    'website',
  ],
  atencion: [
    'opening_hours',
    'appointment_slot_minutes',
    'medical_director',
    'health_facility_code',
    'category',
    'document_footer',
  ],
  facturacion: ['currency', 'tax_rate', 'invoice_series', 'receipt_series'],
} as const satisfies Record<string, readonly (keyof FormValues)[]>

type TabKey = keyof typeof TAB_FIELDS

const TAB_META: { key: TabKey; label: string; icon: TabItem['icon'] }[] = [
  { key: 'establecimiento', label: 'Establecimiento', icon: Building2 },
  { key: 'contacto', label: 'Contacto', icon: MapPin },
  { key: 'atencion', label: 'Atención', icon: CalendarClock },
  { key: 'facturacion', label: 'Facturación', icon: Receipt },
]

const CURRENCIES = [
  { value: 'PEN', label: 'PEN — Soles' },
  { value: 'USD', label: 'USD — Dólares' },
]

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

function toForm(settings: ClinicSettings): FormValues {
  return {
    name: settings.name,
    short_name: settings.short_name,
    tagline: settings.tagline ?? '',
    legal_name: settings.legal_name ?? '',
    tax_id: settings.tax_id ?? '',
    address: settings.address ?? '',
    district: settings.district ?? '',
    province: settings.province ?? '',
    department: settings.department ?? '',
    phone: settings.phone ?? '',
    whatsapp: settings.whatsapp ?? '',
    email: settings.email ?? '',
    website: settings.website ?? '',
    health_facility_code: settings.health_facility_code ?? '',
    medical_director: settings.medical_director ?? '',
    category: settings.category ?? '',
    document_footer: settings.document_footer ?? '',
    opening_hours: settings.opening_hours ?? '',
    appointment_slot_minutes: String(settings.appointment_slot_minutes),
    currency: settings.currency,
    tax_rate: String(settings.tax_rate),
    invoice_series: settings.invoice_series ?? '',
    receipt_series: settings.receipt_series ?? '',
  }
}

const optional = (value: string): string | null => value.trim() || null

function toPayload(values: FormValues): ClinicSettingsPayload {
  return {
    name: values.name.trim(),
    short_name: values.short_name.trim(),
    tagline: optional(values.tagline),
    legal_name: optional(values.legal_name),
    tax_id: optional(values.tax_id),
    address: optional(values.address),
    district: optional(values.district),
    province: optional(values.province),
    department: optional(values.department),
    phone: optional(values.phone),
    whatsapp: optional(values.whatsapp),
    email: optional(values.email),
    website: optional(values.website),
    health_facility_code: optional(values.health_facility_code),
    medical_director: optional(values.medical_director),
    category: optional(values.category),
    document_footer: optional(values.document_footer),
    opening_hours: optional(values.opening_hours),
    appointment_slot_minutes: Number(values.appointment_slot_minutes),
    currency: values.currency,
    tax_rate: Number(values.tax_rate),
    invoice_series: optional(values.invoice_series),
    receipt_series: optional(values.receipt_series),
  }
}

function validate(values: FormValues): FieldErrors {
  const errors: FieldErrors = {}

  if (values.name.trim().length < 3) errors.name = 'Ingrese el nombre del establecimiento'
  if (values.short_name.trim().length < 2) errors.short_name = 'Mínimo 2 caracteres'
  if (values.email.trim() && !EMAIL_PATTERN.test(values.email.trim()))
    errors.email = 'Ingrese un correo válido'
  if (values.tax_id.trim() && !/^\d{8,20}$/.test(values.tax_id.trim()))
    errors.tax_id = 'Sólo números (8 a 20 dígitos)'

  if (values.category.trim().length > 10) errors.category = 'Máximo 10 caracteres'
  if (values.document_footer.trim().length > 255)
    errors.document_footer = 'Máximo 255 caracteres'

  const slot = Number(values.appointment_slot_minutes)
  if (!Number.isInteger(slot) || slot < 5 || slot > 180)
    errors.appointment_slot_minutes = 'Entre 5 y 180 minutos'

  const tax = Number(values.tax_rate)
  if (Number.isNaN(tax) || tax < 0 || tax > 100) errors.tax_rate = 'Entre 0 y 100'

  return errors
}

interface SettingsFormProps {
  settings: ClinicSettings
}

export function SettingsForm({ settings }: SettingsFormProps) {
  const [values, setValues] = useState<FormValues>(() => toForm(settings))
  const [errors, setErrors] = useState<FieldErrors>({})
  const [activeTab, setActiveTab] = useState<TabKey>('establecimiento')
  const { mutate, isLoading, isSuccess, error, reset } = useUpdateSettings()

  useEffect(() => {
    setValues(toForm(settings))
  }, [settings])

  const initial = toForm(settings)
  const isDirty = (Object.keys(initial) as (keyof FormValues)[]).some(
    (field) => values[field] !== initial[field],
  )

  const field = (name: keyof FormValues) => ({
    value: values[name],
    error: errors[name],
    disabled: isLoading,
    onChange: (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const { value } = event.target
      setValues((prev) => ({ ...prev, [name]: value }))
      if (errors[name]) setErrors((prev) => ({ ...prev, [name]: undefined }))
      if (isSuccess || error) reset()
    },
  })

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    const nextErrors = validate(values)
    setErrors(nextErrors)

    const failing = Object.keys(nextErrors) as (keyof FormValues)[]
    if (failing.length > 0) {
      const tabWithError = TAB_META.find((tab) =>
        (TAB_FIELDS[tab.key] as readonly (keyof FormValues)[]).some((name) =>
          failing.includes(name),
        ),
      )
      if (tabWithError) setActiveTab(tabWithError.key)
      return
    }

    try {
      await mutate(toPayload(values))
    } catch {
      /* el error se muestra desde el estado de la mutación */
    }
  }

  const tabs: TabItem[] = TAB_META.map((tab) => ({
    ...tab,
    hasError: (TAB_FIELDS[tab.key] as readonly (keyof FormValues)[]).some((name) =>
      Boolean(errors[name]),
    ),
  }))

  return (
    <Card>
      <CardHeader
        title="Datos del establecimiento"
        description="Información institucional utilizada por todo el sistema"
      />

      <form onSubmit={handleSubmit} noValidate>
        <CardBody className="space-y-5">
          <Tabs items={tabs} active={activeTab} onChange={(key) => setActiveTab(key as TabKey)} />

          {error && <Alert variant="danger">{error}</Alert>}
          {isSuccess && !isDirty && <Alert variant="success">Configuración guardada</Alert>}

          {activeTab === 'establecimiento' && (
            <div className="space-y-4">
              <Input label="Nombre del establecimiento" placeholder="Policlínico Estabridis" {...field('name')} />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Nombre corto"
                  hint="Se muestra en el menú lateral"
                  placeholder="ESTABRIDIS"
                  {...field('short_name')}
                />
                <Input label="Lema institucional" placeholder="Atención médica integral" {...field('tagline')} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Razón social" placeholder="Razón social registrada" {...field('legal_name')} />
                <Input label="RUC" placeholder="20601234567" inputMode="numeric" {...field('tax_id')} />
              </div>
            </div>
          )}

          {activeTab === 'contacto' && (
            <div className="space-y-4">
              <Input label="Dirección" placeholder="Jr. Colonos Fundadores 123" {...field('address')} />
              <div className="grid gap-4 sm:grid-cols-3">
                <Input label="Distrito" placeholder="Satipo" {...field('district')} />
                <Input label="Provincia" placeholder="Satipo" {...field('province')} />
                <Input label="Departamento" placeholder="Junín" {...field('department')} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Teléfono" placeholder="064 545123" {...field('phone')} />
                <Input label="WhatsApp" placeholder="964 555 111" {...field('whatsapp')} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Correo" type="email" placeholder="contacto@estabridis.pe" {...field('email')} />
                <Input label="Sitio web" placeholder="www.estabridis.pe" {...field('website')} />
              </div>
            </div>
          )}

          {activeTab === 'atencion' && (
            <div className="space-y-4">
              <Input
                label="Horario de atención"
                placeholder="Lunes a sábado, 8:00 a 20:00"
                {...field('opening_hours')}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Duración de cita (minutos)"
                  type="number"
                  min={5}
                  max={180}
                  hint="Usado por el módulo de citas"
                  {...field('appointment_slot_minutes')}
                />
                <Input
                  label="Código del establecimiento"
                  hint="Código RENIPRESS / RENAES"
                  placeholder="00012345"
                  {...field('health_facility_code')}
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Director médico" placeholder="Dr. Luis Estabridis" {...field('medical_director')} />
                <Input
                  label="Categoría"
                  hint="Categoría MINSA del establecimiento"
                  placeholder="I-3"
                  {...field('category')}
                />
              </div>
              <Input
                label="Pie de los documentos impresos"
                hint="Se imprime al final de informes, fichas y consentimientos"
                placeholder="Policlínico Estabridis S.A.C. · RUC 20601234567 · Satipo, Junín"
                {...field('document_footer')}
              />
            </div>
          )}

          {activeTab === 'facturacion' && (
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Select label="Moneda" options={CURRENCIES} {...field('currency')} />
                <Input
                  label="IGV (%)"
                  type="number"
                  min={0}
                  max={100}
                  step="0.01"
                  {...field('tax_rate')}
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Serie de factura" placeholder="F001" {...field('invoice_series')} />
                <Input label="Serie de boleta" placeholder="B001" {...field('receipt_series')} />
              </div>
              <p className="text-xs text-muted">
                Estos valores serán utilizados por los módulos de caja y facturación.
              </p>
            </div>
          )}
        </CardBody>

        <CardFooter className="flex justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            disabled={!isDirty || isLoading}
            onClick={() => {
              setValues(toForm(settings))
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
