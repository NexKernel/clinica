export type NotificationSeverity = 'info' | 'warning' | 'danger'

/** Aviso operativo calculado por el servidor sobre el estado real del sistema. */
export interface AppNotification {
  code: string
  /** Módulo al que pertenece; la campanita lo usa para saber a dónde llevar. */
  module: string
  title: string
  description: string
  count: number
  severity: NotificationSeverity
}

export interface NotificationFeed {
  /** Suma de pendientes: la cifra que se pinta sobre la campanita. */
  total: number
  items: AppNotification[]
}
