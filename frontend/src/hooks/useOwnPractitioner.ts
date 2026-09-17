import { useAuthStore } from '@/store/auth.store'

/**
 * Ficha de profesional de quien tiene la sesión abierta, para preseleccionarla.
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
export function useOwnPractitionerId(available: readonly { id: number }[]): number | null {
  const own = useAuthStore((state) => state.user?.practitioner_id ?? null)
  return own !== null && available.some((item) => item.id === own) ? own : null
}
