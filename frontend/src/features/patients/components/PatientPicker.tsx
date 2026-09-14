import { useCallback } from 'react'

import { EntityPicker } from '@/components/common/EntityPicker'
import { patientsApi } from '@/features/patients/api/patients.api'
import type { PatientSummary } from '@/types'

interface PatientPickerProps {
  label?: string
  value: PatientSummary | null
  onChange: (patient: PatientSummary | null) => void
  disabled?: boolean
  error?: string | null
  hint?: string
}

export function PatientPicker({
  label = 'Paciente',
  value,
  onChange,
  disabled,
  error,
  hint,
}: PatientPickerProps) {
  const search = useCallback((term: string) => patientsApi.search(term), [])

  return (
    <EntityPicker<PatientSummary>
      label={label}
      placeholder="Nombre, DNI o número de historia"
      hint={hint}
      value={value}
      onChange={onChange}
      search={search}
      disabled={disabled}
      error={error}
      emptyLabel="No se encontraron pacientes"
      getKey={(patient) => patient.id}
      getLabel={(patient) => patient.full_name}
      renderItem={(patient) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{patient.full_name}</p>
          <p className="truncate text-xs text-muted">
            {patient.history_number}
            {patient.document_number ? ` · ${patient.document_type} ${patient.document_number}` : ''}
            {patient.age !== null ? ` · ${patient.age} años` : ''}
          </p>
        </div>
      )}
    />
  )
}
