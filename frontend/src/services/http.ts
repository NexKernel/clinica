import axios, { AxiosError, type AxiosInstance } from 'axios'

const baseURL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

/** Origen del backend, usado para servir archivos subidos (logo, adjuntos). */
export const apiOrigin = baseURL.replace(/\/api\/v\d+\/?$/, '')

export function resolveMediaUrl(path: string | null | undefined): string | null {
  if (!path) return null
  if (/^https?:\/\//.test(path)) return path
  return `${apiOrigin}${path.startsWith('/') ? path : `/${path}`}`
}

type TokenGetter = () => string | null
type UnauthorizedHandler = () => void

let getToken: TokenGetter = () => null
let onUnauthorized: UnauthorizedHandler = () => {}

export function configureHttp(options: {
  getToken: TokenGetter
  onUnauthorized: UnauthorizedHandler
}): void {
  getToken = options.getToken
  onUnauthorized = options.onUnauthorized
}

export const http: AxiosInstance = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 20000,
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  // El navegador debe fijar el boundary del multipart al subir archivos.
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
})

/** Endpoints cuyo 401 es parte del flujo, no una sesión expirada. */
const PUBLIC_ENDPOINTS = ['/auth/login']

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const url = error.config?.url ?? ''
    const isPublic = PUBLIC_ENDPOINTS.some((endpoint) => url.includes(endpoint))
    if (error.response?.status === 401 && !isPublic) {
      onUnauthorized()
    }
    return Promise.reject(error)
  },
)

export function getErrorMessage(error: unknown, fallback = 'Ocurrió un error inesperado'): string {
  if (axios.isAxiosError(error)) {
    if (error.code === 'ERR_NETWORK') {
      return 'No se pudo conectar con el servidor'
    }
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string } | undefined
      if (first?.msg) return first.msg.replace(/^Value error,\s*/, '')
    }
  }
  if (error instanceof Error && error.message) return error.message
  return fallback
}
