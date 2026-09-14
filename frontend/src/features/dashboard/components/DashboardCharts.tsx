import { useMemo } from 'react'
import type { ChartConfiguration } from 'chart.js'

import { ChartCanvas } from '@/components/charts/ChartCanvas'
import { ChartCard, type ChartLegendItem } from '@/components/charts/ChartCard'
import {
  axisTicks,
  baseOptions,
  directLabelPlugin,
  formatCurrencyValue,
  formatNumber,
  gridLine,
  noGrid,
  token,
} from '@/lib/chart'
import type { SeriesPoint, StatusSlice } from '@/types'

/* Tokens de la paleta de datos, asignados en orden a los estados de la agenda. */
const STATUS_TOKENS = ['chart-1', 'chart-3', 'chart-2', 'chart-4'] as const
const STATUS_CLASSES = ['bg-chart-1', 'bg-chart-3', 'bg-chart-2', 'bg-chart-4'] as const

interface SeriesProps {
  points: SeriesPoint[]
}

/** Atenciones registradas por día: una serie, con etiqueta sólo en el extremo. */
export function AttentionsChart({ points }: SeriesProps) {
  const labels = points.map((point) => point.label)
  const values = points.map((point) => point.value)

  const config = useMemo<ChartConfiguration>(() => {
    const base = baseOptions()

    return {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Atenciones',
            data: values,
            borderColor: token('chart-1'),
            backgroundColor: token('chart-1'),
            pointBackgroundColor: token('chart-1'),
            pointBorderColor: token('brand-surface'),
            pointBorderWidth: 2,
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointHitRadius: 18,
            tension: 0.35,
            fill: false,
          },
        ],
      },
      options: {
        ...base,
        // Espacio a la derecha para la etiqueta del extremo.
        layout: { padding: { top: 18, right: 40, bottom: 0, left: 0 } },
        scales: {
          x: { grid: noGrid, border: { display: false }, ticks: axisTicks() },
          y: {
            beginAtZero: true,
            grid: gridLine(),
            border: { display: false },
            ticks: { ...axisTicks(formatNumber), maxTicksLimit: 5 },
          },
        },
      },
      plugins: [
        directLabelPlugin({
          pick: (_datasetIndex, index, _value, series) => index === series.length - 1,
          format: formatNumber,
          align: 'right',
        }),
      ],
    }
  }, [labels, values])

  return (
    <ChartCard
      title="Atenciones de la semana"
      description="Consultas registradas por día"
      height="h-64 sm:h-72"
      table={{
        headers: ['Día', 'Atenciones'],
        rows: points.map((point) => [point.label, point.value]),
      }}
    >
      <ChartCanvas config={config} ariaLabel="Atenciones médicas registradas por día" />
    </ChartCard>
  )
}

/** Ingresos por día: columnas con extremo redondeado y máximo rotulado. */
export function RevenueChart({ points }: SeriesProps) {
  const labels = points.map((point) => point.label)
  const values = points.map((point) => point.value)

  const config = useMemo<ChartConfiguration>(() => {
    const base = baseOptions()
    const max = values.length > 0 ? Math.max(...values) : 0

    return {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Ingresos',
            data: values,
            backgroundColor: token('chart-1'),
            hoverBackgroundColor: token('chart-1', 0.85),
            borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 },
            borderSkipped: false,
            maxBarThickness: 24,
          },
        ],
      },
      options: {
        ...base,
        plugins: {
          ...base.plugins,
          tooltip: {
            ...base.plugins?.tooltip,
            callbacks: {
              label: (item) => ` ${formatCurrencyValue(Number(item.raw))}`,
            },
          },
        },
        scales: {
          x: { grid: noGrid, border: { display: false }, ticks: axisTicks() },
          y: {
            beginAtZero: true,
            grid: gridLine(),
            border: { display: false },
            ticks: { ...axisTicks(formatCurrencyValue), maxTicksLimit: 5 },
          },
        },
      },
      plugins: [
        directLabelPlugin({
          pick: (_dataset, _index, value) => max > 0 && value === max,
          format: formatCurrencyValue,
        }),
      ],
    }
  }, [labels, values])

  return (
    <ChartCard
      title="Ingresos de la semana"
      description="Cobros registrados en caja por día"
      height="h-64 sm:h-72"
      table={{
        headers: ['Día', 'Ingresos'],
        rows: points.map((point) => [point.label, formatCurrencyValue(point.value)]),
      }}
    >
      <ChartCanvas config={config} ariaLabel="Ingresos de caja por día de la semana" />
    </ChartCard>
  )
}

interface StatusProps {
  slices: StatusSlice[]
}

/** Estado de las citas de hoy: barra apilada de parte-a-todo. */
export function AppointmentStatusChart({ slices }: StatusProps) {
  const total = slices.reduce((sum, item) => sum + item.value, 0)

  const config = useMemo<ChartConfiguration>(() => {
    const base = baseOptions()
    const lastIndex = slices.length - 1

    return {
      type: 'bar',
      data: {
        labels: ['Citas'],
        datasets: slices.map((item, index) => ({
          label: item.label,
          data: [item.value],
          backgroundColor: token(STATUS_TOKENS[index % STATUS_TOKENS.length] as string),
          borderColor: token('brand-surface'),
          borderWidth: { top: 0, bottom: 0, left: index === 0 ? 0 : 2, right: 0 },
          borderSkipped: false,
          borderRadius:
            index === 0
              ? { topLeft: 6, bottomLeft: 6, topRight: 0, bottomRight: 0 }
              : index === lastIndex
                ? { topLeft: 0, bottomLeft: 0, topRight: 6, bottomRight: 6 }
                : 0,
          barThickness: 22,
        })),
      },
      options: {
        ...base,
        indexAxis: 'y',
        layout: { padding: 0 },
        interaction: { mode: 'nearest', intersect: true },
        plugins: {
          ...base.plugins,
          tooltip: {
            ...base.plugins?.tooltip,
            callbacks: {
              title: (items) => items[0]?.dataset.label ?? '',
              label: (item) =>
                ` ${item.raw} de ${total} citas (${Math.round((Number(item.raw) / total) * 100)}%)`,
            },
          },
        },
        scales: {
          x: { stacked: true, display: false, grid: noGrid },
          y: { stacked: true, display: false, grid: noGrid },
        },
      },
    }
  }, [slices, total])

  const legend: ChartLegendItem[] = slices.map((item, index) => ({
    label: item.label,
    colorClass: STATUS_CLASSES[index % STATUS_CLASSES.length] as string,
    value: `${item.value} · ${Math.round((item.value / total) * 100)}%`,
  }))

  if (total === 0) {
    return (
      <ChartCard
        title="Citas de hoy por estado"
        description="Aún no hay citas registradas para hoy"
        height="h-12"
        table={{ headers: ['Estado', 'Citas'], rows: [] }}
      >
        <p className="flex h-full items-center text-sm text-muted">Sin citas en la agenda.</p>
      </ChartCard>
    )
  }

  return (
    <ChartCard
      title="Citas de hoy por estado"
      description={`${total} citas registradas en la agenda`}
      legend={legend}
      height="h-12"
      table={{
        headers: ['Estado', 'Citas', '%'],
        rows: slices.map((item) => [
          item.label,
          item.value,
          `${Math.round((item.value / total) * 100)}%`,
        ]),
      }}
    >
      <ChartCanvas config={config} ariaLabel="Distribución de las citas de hoy por estado" />
    </ChartCard>
  )
}
