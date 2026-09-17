import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Save } from 'lucide-react'

import { Alert, Button, Input, Modal, Select, Textarea, type SelectOption } from '@/components/ui'
import { useActivePractitioners } from '@/features/catalog/hooks/useCatalog'
import { useCredActions, useCredCatalog } from '@/features/cred/hooks/useCred'
import { useOwnPractitionerId } from '@/hooks/useOwnPractitioner'
import { getErrorMessage } from '@/services/http'

const hoy = () => new Date().toISOString().slice(0, 10)

interface CredEntryModalProps {
  open: boolean
  patientId: number
  onClose: () => void
}

export function CredEntryModal({ open, patientId, onClose }: CredEntryModalProps) {
  const { items, isLoading: loadingCatalog } = useCredCatalog(patientId, open)
  const { practitioners } = useActivePractitioners()
  const ownPractitionerId = useOwnPractitionerId(practitioners)
  const { create } = useCredActions(patientId)

  const [itemCode, setItemCode] = useState('')
  const [performedOn, setPerformedOn] = useState(hoy)
  const [result, setResult] = useState('')
  const [notes, setNotes] = useState('')
  const [practitionerId, setPractitionerId] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setItemCode('')
    setPerformedOn(hoy())
    setResult('')
    setNotes('')
    setPractitionerId('')
    setFormError(null)
  }, [open])

  /* Ver nota en EncounterFormModal: el relleno de la ficha propia va aparte
     del reinicio, porque la lista de profesionales llega más tarde. */
  useEffect(() => {
    if (!open || !ownPractitionerId) return
    setPractitionerId((actual) => actual || String(ownPractitionerId))
  }, [open, ownPractitionerId])

  /* Lo ya aplicado que no se repite se ofrece igual, pero anotado: así se ve
     que está puesto en vez de desaparecer sin explicación de la lista. */
  const options: SelectOption[] = useMemo(
    () =>
      items
        .filter((item) => item.repeatable || !item.already_applied)
        .map((item) => ({
          value: item.code,
          label: `${item.kind_label} · ${item.label}`,
        })),
    [items],
  )

  const selected = items.find((item) => item.code === itemCode) ?? null
  const yaAplicadas = items.filter((item) => !item.repeatable && item.already_applied).length

  const practitionerOptions: SelectOption[] = practitioners.map((item) => ({
    value: String(item.id),
    label: item.full_name,
  }))

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (create.isPending) return
    if (!itemCode) return setFormError('Elija la prestación aplicada')
    if (!performedOn) return setFormError('Indique la fecha en que se aplicó')

    try {
      await create.mutateAsync({
        patient_id: patientId,
        item_code: itemCode,
        performed_on: performedOn,
        result: result.trim() || null,
        notes: notes.trim() || null,
        practitioner_id: practitionerId ? Number(practitionerId) : null,
      })
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo registrar la prestación'))
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Registrar prestación del carné"
      description="Anote lo aplicado: vacuna, control, tamizaje, suplemento o sesión"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={create.isPending}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="cred-form"
            size="sm"
            isLoading={create.isPending}
            leftIcon={<Save className="h-4 w-4" />}
          >
            Registrar
          </Button>
        </>
      }
    >
      <form id="cred-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        <Select
          label="Prestación"
          options={options}
          placeholder={loadingCatalog ? 'Cargando el calendario…' : 'Elija la prestación'}
          value={itemCode}
          disabled={create.isPending || loadingCatalog}
          onChange={(event) => {
            setItemCode(event.target.value)
            setFormError(null)
          }}
        />
        {yaAplicadas > 0 && (
          <p className="-mt-2 text-xs text-muted">
            {yaAplicadas} prestaciones no figuran en la lista porque ya constan aplicadas.
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Fecha de aplicación"
            type="date"
            max={hoy()}
            value={performedOn}
            disabled={create.isPending}
            onChange={(event) => setPerformedOn(event.target.value)}
          />
          <Select
            label="Profesional que la aplicó"
            options={practitionerOptions}
            placeholder="Sin especificar"
            value={practitionerId}
            disabled={create.isPending}
            onChange={(event) => setPractitionerId(event.target.value)}
          />
        </div>

        {selected?.records_result && (
          <Input
            label="Resultado"
            placeholder="Hb 11.2 g/dL · Negativo"
            hint="Queda en el carné junto a la fecha"
            value={result}
            disabled={create.isPending}
            onChange={(event) => setResult(event.target.value)}
          />
        )}

        <Textarea
          label="Observaciones"
          value={notes}
          disabled={create.isPending}
          onChange={(event) => setNotes(event.target.value)}
        />
      </form>
    </Modal>
  )
}
