import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from '@/app/App'
import { AppProviders } from '@/app/providers'
import '@/index.css'

const container = document.getElementById('root')
if (!container) throw new Error('No se encontró el contenedor raíz de la aplicación')

createRoot(container).render(
  <StrictMode>
    <AppProviders>
      <App />
    </AppProviders>
  </StrictMode>,
)
