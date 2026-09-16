import { useMemo, useState } from 'react'
import { Eraser } from 'lucide-react'

import { cn } from '@/lib/utils'

/**
 * Odontograma marcable en notación FDI.
 *
 * El catálogo de hallazgos y la geometría de la pieza están repetidos en
 * `backend/app/core/odontogram.py`, que es quien dibuja el mismo gráfico para
 * la ficha impresa. Si cambia uno hay que cambiar el otro: lo que el dentista
 * marca en pantalla y lo que sale en el papel tienen que coincidir.
 *
 * El código de color es el que ya se usa sobre el formato en papel: rojo lo
 * que falta tratar, azul lo que ya está tratado.
 */

const ROJO = '#c0392b'
const AZUL = '#1f5fa8'
const AZUL_CLARO = '#8ab4e0'
const TRAZO = '#94a3b8'
const TINTA = '#1f2937'

type Cara = 'o' | 'm' | 'd' | 'v' | 'l'
type Marca = 'x' | 'o' | string

interface HallazgoCara {
  clave: string
  label: string
  color: string
}

interface HallazgoPieza {
  clave: string
  label: string
  color: string
  marca: Marca
}

const HALLAZGOS_CARA: HallazgoCara[] = [
  { clave: 'caries', label: 'Caries', color: ROJO },
  { clave: 'obturado', label: 'Obturado', color: AZUL },
  { clave: 'sellante', label: 'Sellante', color: AZUL_CLARO },
]

const HALLAZGOS_PIEZA: HallazgoPieza[] = [
  { clave: 'extraccion', label: 'Exodoncia indicada', color: ROJO, marca: 'x' },
  { clave: 'ausente', label: 'Pieza ausente', color: AZUL, marca: 'x' },
  { clave: 'corona', label: 'Corona', color: AZUL, marca: 'o' },
  { clave: 'implante', label: 'Implante', color: AZUL, marca: 'I' },
  { clave: 'erupcion', label: 'En erupción', color: AZUL, marca: 'E' },
  { clave: 'remanente', label: 'Remanente radicular', color: ROJO, marca: 'R' },
]

const COLOR_CARA = new Map(HALLAZGOS_CARA.map((h) => [h.clave, h.color]))

/** Una hilera es la mitad derecha y la izquierda del diagrama. */
type Fila = [string[], string[]]
type ParDeFilas = [Fila, Fila]
const PIEZA_POR_CLAVE = new Map(HALLAZGOS_PIEZA.map((h) => [h.clave, h]))

const FILAS_PERMANENTES: ParDeFilas = [
  [
    ['18', '17', '16', '15', '14', '13', '12', '11'],
    ['21', '22', '23', '24', '25', '26', '27', '28'],
  ],
  [
    ['48', '47', '46', '45', '44', '43', '42', '41'],
    ['31', '32', '33', '34', '35', '36', '37', '38'],
  ],
]

const FILAS_DECIDUAS: ParDeFilas = [
  [
    ['55', '54', '53', '52', '51'],
    ['61', '62', '63', '64', '65'],
  ],
  [
    ['85', '84', '83', '82', '81'],
    ['71', '72', '73', '74', '75'],
  ],
]

const CELDA = 28
const SEPARACION = 2
const PASO = CELDA + SEPARACION
const LINEA_MEDIA = 14
const SANGRIA = 9
const INTERIOR = CELDA - SANGRIA

// Alturas del diagrama. Tienen que coincidir con las de
// `backend/app/core/odontogram.py`, que dibuja el mismo gráfico para la ficha
// impresa. El bloque deciduo arranca lejos de la hilera permanente para que su
// rótulo no caiga sobre la numeración de abajo.
const Y_TITULO_PERMANENTE = 10
const Y_PERMANENTE_SUPERIOR = 24
const Y_PERMANENTE_INFERIOR = 56
const Y_TITULO_DECIDUO = 112
const Y_DECIDUO_SUPERIOR = 132
const Y_DECIDUO_INFERIOR = 164
const ALTO = 210

const NUM_ARRIBA = 3
const NUM_ABAJO = 9

type Ranura = 'arriba' | 'derecha' | 'abajo' | 'izquierda'

const TRAPECIOS: Record<Ranura, string> = {
  arriba: `0,0 ${CELDA},0 ${INTERIOR},${SANGRIA} ${SANGRIA},${SANGRIA}`,
  derecha: `${CELDA},0 ${CELDA},${CELDA} ${INTERIOR},${INTERIOR} ${INTERIOR},${SANGRIA}`,
  abajo: `0,${CELDA} ${SANGRIA},${INTERIOR} ${INTERIOR},${INTERIOR} ${CELDA},${CELDA}`,
  izquierda: `0,0 ${SANGRIA},${SANGRIA} ${SANGRIA},${INTERIOR} 0,${CELDA}`,
}

const NOMBRE_CARA: Record<Cara, string> = {
  o: 'oclusal',
  m: 'mesial',
  d: 'distal',
  v: 'vestibular',
  l: 'lingual o palatina',
}

/**
 * Qué trapecio le toca a cada cara según el cuadrante.
 *
 * En el maxilar superior la vestibular queda hacia arriba de la hoja y la
 * palatina hacia abajo; en el inferior es al revés. La mesial siempre apunta a
 * la línea media, que está al centro del diagrama.
 */
function ranuras(pieza: string): Record<Exclude<Cara, 'o'>, Ranura> {
  const cuadrante = pieza.charAt(0)
  const superior = ['1', '2', '5', '6'].includes(cuadrante)
  const izquierdaDeLaHoja = ['1', '4', '5', '8'].includes(cuadrante)
  return {
    v: superior ? 'arriba' : 'abajo',
    l: superior ? 'abajo' : 'arriba',
    m: izquierdaDeLaHoja ? 'derecha' : 'izquierda',
    d: izquierdaDeLaHoja ? 'izquierda' : 'derecha',
  }
}

export type MarcasPieza = Partial<Record<Cara, string>> & { pieza?: string }
export type DatosOdontograma = Record<string, MarcasPieza>

/** El formulario guarda texto; aquí se entra y se sale por JSON. */
export function parseOdontograma(raw: string): DatosOdontograma {
  if (!raw.trim()) return {}
  try {
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

type Herramienta = { tipo: 'cara' | 'pieza'; clave: string } | { tipo: 'borrar' } | null

interface OdontogramProps {
  value: string
  disabled?: boolean
  onChange: (next: string) => void
}

export function Odontogram({ value, disabled = false, onChange }: OdontogramProps) {
  const datos = useMemo(() => parseOdontograma(value), [value])
  const [herramienta, setHerramienta] = useState<Herramienta>({ tipo: 'cara', clave: 'caries' })

  const anchoPermanente = 16 * PASO + LINEA_MEDIA - 2 * SEPARACION
  const anchoDeciduo = 10 * PASO + LINEA_MEDIA - 2 * SEPARACION
  const sangriaDecidua = (anchoPermanente - anchoDeciduo) / 2

  const guardar = (siguiente: DatosOdontograma) => {
    // Las piezas que se quedan sin ninguna marca no se guardan: el documento
    // conserva solo lo anotado, no una rejilla de cincuenta y dos vacíos.
    const limpio: DatosOdontograma = {}
    for (const [pieza, marcas] of Object.entries(siguiente)) {
      if (Object.keys(marcas).length > 0) limpio[pieza] = marcas
    }
    onChange(Object.keys(limpio).length ? JSON.stringify(limpio) : '')
  }

  const marcarCara = (pieza: string, cara: Cara) => {
    if (disabled || !herramienta) return
    if (herramienta.tipo === 'pieza') return
    const actual = { ...(datos[pieza] ?? {}) }
    if (herramienta.tipo === 'borrar' || actual[cara] === herramienta.clave) delete actual[cara]
    else actual[cara] = herramienta.clave
    guardar({ ...datos, [pieza]: actual })
  }

  const marcarPieza = (pieza: string) => {
    if (disabled || !herramienta) return
    if (herramienta.tipo === 'cara') return
    if (herramienta.tipo === 'borrar') {
      const siguiente = { ...datos }
      delete siguiente[pieza]
      guardar(siguiente)
      return
    }
    const actual = { ...(datos[pieza] ?? {}) }
    if (actual.pieza === herramienta.clave) delete actual.pieza
    else actual.pieza = herramienta.clave
    guardar({ ...datos, [pieza]: actual })
  }

  const dibujarPieza = (pieza: string, x: number, y: number) => {
    const marcas = datos[pieza] ?? {}
    const slots = ranuras(pieza)
    const estado = marcas.pieza ? PIEZA_POR_CLAVE.get(marcas.pieza) : undefined
    const activaCara = herramienta?.tipo === 'cara' || herramienta?.tipo === 'borrar'

    return (
      <g key={pieza} transform={`translate(${x},${y})`}>
        {(Object.keys(slots) as Exclude<Cara, 'o'>[]).map((cara) => (
          <polygon
            key={cara}
            points={TRAPECIOS[slots[cara]]}
            fill={COLOR_CARA.get(marcas[cara] ?? '') ?? 'transparent'}
            stroke={TRAZO}
            strokeWidth={0.6}
            className={cn(activaCara && !disabled && 'cursor-pointer hover:opacity-70')}
            onClick={() => marcarCara(pieza, cara)}
          >
            <title>{`Pieza ${pieza} · ${NOMBRE_CARA[cara]}`}</title>
          </polygon>
        ))}
        <rect
          x={SANGRIA}
          y={SANGRIA}
          width={INTERIOR - SANGRIA}
          height={INTERIOR - SANGRIA}
          fill={COLOR_CARA.get(marcas.o ?? '') ?? 'transparent'}
          stroke={TRAZO}
          strokeWidth={0.6}
          className={cn(activaCara && !disabled && 'cursor-pointer hover:opacity-70')}
          onClick={() => marcarCara(pieza, 'o')}
        >
          <title>{`Pieza ${pieza} · oclusal o incisal`}</title>
        </rect>
        {estado?.marca === 'x' && (
          <path
            d={`M2,2 L${CELDA - 2},${CELDA - 2} M${CELDA - 2},2 L2,${CELDA - 2}`}
            stroke={estado.color}
            strokeWidth={2}
            fill="none"
            pointerEvents="none"
          />
        )}
        {estado?.marca === 'o' && (
          <circle
            cx={CELDA / 2}
            cy={CELDA / 2}
            r={CELDA / 2 - 1}
            stroke={estado.color}
            strokeWidth={2}
            fill="none"
            pointerEvents="none"
          />
        )}
        {estado && estado.marca !== 'x' && estado.marca !== 'o' && (
          <text
            x={CELDA / 2}
            y={CELDA / 2 + 4}
            textAnchor="middle"
            fontSize={13}
            fontWeight={700}
            fill={estado.color}
            pointerEvents="none"
          >
            {estado.marca}
          </text>
        )}
      </g>
    )
  }

  const dibujarFila = (
    fila: Fila,
    origenX: number,
    y: number,
    numerosArriba: boolean,
  ) => {
    const salto = fila[0].length * PASO + LINEA_MEDIA - SEPARACION
    const numeroY = numerosArriba ? y - NUM_ARRIBA : y + CELDA + NUM_ABAJO
    const activaPieza = herramienta?.tipo === 'pieza' || herramienta?.tipo === 'borrar'

    return fila.flatMap((mitad, indiceMitad) =>
      mitad.map((pieza, i) => {
        const x = origenX + indiceMitad * salto + i * PASO
        return (
          <g key={`g-${pieza}`}>
            {dibujarPieza(pieza, x, y)}
            <text
              x={x + CELDA / 2}
              y={numeroY}
              textAnchor="middle"
              fontSize={7.5}
              fill={datos[pieza]?.pieza ? PIEZA_POR_CLAVE.get(datos[pieza].pieza!)?.color : TINTA}
              fontWeight={datos[pieza]?.pieza ? 700 : 400}
              className={cn(activaPieza && !disabled && 'cursor-pointer')}
              onClick={() => marcarPieza(pieza)}
            >
              <title>{`Pieza ${pieza}`}</title>
              {pieza}
            </text>
          </g>
        )
      }),
    )
  }

  const conHallazgos = Object.keys(datos).length
  const chip = (activa: boolean, color?: string) =>
    cn(
      'inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs transition',
      activa ? 'border-primary bg-primary/10 font-semibold text-foreground' : 'border-border text-muted',
      disabled ? 'cursor-not-allowed opacity-60' : 'hover:border-primary/60',
      color && '',
    )

  return (
    <div className="sm:col-span-2 space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-foreground">Odontograma</p>
        <p className="text-xs text-muted">
          {conHallazgos === 0
            ? 'Sin hallazgos registrados'
            : `${conHallazgos} pieza${conHallazgos === 1 ? '' : 's'} con hallazgos`}
        </p>
      </div>

      <div className="space-y-2 rounded-xl border border-border p-3">
        <div className="flex flex-wrap gap-1.5">
          {HALLAZGOS_CARA.map((h) => (
            <button
              key={h.clave}
              type="button"
              disabled={disabled}
              className={chip(herramienta?.tipo === 'cara' && herramienta.clave === h.clave)}
              onClick={() => setHerramienta({ tipo: 'cara', clave: h.clave })}
            >
              <span
                className="h-3 w-3 rounded-sm border border-border"
                style={{ backgroundColor: h.color }}
              />
              {h.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {HALLAZGOS_PIEZA.map((h) => (
            <button
              key={h.clave}
              type="button"
              disabled={disabled}
              className={chip(herramienta?.tipo === 'pieza' && herramienta.clave === h.clave)}
              onClick={() => setHerramienta({ tipo: 'pieza', clave: h.clave })}
            >
              <span className="font-bold" style={{ color: h.color }}>
                {h.marca === 'x' ? '✕' : h.marca === 'o' ? '◯' : h.marca}
              </span>
              {h.label}
            </button>
          ))}
          <button
            type="button"
            disabled={disabled}
            className={chip(herramienta?.tipo === 'borrar')}
            onClick={() => setHerramienta({ tipo: 'borrar' })}
          >
            <Eraser className="h-3.5 w-3.5" />
            Borrar
          </button>
        </div>
        <p className="text-xs text-muted">
          {herramienta?.tipo === 'pieza'
            ? 'Haga clic en el número de la pieza para marcarla entera.'
            : herramienta?.tipo === 'borrar'
              ? 'Haga clic en una cara para borrarla, o en el número para dejar la pieza limpia.'
              : 'Haga clic en una cara de la pieza para marcarla.'}
        </p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border bg-white p-3">
        <svg
          viewBox={`0 0 ${anchoPermanente} ${ALTO}`}
          className="block h-auto w-full min-w-[520px]"
          role="img"
          aria-label="Odontograma en notación FDI"
        >
          <text x={0} y={Y_TITULO_PERMANENTE} fontSize={8} fontWeight={700} fill={TINTA}>
            DENTICIÓN PERMANENTE
          </text>
          {dibujarFila(FILAS_PERMANENTES[0], 0, Y_PERMANENTE_SUPERIOR, true)}
          {dibujarFila(FILAS_PERMANENTES[1], 0, Y_PERMANENTE_INFERIOR, false)}
          <text x={sangriaDecidua} y={Y_TITULO_DECIDUO} fontSize={8} fontWeight={700} fill={TINTA}>
            DENTICIÓN DECIDUA
          </text>
          {dibujarFila(FILAS_DECIDUAS[0], sangriaDecidua, Y_DECIDUO_SUPERIOR, true)}
          {dibujarFila(FILAS_DECIDUAS[1], sangriaDecidua, Y_DECIDUO_INFERIOR, false)}
        </svg>
      </div>
    </div>
  )
}
