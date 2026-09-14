import { useEffect, useRef } from 'react'
import {
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  Legend,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
  type ChartConfiguration,
} from 'chart.js'

// Registro explícito: sólo los controladores y escalas que usa el sistema.
Chart.register(
  BarController,
  BarElement,
  CategoryScale,
  Legend,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
)

interface ChartCanvasProps {
  /** Configuración completa de Chart.js; se recrea si cambia la referencia. */
  config: ChartConfiguration
  /** Descripción accesible del gráfico. */
  ariaLabel: string
  className?: string
}

export function ChartCanvas({ config, ariaLabel, className }: ChartCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const chart = new Chart(canvas, config)

    // El lienzo puede montarse antes de que el contenedor tenga su ancho final
    // (y en StrictMode el gráfico se crea dos veces): re-medimos tras el layout
    // para que escalas y elementos compartan siempre la misma geometría.
    const relayout = () => {
      chart.resize()
      chart.update('none')
    }
    const frame = requestAnimationFrame(relayout)

    return () => {
      cancelAnimationFrame(frame)
      chart.destroy()
    }
  }, [config])

  return (
    <canvas ref={canvasRef} role="img" aria-label={ariaLabel} className={className}>
      {ariaLabel}
    </canvas>
  )
}
