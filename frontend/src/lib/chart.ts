import type { ChartOptions, Plugin, TooltipModel } from 'chart.js'

import { LOCALE } from '@/lib/datetime'
import { formatCurrency } from '@/lib/utils'

/** Lee un token de color del sistema de diseño y lo devuelve como rgb(). */
export function token(name: string, alpha = 1): string {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim()
  const channels = raw || '0 0 0'
  return alpha === 1 ? `rgb(${channels})` : `rgb(${channels} / ${alpha})`
}

export const prefersReducedMotion = (): boolean =>
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

export const FONT_FAMILY = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"

export const formatCurrencyValue = formatCurrency
export const formatNumber = (value: number): string => new Intl.NumberFormat(LOCALE).format(value)

/**
 * Base común: rejilla discreta de una sola línea sólida, tipografía del sistema
 * y tooltip con la superficie de la marca.
 */
export function baseOptions(): ChartOptions {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: prefersReducedMotion() ? false : { duration: 420 },
    interaction: { mode: 'index', intersect: false },
    layout: { padding: { top: 18, right: 14, bottom: 0, left: 0 } },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: token('brand-surface'),
        titleColor: token('brand-foreground'),
        bodyColor: token('brand-foreground'),
        borderColor: token('brand-border'),
        borderWidth: 1,
        cornerRadius: 12,
        padding: 12,
        boxPadding: 6,
        usePointStyle: true,
        titleFont: { family: FONT_FAMILY, size: 12, weight: 600 },
        bodyFont: { family: FONT_FAMILY, size: 12 },
        displayColors: true,
      },
    },
  }
}

export function axisTicks(formatter?: (value: number) => string) {
  return {
    color: token('brand-muted'),
    font: { family: FONT_FAMILY, size: 11 },
    padding: 8,
    ...(formatter
      ? { callback: (value: string | number) => formatter(Number(value)) }
      : {}),
  }
}

export const gridLine = () => ({
  color: token('brand-border'),
  lineWidth: 1,
  drawTicks: false,
})

export const noGrid = { display: false, drawTicks: false }

/**
 * Etiquetas directas selectivas: sólo los puntos indicados por `pick`.
 * Evita el anti-patrón de rotular cada punto de la serie.
 */
export function directLabelPlugin(options: {
  pick: (datasetIndex: number, index: number, value: number, values: number[]) => boolean
  format: (value: number) => string
  align?: 'top' | 'right'
}): Plugin<'line' | 'bar'> {
  return {
    id: 'directLabels',
    afterDatasetsDraw(chart) {
      const { ctx } = chart
      ctx.save()
      ctx.font = `600 11px ${FONT_FAMILY}`
      ctx.fillStyle = token('brand-foreground')

      chart.data.datasets.forEach((dataset, datasetIndex) => {
        const meta = chart.getDatasetMeta(datasetIndex)
        if (meta.hidden) return
        const values = (dataset.data as number[]) ?? []

        meta.data.forEach((element, index) => {
          const value = values[index]
          if (typeof value !== 'number') return
          if (!options.pick(datasetIndex, index, value, values)) return

          const text = options.format(value)
          if (options.align === 'right') {
            ctx.textAlign = 'left'
            ctx.textBaseline = 'middle'
            ctx.fillText(text, element.x + 10, element.y)
          } else {
            ctx.textAlign = 'center'
            ctx.textBaseline = 'bottom'
            ctx.fillText(text, element.x, element.y - 10)
          }
        })
      })
      ctx.restore()
    },
  }
}

export type ChartTooltip = TooltipModel<'line' | 'bar'>
