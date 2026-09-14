import { Compass } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Button, Card, EmptyState } from '@/components/ui'
import { ROUTES } from '@/routes/paths'

export function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <Card>
      <EmptyState
        icon={Compass}
        title="Página no encontrada"
        description="La ruta solicitada no existe o fue movida."
        action={<Button onClick={() => navigate(ROUTES.dashboard)}>Ir al dashboard</Button>}
      />
    </Card>
  )
}
