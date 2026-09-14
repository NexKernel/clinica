import { useState } from 'react'
import { Building2, FileClock, Receipt, RefreshCw, ShieldCheck, Stethoscope, Tag } from 'lucide-react'

import { Alert, Button, Card, LoadingState, PageHeader, Tabs, type TabItem } from '@/components/ui'
import { PractitionersPanel, ServicesPanel } from '@/features/admin/components/CatalogPanels'
import {
  AuditPanel,
  PermissionsPanel,
  SeriesPanel,
} from '@/features/admin/components/SecurityPanels'
import { LogoUploader } from '@/features/settings/components/LogoUploader'
import { SettingsForm } from '@/features/settings/components/SettingsForm'
import { useClinicSettings } from '@/features/settings/hooks/useSettings'

const TABS: TabItem[] = [
  { key: 'general', label: 'Establecimiento', icon: Building2 },
  { key: 'practitioners', label: 'Profesionales', icon: Stethoscope },
  { key: 'services', label: 'Tarifario', icon: Tag },
  { key: 'series', label: 'Comprobantes', icon: Receipt },
  { key: 'permissions', label: 'Permisos', icon: ShieldCheck },
  { key: 'audit', label: 'Auditoría', icon: FileClock },
]

export function SettingsPage() {
  const [tab, setTab] = useState('general')
  const { settings, isLoading, error, refetch } = useClinicSettings()

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Sistema"
        title="Configuración"
        subtitle="Datos del establecimiento, catálogos y seguridad del sistema"
      />

      <Tabs items={TABS} active={tab} onChange={setTab} />

      {tab === 'general' && (
        <>
          {isLoading && (
            <Card>
              <LoadingState label="Cargando configuración…" />
            </Card>
          )}

          {!isLoading && error && (
            <Alert variant="danger">
              <span className="flex flex-wrap items-center gap-3">
                {error}
                <Button
                  variant="outline"
                  size="sm"
                  leftIcon={<RefreshCw className="h-4 w-4" />}
                  onClick={() => void refetch()}
                >
                  Reintentar
                </Button>
              </span>
            </Alert>
          )}

          {settings && (
            <div className="space-y-4">
              <LogoUploader logoUrl={settings.logo_url} name={settings.name} />
              <SettingsForm settings={settings} />
            </div>
          )}
        </>
      )}

      {tab === 'practitioners' && <PractitionersPanel />}
      {tab === 'services' && <ServicesPanel />}
      {tab === 'series' && <SeriesPanel />}
      {tab === 'permissions' && <PermissionsPanel />}
      {tab === 'audit' && <AuditPanel />}
    </div>
  )
}
