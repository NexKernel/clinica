import { useAuthStore } from '@/store/auth.store'

/**
 * Ficha de profesional de quien tiene la sesión abierta.
 *
 * Quien abre una atención o emite una ficha clínica es, casi siempre, quien la
 * firma: obligarlo a buscarse a sí mismo en una lista de profesionales es
 * trabajo que el sistema ya puede ahorrarse, porque sabe quién entró.
 *
 * Se devuelve `null` cuando el perfil no atiende —administración, recepción,
 * caja— y también cuando la ficha propia no está entre las que el selector
 * puede ofrecer: preseleccionar un valor ausente de las opciones dejaría el
 * campo en blanco sin que se entienda por qué.
 */
export function useOwnPractitioner<T extends { id: number }>(available: readonly T[]): T | null {
  const own = useAuthStore((state) => state.user?.practitioner_id ?? null)
  return own === null ? null : (available.find((item) => item.id === own) ?? null)
}

/** Igual que `useOwnPractitioner`, cuando solo hace falta el identificador. */
export function useOwnPractitionerId(available: readonly { id: number }[]): number | null {
  return useOwnPractitioner(available)?.id ?? null
}
