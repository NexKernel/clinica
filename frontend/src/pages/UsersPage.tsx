import { useEffect, useMemo, useState } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  KeyRound,
  MoreVertical,
  Pencil,
  Search,
  ShieldOff,
  ShieldCheck,
  UserPlus,
  Users as UsersIcon,
} from 'lucide-react'

import {
  Alert,
  Avatar,
  Badge,
  Button,
  Card,
  CardBody,
  Dropdown,
  DropdownItem,
  EmptyState,
  Input,
  PageHeader,
  Select,
  Table,
  type Column,
  type SelectOption,
} from '@/components/ui'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { ResetPasswordModal } from '@/features/users/components/ResetPasswordModal'
import { UserFormModal } from '@/features/users/components/UserFormModal'
import { useRoles, useUserActions, useUsersList } from '@/features/users/hooks/useUsers'
import { getErrorMessage } from '@/services/http'
import type { User, UserFilters } from '@/types'

const PAGE_SIZE = 10

const STATUS_OPTIONS: SelectOption[] = [
  { value: 'active', label: 'Activos' },
  { value: 'inactive', label: 'Inactivos' },
]

export function UsersPage() {
  const { user: currentUser } = useAuth()
  const { roles } = useRoles()

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)

  const [formOpen, setFormOpen] = useState(false)
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [selected, setSelected] = useState<User | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const { setStatus } = useUserActions()

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const filters: UserFilters = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      ...(search ? { search } : {}),
      ...(roleFilter ? { role: roleFilter } : {}),
      ...(statusFilter ? { is_active: statusFilter === 'active' } : {}),
    }),
    [page, search, roleFilter, statusFilter],
  )

  const { data, isLoading, isFetching, error } = useUsersList(filters)

  const roleOptions: SelectOption[] = roles.map((role) => ({
    value: role.code,
    label: role.name,
  }))

  const openCreate = () => {
    setSelected(null)
    setActionError(null)
    setFormOpen(true)
  }

  const openEdit = (user: User) => {
    setSelected(user)
    setActionError(null)
    setFormOpen(true)
  }

  const openPassword = (user: User) => {
    setSelected(user)
    setActionError(null)
    setPasswordOpen(true)
  }

  const toggleStatus = async (user: User) => {
    setActionError(null)
    try {
      await setStatus.mutateAsync({ id: user.id, isActive: !user.is_active })
    } catch (err) {
      setActionError(getErrorMessage(err, 'No se pudo cambiar el estado del usuario'))
    }
  }

  const columns: Column<User>[] = [
    {
      key: 'user',
      header: 'Usuario',
      render: (row) => (
        <div className="flex items-center gap-3">
          <Avatar name={row.full_name} size="sm" />
          <div className="min-w-0">
            <p className="truncate font-medium text-foreground">{row.full_name}</p>
            <p className="truncate text-xs text-muted">@{row.username}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'email',
      header: 'Correo',
      className: 'text-muted',
      render: (row) => row.email,
    },
    {
      key: 'role',
      header: 'Perfil',
      className: 'w-44',
      render: (row) => <Badge variant="primary">{row.role_name}</Badge>,
    },
    {
      key: 'status',
      header: 'Estado',
      className: 'w-28',
      render: (row) => (
        <Badge variant={row.is_active ? 'success' : 'neutral'} dot>
          {row.is_active ? 'Activo' : 'Inactivo'}
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
              aria-label={`Acciones de ${row.full_name}`}
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
                  openEdit(row)
                }}
              >
                Editar
              </DropdownItem>
              <DropdownItem
                icon={<KeyRound className="h-4 w-4" />}
                onClick={() => {
                  close()
                  openPassword(row)
                }}
              >
                Restablecer contraseña
              </DropdownItem>
              {row.id !== currentUser?.id && (
                <DropdownItem
                  icon={
                    row.is_active ? (
                      <ShieldOff className="h-4 w-4" />
                    ) : (
                      <ShieldCheck className="h-4 w-4" />
                    )
                  }
                  variant={row.is_active ? 'danger' : 'default'}
                  onClick={() => {
                    close()
                    void toggleStatus(row)
                  }}
                >
                  {row.is_active ? 'Desactivar' : 'Activar'}
                </DropdownItem>
              )}
            </>
          )}
        </Dropdown>
      ),
    },
  ]

  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const hasFilters = Boolean(search || roleFilter || statusFilter)

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Sistema"
        title="Usuarios"
        subtitle="Cuentas de acceso y perfiles del personal"
        actions={
          <Button size="sm" leftIcon={<UserPlus className="h-4 w-4" />} onClick={openCreate}>
            Nuevo usuario
          </Button>
        }
      />

      {actionError && <Alert variant="danger">{actionError}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}

      <Card>
        <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            placeholder="Buscar por nombre, usuario o correo"
            icon={<Search className="h-[18px] w-[18px]" />}
            value={searchInput}
            containerClassName="lg:col-span-2"
            onChange={(event) => setSearchInput(event.target.value)}
          />
          <Select
            options={roleOptions}
            placeholder="Todos los perfiles"
            value={roleFilter}
            onChange={(event) => {
              setRoleFilter(event.target.value)
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
              icon={UsersIcon}
              title={hasFilters ? 'Sin resultados' : 'Aún no hay usuarios'}
              description={
                hasFilters
                  ? 'Pruebe con otros criterios de búsqueda.'
                  : 'Registre al personal que utilizará el sistema.'
              }
              action={
                !hasFilters ? (
                  <Button size="sm" leftIcon={<UserPlus className="h-4 w-4" />} onClick={openCreate}>
                    Nuevo usuario
                  </Button>
                ) : undefined
              }
            />
          }
        />

        {total > 0 && (
          <div className="flex flex-col items-center justify-between gap-3 border-t border-border px-5 py-3.5 sm:flex-row">
            <p className="text-xs text-muted">
              {total} {total === 1 ? 'usuario' : 'usuarios'} · página {page} de {totalPages}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                leftIcon={<ChevronLeft className="h-4 w-4" />}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                rightIcon={<ChevronRight className="h-4 w-4" />}
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              >
                Siguiente
              </Button>
            </div>
          </div>
        )}
      </Card>

      <UserFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        user={selected}
        roles={roles}
        isSelf={selected?.id === currentUser?.id}
      />

      <ResetPasswordModal
        open={passwordOpen}
        onClose={() => setPasswordOpen(false)}
        user={selected}
      />
    </div>
  )
}
