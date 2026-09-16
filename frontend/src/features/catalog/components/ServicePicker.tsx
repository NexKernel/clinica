import { useCallback } from 'react'

import { EntityPicker } from '@/components/common/EntityPicker'
import { catalogApi } from '@/features/catalog/api/catalog.api'
import { formatMoney } from '@/lib/utils'
import type { MedicalService } from '@/types'

/** Resultados por búsqueda: suficientes para elegir sin llenar la pantalla. */
const MAX_RESULTS = 20

interface ServicePickerProps {
  label?: string
  placeholder?: string
  value: MedicalService | null
  onChange: (service: MedicalService | null) => void
  disabled?: boolean
  error?: string | null
  hint?: string
  containerClassName?: string
}

/**
 * Selector del tarifario con búsqueda contra la API.
 *
 * El tarifario del policlínico pasa de los seiscientos servicios, de modo que
 * no cabe en un desplegable: se busca por nombre o por código y solo viaja la
 * página de resultados que el usuario ve.
 */
export function ServicePicker({
  label = 'Servicio',
  placeholder = 'Nombre o código del servicio',
  value,
  onChange,
  disabled,
  error,
  hint,
  containerClassName,
}: ServicePickerProps) {
  const search = useCallback(async (term: string) => {
    const page = await catalogApi.services({
      page: 1,
      page_size: MAX_RESULTS,
      search: term,
      is_active: true,
    })
    return page.items
  }, [])

  return (
    <EntityPicker<MedicalService>
      label={label}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      search={search}
      disabled={disabled}
      error={error}
      hint={hint}
      containerClassName={containerClassName}
      emptyLabel="No se encontraron servicios"
      getKey={(service) => service.id}
      getLabel={(service) => service.name}
      renderItem={(service) => (
        <div className="flex items-baseline justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate font-medium text-foreground">{service.name}</p>
            <p className="truncate text-xs text-muted">
              {service.code} · {service.specialty_name ?? service.kind_label}
            </p>
          </div>
          <span className="shrink-0 text-xs font-semibold text-primary-dark">
            {formatMoney(service.price)}
          </span>
        </div>
      )}
    />
  )
}
