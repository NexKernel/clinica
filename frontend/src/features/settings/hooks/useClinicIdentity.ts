import { useBranding } from '@/features/settings/hooks/useSettings'
import { CLINIC } from '@/lib/brand'
import { resolveMediaUrl } from '@/services/http'

export interface ClinicIdentity {
  name: string
  shortName: string
  tagline: string
  location: string
  logoUrl: string | null
}

/**
 * Identidad del establecimiento lista para la interfaz.
 * Cae en los valores por defecto mientras la configuración no esté disponible.
 */
export function useClinicIdentity(): ClinicIdentity {
  const { branding } = useBranding()

  return {
    name: branding?.name ?? CLINIC.name,
    shortName: branding?.short_name ?? CLINIC.shortName,
    tagline: branding?.tagline ?? CLINIC.tagline,
    location: branding?.location ?? CLINIC.location,
    logoUrl: resolveMediaUrl(branding?.logo_url),
  }
}
