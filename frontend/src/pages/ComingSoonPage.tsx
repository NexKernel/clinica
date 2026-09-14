import { ArrowLeft, Hammer } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

import { Button, Card, EmptyState, PageHeader } from '@/components/ui'
import { findNavItemByPath } from '@/routes/navigation'
import { ROUTES } from '@/routes/paths'

export function ComingSoonPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const item = findNavItemByPath(location.pathname)

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Módulo"
        title={item?.label ?? 'Módulo'}
        subtitle={item?.description}
        actions={
          <Button
            variant="outline"
            size="sm"
            leftIcon={<ArrowLeft className="h-4 w-4" />}
            onClick={() => navigate(ROUTES.dashboard)}
          >
            Volver al dashboard
          </Button>
        }
      />

      <Card>
        <EmptyState
          icon={Hammer}
          title="Próximamente"
          description="Este módulo será habilitado en la siguiente etapa de implementación del sistema."
        />
      </Card>
    </div>
  )
}
