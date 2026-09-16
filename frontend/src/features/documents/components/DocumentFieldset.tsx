import { Input, Select, Switch, Textarea, type SelectOption } from '@/components/ui'
import type { DocumentData, TemplateField } from '@/types'
import { Odontogram, parseOdontograma } from './Odontogram'

/** El formulario trabaja siempre con texto; la conversión ocurre al guardar. */
export type FieldValues = Record<string, string>

const asText = (value: unknown): string => {
  if (value === null || value === undefined) return ''
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return String(value)
}

const asNumber = (value: string): number => {
  const parsed = Number.parseFloat(value.replace(',', '.'))
  return Number.isFinite(parsed) ? parsed : 0
}

/** Puntaje de un campo `computed`: la suma de las claves que declara. */
export function computedValue(field: TemplateField, values: FieldValues): number {
  return (field.sum ?? []).reduce((total, key) => total + asNumber(values[key] ?? ''), 0)
}

/** Estado inicial del formulario: lo guardado y, si falta, el valor sugerido. */
export function toFieldValues(fields: TemplateField[], data: DocumentData): FieldValues {
  return Object.fromEntries(
    fields.map((field) => {
      const raw = data[field.key] ?? field.default
      if (field.type === 'odontograma') {
        return [field.key, raw && typeof raw === 'object' ? JSON.stringify(raw) : '']
      }
      return [field.key, asText(raw)]
    }),
  )
}

/** Datos a enviar. Un campo vacío viaja como nulo: se imprime en blanco. */
export function toDocumentData(fields: TemplateField[], values: FieldValues): DocumentData {
  const data: DocumentData = {}

  for (const field of fields) {
    const raw = (values[field.key] ?? '').trim()

    if (field.type === 'computed') {
      data[field.key] = computedValue(field, values)
    } else if (field.type === 'odontograma') {
      const marcas = parseOdontograma(raw)
      data[field.key] = Object.keys(marcas).length ? marcas : null
    } else if (field.type === 'boolean') {
      data[field.key] = raw === 'true'
    } else if (field.type === 'number') {
      data[field.key] = raw ? asNumber(raw) : null
    } else {
      data[field.key] = raw || null
    }
  }

  return data
}

/** Campos obligatorios sin completar, en el orden en que aparecen. */
export function missingRequired(fields: TemplateField[], values: FieldValues): TemplateField[] {
  return fields.filter(
    (field) =>
      field.required && field.type !== 'computed' && !(values[field.key] ?? '').trim(),
  )
}

/** Agrupa los campos respetando el orden de la plantilla. */
function byGroup(fields: TemplateField[]): [string, TemplateField[]][] {
  const groups = new Map<string, TemplateField[]>()
  for (const field of fields) {
    const name = field.group ?? ''
    const current = groups.get(name)
    if (current) current.push(field)
    else groups.set(name, [field])
  }
  return [...groups.entries()]
}

interface DocumentFieldsetProps {
  fields: TemplateField[]
  values: FieldValues
  disabled?: boolean
  /** Claves resaltadas por estar obligatoriamente vacías al intentar emitir. */
  invalidKeys?: string[]
  onChange: (key: string, value: string) => void
}

export function DocumentFieldset({
  fields,
  values,
  disabled = false,
  invalidKeys = [],
  onChange,
}: DocumentFieldsetProps) {
  if (fields.length === 0) {
    return (
      <p className="text-sm text-muted">
        Este formato no tiene campos por llenar: se compone con los datos del paciente y del
        establecimiento.
      </p>
    )
  }

  return (
    <div className="space-y-6">
      {byGroup(fields).map(([group, groupFields]) => (
        <fieldset key={group || 'general'} className="space-y-4" disabled={disabled}>
          {group && (
            <legend className="caption w-full border-b border-border pb-1.5 uppercase tracking-wide">
              {group}
            </legend>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            {groupFields.map((field) => (
              <DocumentControl
                key={field.key}
                field={field}
                values={values}
                disabled={disabled}
                invalid={invalidKeys.includes(field.key)}
                onChange={onChange}
              />
            ))}
          </div>
        </fieldset>
      ))}
    </div>
  )
}

interface DocumentControlProps {
  field: TemplateField
  values: FieldValues
  disabled: boolean
  invalid: boolean
  onChange: (key: string, value: string) => void
}

function DocumentControl({ field, values, disabled, invalid, onChange }: DocumentControlProps) {
  const value = values[field.key] ?? ''
  const label = field.required ? `${field.label} *` : field.label
  const error = invalid ? 'Complete este campo para poder emitir' : null
  const span = field.wide || field.type === 'textarea' ? 'sm:col-span-2' : undefined
  const set = (next: string) => onChange(field.key, next)

  if (field.type === 'computed') {
    return (
      <div className={span}>
        <p className="text-sm font-medium text-foreground">{field.label}</p>
        <p className="mt-1.5 flex h-12 items-center rounded-xl border border-border bg-background/70 px-4 text-sm font-semibold text-foreground">
          {computedValue(field, values)}
        </p>
        {field.help && <p className="mt-1.5 text-xs text-muted">{field.help}</p>}
      </div>
    )
  }

  if (field.type === 'boolean') {
    return (
      <div className={span}>
        <div className="flex h-12 items-center rounded-xl border border-border px-4">
          <Switch
            className="w-full"
            label={field.label}
            description={field.help ?? undefined}
            checked={value === 'true'}
            disabled={disabled}
            onChange={(checked) => set(checked ? 'true' : 'false')}
          />
        </div>
      </div>
    )
  }

  if (field.type === 'odontograma') {
    return <Odontogram value={value} disabled={disabled} onChange={set} />
  }

  if (field.type === 'select') {
    const options: SelectOption[] = field.options ?? []
    return (
      <div className={span}>
        <Select
          label={label}
          options={options}
          placeholder="Sin especificar"
          value={value}
          error={error}
          disabled={disabled}
          onChange={(event) => set(event.target.value)}
        />
        {field.help && !error && <p className="mt-1.5 text-xs text-muted">{field.help}</p>}
      </div>
    )
  }

  if (field.type === 'textarea') {
    return (
      <Textarea
        containerClassName={span}
        label={label}
        rows={3}
        placeholder={field.placeholder ?? undefined}
        hint={field.help ?? undefined}
        value={value}
        error={error}
        disabled={disabled}
        onChange={(event) => set(event.target.value)}
      />
    )
  }

  return (
    <Input
      containerClassName={span}
      label={label}
      type={field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'}
      step={field.type === 'number' ? 'any' : undefined}
      placeholder={field.placeholder ?? undefined}
      hint={field.help ?? undefined}
      value={value}
      error={error}
      disabled={disabled}
      onChange={(event) => set(event.target.value)}
    />
  )
}
