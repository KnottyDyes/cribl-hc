import { useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { brandingApi } from '../api/branding'
import type {
  BrandingConfig,
  ServiceProviderBranding,
  ClientBranding,
  UITheme,
  ThemeMode,
} from '../api/types'

const DEFAULT_BRANDING: BrandingConfig = {
  theme: {
    default_mode: 'system',
    light: {
      primary: '#00A3E0',
      primary_hover: '#0082B3',
      primary_foreground: '#FFFFFF',
      secondary: '#0066A1',
      secondary_hover: '#005080',
      secondary_foreground: '#FFFFFF',
      accent: '#FFB81C',
      accent_hover: '#E6A619',
      accent_foreground: '#1F2937',
      background: '#FFFFFF',
      background_secondary: '#F9FAFB',
      background_tertiary: '#F3F4F6',
      foreground: '#111827',
      foreground_secondary: '#4B5563',
      foreground_muted: '#9CA3AF',
      border: '#E5E7EB',
      border_focus: '#00A3E0',
      severity_critical: '#DC2626',
      severity_high: '#EA580C',
      severity_medium: '#F59E0B',
      severity_low: '#3B82F6',
      severity_info: '#6B7280',
      success: '#10B981',
      warning: '#F59E0B',
      error: '#EF4444',
    },
    dark: {
      primary: '#00A3E0',
      primary_hover: '#33B5E7',
      primary_foreground: '#FFFFFF',
      secondary: '#0066A1',
      secondary_hover: '#3385B5',
      secondary_foreground: '#FFFFFF',
      accent: '#FFB81C',
      accent_hover: '#FFC94D',
      accent_foreground: '#1F2937',
      background: '#111827',
      background_secondary: '#1F2937',
      background_tertiary: '#374151',
      foreground: '#F9FAFB',
      foreground_secondary: '#D1D5DB',
      foreground_muted: '#6B7280',
      border: '#374151',
      border_focus: '#00A3E0',
      severity_critical: '#F87171',
      severity_high: '#FB923C',
      severity_medium: '#FBBF24',
      severity_low: '#60A5FA',
      severity_info: '#9CA3AF',
      success: '#34D399',
      warning: '#FBBF24',
      error: '#F87171',
    },
    font_family: undefined,
    font_family_mono: undefined,
    border_radius: '0.5rem',
    border_radius_lg: '0.75rem',
  },
  report: {
    show_provider_logo: true,
    show_client_logo: true,
    show_footer: true,
    show_watermark: false,
    watermark_text: undefined,
    custom_css: undefined,
    header_template: undefined,
    footer_template: undefined,
  },
}

export function useBranding() {
  const queryClient = useQueryClient()

  const {
    data: branding,
    isLoading,
    error,
  } = useQuery<BrandingConfig>({
    queryKey: ['branding'],
    queryFn: brandingApi.get,
    staleTime: 300000,
  })

  const updateMutation = useMutation({
    mutationFn: brandingApi.update,
    onSuccess: (updatedBranding) => {
      queryClient.setQueryData(['branding'], updatedBranding)
    },
  })

  const resetMutation = useMutation({
    mutationFn: brandingApi.reset,
    onSuccess: (resetBranding) => {
      queryClient.setQueryData(['branding'], resetBranding)
    },
  })

  const updateProviderMutation = useMutation({
    mutationFn: brandingApi.updateProvider,
    onSuccess: (updatedBranding) => {
      queryClient.setQueryData(['branding'], updatedBranding)
    },
  })

  const updateClientMutation = useMutation({
    mutationFn: brandingApi.updateClient,
    onSuccess: (updatedBranding) => {
      queryClient.setQueryData(['branding'], updatedBranding)
    },
  })

  const updateThemeMutation = useMutation({
    mutationFn: brandingApi.updateTheme,
    onSuccess: (updatedTheme) => {
      queryClient.setQueryData(['branding'], (old: BrandingConfig | undefined) => ({
        ...old,
        theme: updatedTheme,
      }))
    },
  })

  const setThemeModeMutation = useMutation({
    mutationFn: brandingApi.setThemeMode,
    onSuccess: (updatedTheme) => {
      queryClient.setQueryData(['branding'], (old: BrandingConfig | undefined) => ({
        ...old,
        theme: updatedTheme,
      }))
    },
  })

  const deleteProviderMutation = useMutation({
    mutationFn: brandingApi.deleteProvider,
    onSuccess: (updatedBranding) => {
      queryClient.setQueryData(['branding'], updatedBranding)
    },
  })

  const deleteClientMutation = useMutation({
    mutationFn: brandingApi.deleteClient,
    onSuccess: (updatedBranding) => {
      queryClient.setQueryData(['branding'], updatedBranding)
    },
  })

  const uploadLogoMutation = useMutation({
    mutationFn: ({
      type,
      file,
    }: {
      type: 'provider' | 'provider_dark' | 'client' | 'client_dark'
      file: File
    }) => brandingApi.uploadLogo(type, file),
    onSuccess: (updatedBranding) => {
      queryClient.setQueryData(['branding'], updatedBranding)
    },
  })

  const deleteLogoMutation = useMutation({
    mutationFn: (type: 'provider' | 'provider_dark' | 'client' | 'client_dark') =>
      brandingApi.deleteLogo(type),
    onSuccess: (updatedBranding) => {
      queryClient.setQueryData(['branding'], updatedBranding)
    },
  })

  const updateBranding = useCallback(
    (data: Partial<BrandingConfig>) => {
      return updateMutation.mutate(data)
    },
    [updateMutation]
  )

  const resetBranding = useCallback(() => {
    return resetMutation.mutate()
  }, [resetMutation])

  const updateProvider = useCallback(
    (provider: ServiceProviderBranding) => {
      return updateProviderMutation.mutate(provider)
    },
    [updateProviderMutation]
  )

  const updateClient = useCallback(
    (client: ClientBranding) => {
      return updateClientMutation.mutate(client)
    },
    [updateClientMutation]
  )

  const updateTheme = useCallback(
    (theme: UITheme) => {
      return updateThemeMutation.mutate(theme)
    },
    [updateThemeMutation]
  )

  const setThemeMode = useCallback(
    (mode: ThemeMode) => {
      return setThemeModeMutation.mutate(mode)
    },
    [setThemeModeMutation]
  )

  const deleteProvider = useCallback(() => {
    return deleteProviderMutation.mutate()
  }, [deleteProviderMutation])

  const deleteClient = useCallback(() => {
    return deleteClientMutation.mutate()
  }, [deleteClientMutation])

  const uploadLogo = useCallback(
    (type: 'provider' | 'provider_dark' | 'client' | 'client_dark', file: File) => {
      return uploadLogoMutation.mutate({ type, file })
    },
    [uploadLogoMutation]
  )

  const deleteLogo = useCallback(
    (type: 'provider' | 'provider_dark' | 'client' | 'client_dark') => {
      return deleteLogoMutation.mutate(type)
    },
    [deleteLogoMutation]
  )

  return {
    branding: branding || DEFAULT_BRANDING,
    isLoading,
    error,
    updateBranding,
    resetBranding,
    updateProvider,
    updateClient,
    updateTheme,
    setThemeMode,
    deleteProvider,
    deleteClient,
    uploadLogo,
    deleteLogo,
    isUpdating: updateMutation.isPending,
    isResetting: resetMutation.isPending,
    isUpdatingProvider: updateProviderMutation.isPending,
    isUpdatingClient: updateClientMutation.isPending,
    isUpdatingTheme: updateThemeMutation.isPending,
    isSettingThemeMode: setThemeModeMutation.isPending,
    isDeletingProvider: deleteProviderMutation.isPending,
    isDeletingClient: deleteClientMutation.isPending,
    isUploadingLogo: uploadLogoMutation.isPending,
    isDeletingLogo: deleteLogoMutation.isPending,
  }
}