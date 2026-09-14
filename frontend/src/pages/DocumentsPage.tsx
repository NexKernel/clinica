import { useEffect, useMemo, useState } from 'react'
import { Ban, FileSignature, FileText, MoreVertical, Pencil, Plus, Printer, Search, Trash2 } from 'lucide-react'

import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  ConfirmDialog,
  Dropdown,
  DropdownItem,
  EmptyState,
  Input,
  PageHeader,
  Pagination,
  Select,
  Table,
  type BadgeVariant,
  type Column,
  type SelectOption,
} from '@/components/ui'
import { DocumentEditorModal } from '@/features/documents/components/DocumentEditorModal'
import { DocumentSheetModal } from '@/features/documents/components/DocumentSheetModal'
import { TemplatePickerModal } from '@/features/documents/components/TemplatePickerModal'
import { useDocumentActions, useDocumentsList } from '@/features/documents/hooks/useDocuments'
import { formatDate } from '@/lib/datetime'
import { getErrorMessage } from '@/services/http'
import {
  DOCUMENT_FAMILIES,
  DOCUMENT_FAMILY_LABELS,
  DOCUMENT_STATUS_LABELS,
  DOCUMENT_STATUSES,
  type DocumentFilters,
  type DocumentListItem,
  type DocumentStatus,
} from '@/types'

const PAGE_SIZE = 10

const STATUS_VARIANT: Record<DocumentStatus, BadgeVariant> = {
  BORRADOR: 'warning',
  EMITIDO: 'success',
  ANULADO: 'danger',
}

const FAMILY_OPTIONS: SelectOption[] = DOCUMENT_FAMILIES.map((family) => ({
  value: family,
  label: DOCUMENT_FAMILY_LABELS[family],
}))

const STATUS_OPTIONS: SelectOption[] = DOCUMENT_STATUSES.map((status) => ({
  value: status,
  label: DOCUMENT_STATUS_LABELS[status],
}))

export function DocumentsPage() {
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [familyFilter, setFamilyFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)

  const [pickerOpen, setPickerOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [sheetId, setSheetId] = useState<number | null>(null)
  const [voiding, setVoiding] = useState<DocumentListItem | null>(null)
  const [deleting, setDeleting] = useState<DocumentListItem | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const { voidDocument, remove } = useDocumentActions()

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const filters: DocumentFilters = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      ...(search ? { search } : {}),
      ...(familyFilter ? { family: familyFilter } : {}),
      ...(statusFilter ? { status: statusFilter } : {}),
    }),
    [page, search, familyFilter, statusFilter],
  )

  const { data, isLoading, isFetching, error } = useDocumentsList(filters)

  const confirmVoid = async (reason: string) => {
    if (!voiding) return
    setActionError(null)
    try {
      await voidDocument.mutateAsync({ id: voiding.id, reason })
      setVoiding(null)
    } catch (err) {
      setActionError(getErrorMessage(err, 'No se pudo anular el documento'))
    }
  }

  const confirmDelete = async () => {
    if (!deleting) return
    setActionError(null)
    try {
      await remove.mutateAsync(deleting.id)
      setDeleting(null)
    } catch (err) {
      setActionError(getErrorMessage(err, 'No se pudo eliminar el borrador'))
    }
  }

  const columns: Column<DocumentListItem>[] = [
    {
      key: 'created',
      header: 'Fecha',
      className: 'w-32 text-muted',
      render: (row) => formatDate(row.issued_at ?? row.created_at),
    },
    {
      key: 'document',
      header: 'Documento',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-foreground">{row.title}</p>
          <p className="truncate text-xs text-muted">
            {row.number} · {row.family_label}
          </p>
        </div>
      ),
    },
    {
      key: 'patient',
      header: 'Paciente',
      className: 'text-muted',
      render: (row) => row.patient_name,
    },
    {
      key: 'practitioner',
      header: 'Profesional',
      className: 'text-muted',
      render: (row) => row.practitioner_name ?? '—',
    },
    {
      key: 'status',
      header: 'Estado',
      className: 'w-32',
      render: (row) => (
        <Badge variant={STATUS_VARIANT[row.status]} dot>
          {row.status_label}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'w-12',
      render: (row) => (
        <Dropdown
          trigger={({ toggle }) => (
            <button
              type="button"
              aria-label={`Acciones de ${row.number}`}
              onClick={toggle}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-muted transition-colors hover:bg-primary/10 hover:text-primary-dark"
            >
              <MoreVertical className="h-4 w-4" />
            </button>
          )}
        >
          {({ close }) => (
            <>
              <DropdownItem
                icon={<Pencil className="h-4 w-4" />}
                onClick={() => {
                  close()
                  setEditingId(row.id)
                }}
              >
                {row.status === 'BORRADOR' ? 'Continuar borrador' : 'Ver documento'}
              </DropdownItem>
              <DropdownItem
                icon={<Printer className="h-4 w-4" />}
                onClick={() => {
                  close()
                  setSheetId(row.id)
                }}
              >
                Imprimir
              </DropdownItem>
              {row.status !== 'ANULADO' && (
                <DropdownItem
                  icon={<Ban className="h-4 w-4" />}
                  onClick={() => {
                    close()
                    setActionError(null)
                    setVoiding(row)
                  }}
                >
                  Anular
                </DropdownItem>
              )}
              {row.status === 'BORRADOR' && (
                <DropdownItem
                  icon={<Trash2 className="h-4 w-4" />}
                  onClick={() => {
                    close()
                    setActionError(null)
                    setDeleting(row)
                  }}
                >
                  Eliminar borrador
                </DropdownItem>
              )}
            </>
          )}
        </Dropdown>
      ),
    },
  ]

  const total = data?.total ?? 0
  const hasFilters = Boolean(search || familyFilter || statusFilter)

  const openPicker = () => {
    setActionError(null)
    setPickerOpen(true)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Formatos de la clínica"
        title="Documentos"
        subtitle="Informes, fichas, consentimientos y actas listos para imprimir"
        actions={
          <Button size="sm" leftIcon={<Plus className="h-4 w-4" />} onClick={openPicker}>
            Nuevo documento
          </Button>
        }
      />

      {actionError && <Alert variant="danger">{actionError}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}

      <Card>
        <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            placeholder="Buscar por paciente, formato o número"
            icon={<Search className="h-[18px] w-[18px]" />}
            value={searchInput}
            containerClassName="lg:col-span-2"
            onChange={(event) => setSearchInput(event.target.value)}
          />
          <Select
            options={FAMILY_OPTIONS}
            placeholder="Todas las familias"
            value={familyFilter}
            onChange={(event) => {
              setFamilyFilter(event.target.value)
              setPage(1)
            }}
          />
          <Select
            options={STATUS_OPTIONS}
            placeholder="Todos los estados"
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(event.target.value)
              setPage(1)
            }}
          />
        </CardBody>

        <Table
          columns={columns}
          data={data?.items ?? []}
          keyExtractor={(row) => row.id}
          isLoading={isLoading}
          className={isFetching && !isLoading ? 'opacity-60 transition-opacity' : undefined}
          emptyState={
            <EmptyState
              icon={hasFilters ? FileText : FileSignature}
              title={hasFilters ? 'Sin resultados' : 'Aún no hay documentos'}
              description={
                hasFilters
                  ? 'Pruebe con otros criterios de búsqueda.'
                  : 'Elija un formato del catálogo y emita el primer documento.'
              }
              action={
                !hasFilters ? (
                  <Button size="sm" leftIcon={<Plus className="h-4 w-4" />} onClick={openPicker}>
                    Nuevo documento
                  </Button>
                ) : undefined
              }
            />
          }
        />

        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          labels={['documento', 'documentos']}
          onChange={setPage}
        />
      </Card>

      <TemplatePickerModal
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onCreated={(documentId) => {
          setPickerOpen(false)
          setEditingId(documentId)
        }}
      />

      <DocumentEditorModal
        open={editingId !== null}
        documentId={editingId}
        onClose={() => setEditingId(null)}
        onPreview={setSheetId}
      />

      <DocumentSheetModal
        open={sheetId !== null}
        documentId={sheetId}
        onClose={() => setSheetId(null)}
      />

      <ConfirmDialog
        open={voiding !== null}
        title="Anular documento"
        description={
          voiding
            ? `${voiding.title} · ${voiding.number}. El documento se conserva como constancia, marcado como anulado.`
            : undefined
        }
        reasonLabel="Motivo de la anulación"
        confirmLabel="Anular"
        variant="danger"
        isLoading={voidDocument.isPending}
        onClose={() => setVoiding(null)}
        onConfirm={(reason) => void confirmVoid(reason)}
      />

      <ConfirmDialog
        open={deleting !== null}
        title="Eliminar borrador"
        description={
          deleting
            ? `${deleting.title} · ${deleting.number}. El borrador se elimina sin dejar rastro; esta acción no se puede deshacer.`
            : undefined
        }
        confirmLabel="Eliminar"
        variant="danger"
        isLoading={remove.isPending}
        onClose={() => setDeleting(null)}
        onConfirm={() => void confirmDelete()}
      />
    </div>
  )
}
