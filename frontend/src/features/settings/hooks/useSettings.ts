import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { settingsApi } from '@/features/settings/api/settings.api'
import { getErrorMessage } from '@/services/http'
import type { ClinicSettings, ClinicSettingsPayload } from '@/types'

export const SETTINGS_KEY = ['settings'] as const
export const BRANDING_KEY = ['settings', 'branding'] as const

/** IGV usado mientras la configuración del establecimiento no haya llegado. */
const FALLBACK_TAX_RATE = 18

/** Identidad del establecimiento; se consulta también sin sesión iniciada. */
export function useBranding() {
  const query = useQuery({
    queryKey: BRANDING_KEY,
    queryFn: settingsApi.branding,
    staleTime: 5 * 60 * 1000,
    retry: 0,
  })

  return { branding: query.data ?? null, isLoading: query.isLoading }
}

export function useClinicSettings() {
  const query = useQuery({ queryKey: SETTINGS_KEY, queryFn: settingsApi.get })

  return {
    settings: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ? getErrorMessage(query.error, 'No se pudo cargar la configuración') : null,
    refetch: query.refetch,
  }
}

/**
 * IGV configurado en Configuración → Facturación, como fracción (0.18 para 18 %).
 *
 * Es la misma tasa que aplica el servidor al emitir, de modo que el desglose
 * que ve el cajero mientras arma el comprobante coincide con el guardado.
 */
export function useTaxRate(): number {
  const query = useQuery({
    queryKey: SETTINGS_KEY,
    queryFn: settingsApi.get,
    staleTime: 5 * 60 * 1000,
  })

  return (query.data?.tax_rate ?? FALLBACK_TAX_RATE) / 100
}

function useSettingsMutation<TInput>(
  mutationFn: (input: TInput) => Promise<ClinicSettings>,
  fallbackMessage: string,
) {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn,
    onSuccess: (data) => {
      queryClient.setQueryData(SETTINGS_KEY, data)
      void queryClient.invalidateQueries({ queryKey: BRANDING_KEY })
    },
  })

  return {
    mutate: mutation.mutateAsync,
    isLoading: mutation.isPending,
    isSuccess: mutation.isSuccess,
    error: mutation.error ? getErrorMessage(mutation.error, fallbackMessage) : null,
    reset: mutation.reset,
  }
}

export function useUpdateSettings() {
  return useSettingsMutation<ClinicSettingsPayload>(
    settingsApi.update,
    'No se pudo guardar la configuración',
  )
}

export function useUploadLogo() {
  return useSettingsMutation<File>(settingsApi.uploadLogo, 'No se pudo subir el logo')
}

export function useDeleteLogo() {
  return useSettingsMutation<void>(() => settingsApi.deleteLogo(), 'No se pudo quitar el logo')
}
