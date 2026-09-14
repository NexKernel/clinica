import { useEffect, useState, type FormEvent } from 'react'
import { Save } from 'lucide-react'

import { Alert, Button, Input, Modal, Select, Switch, type SelectOption } from '@/components/ui'
import { useCatalogActions, useSpecialties } from '@/features/catalog/hooks/useCatalog'
import { getErrorMessage } from '@/services/http'
import {
  SERVICE_KIND_LABELS,
  SERVICE_KINDS,
  type MedicalService,
  type ServiceKind,
} from '@/types'

const KIND_OPTIONS: SelectOption[] = SERVICE_KINDS.map((kind) => ({
  value: kind,
  label: SERVICE_KIND_LABELS[kind],
}))

interface ServiceFormModalProps {
  open: boolean
  service: MedicalService | null
  onClose: () => void
}

export function ServiceFormModal({ open, service, onClose }: ServiceFormModalProps) {
  const isEdit = service !== null
  const { specialties } = useSpecialties()
  const { createService, updateService } = useCatalogActions()
  const isLoading = createService.isPending || updateService.isPending

  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [kind, setKind] = useState<ServiceKind>('CONSULTA')
  const [specialtyId, setSpecialtyId] = useState('')
  const [price, setPrice] = useState('0.00')
  const [duration, setDuration] = useState('20')
  const [isActive, setIsActive] = useState(true)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setFormError(null)

    if (service) {
      setCode(service.code)
      setName(service.name)
      setKind(service.kind)
      setSpecialtyId(service.specialty_id ? String(service.specialty_id) : '')
      setPrice(service.price)
      setDuration(String(service.duration_minutes))
      setIsActive(service.is_active)
      return
    }

    setCode('')
    setName('')
    setKind('CONSULTA')
    setSpecialtyId('')
    setPrice('0.00')
    setDuration('20')
    setIsActive(true)
  }, [open, service])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isLoading) return

    if (code.trim().length < 2) return setFormError('Indique el código del servicio')
    if (name.trim().length < 3) return setFormError('Indique el nombre del servicio')

    const payload = {
      code: code.trim().toUpperCase(),
      name: name.trim(),
      kind,
      specialty_id: specialtyId ? Number(specialtyId) : null,
      price: price || '0.00',
      duration_minutes: Number(duration) || 20,
      is_active: isActive,
    }

    try {
      if (service) {
        await updateService.mutateAsync({ id: service.id, payload })
      } else {
        await createService.mutateAsync(payload)
      }
      onClose()
    } catch (error) {
      setFormError(getErrorMessage(error, 'No se pudo guardar el servicio'))
    }
  }

  const specialtyOptions: SelectOption[] = specialties.map((item) => ({
    value: String(item.id),
    label: item.name,
  }))

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Editar servicio' : 'Nuevo servicio'}
      description="El tarifario alimenta la agenda de citas y la emisión de comprobantes"
      size="md"
      footer={
        <>
          <Button variant="ghost" size="sm" disabled={isLoading} onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="service-form"
            size="sm"
            isLoading={isLoading}
            leftIcon={<Save className="h-4 w-4" />}
          >
            {isEdit ? 'Guardar cambios' : 'Registrar servicio'}
          </Button>
        </>
      }
    >
      <form id="service-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert variant="danger">{formError}</Alert>}

        <div className="grid gap-4 sm:grid-cols-[9rem_1fr]">
          <Input
            label="Código"
            placeholder="CON-GEN"
            value={code}
            disabled={isLoading}
            onChange={(event) => setCode(event.target.value)}
          />
          <Input
            label="Nombre"
            placeholder="Consulta de medicina general"
            value={name}
            disabled={isLoading}
            onChange={(event) => setName(event.target.value)}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Select
            label="Tipo"
            options={KIND_OPTIONS}
            value={kind}
            disabled={isLoading}
            onChange={(event) => setKind(event.target.value as ServiceKind)}
          />
          <Select
            label="Especialidad"
            options={specialtyOptions}
            placeholder="Sin especialidad"
            value={specialtyId}
            disabled={isLoading}
            onChange={(event) => setSpecialtyId(event.target.value)}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Precio"
            type="number"
            step="0.01"
            hint="Precio de lista, IGV incluido"
            value={price}
            disabled={isLoading}
            onChange={(event) => setPrice(event.target.value)}
          />
          <Input
            label="Duración"
            type="number"
            hint="minutos"
            value={duration}
            disabled={isLoading}
            onChange={(event) => setDuration(event.target.value)}
          />
        </div>

        <Switch
          label="Servicio activo"
          description="Los servicios inactivos no aparecen al programar ni al cobrar"
          checked={isActive}
          disabled={isLoading}
          onChange={setIsActive}
        />
      </form>
    </Modal>
  )
}
