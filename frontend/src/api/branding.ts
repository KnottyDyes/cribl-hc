import { apiClient } from './client'
import type {
  BrandingConfig,
  ServiceProviderBranding,
  ClientBranding,
  UITheme,
  ThemeMode,
  ReportBranding,
} from './types'

/**
 * Branding management API endpoints
 */
export const brandingApi = {
  /**
   * Get current branding configuration
   * GET /api/v1/branding
   */
  get: async (): Promise<BrandingConfig> => {
    return apiClient.get('/api/v1/branding')
  },

  /**
   * Update branding configuration (partial update supported)
   * PUT /api/v1/branding
   */
  update: async (data: Partial<BrandingConfig>): Promise<BrandingConfig> => {
    return apiClient.put('/api/v1/branding', data)
  },

  /**
   * Reset branding to default values
   * POST /api/v1/branding/reset
   */
  reset: async (): Promise<BrandingConfig> => {
    return apiClient.post('/api/v1/branding/reset')
  },

  /**
   * Get current UI theme settings
   * GET /api/v1/branding/theme
   */
  getTheme: async (): Promise<UITheme> => {
    return apiClient.get('/api/v1/branding/theme')
  },

  /**
   * Update UI theme settings
   * PUT /api/v1/branding/theme
   */
  updateTheme: async (theme: UITheme): Promise<UITheme> => {
    return apiClient.put('/api/v1/branding/theme', theme)
  },

  /**
   * Set default theme mode (light, dark, or system)
   * PUT /api/v1/branding/theme/mode
   */
  setThemeMode: async (mode: ThemeMode): Promise<UITheme> => {
    return apiClient.put('/api/v1/branding/theme/mode', { mode })
  },

  /**
   * Get service provider branding
   * GET /api/v1/branding/provider
   */
  getProvider: async (): Promise<ServiceProviderBranding | null> => {
    return apiClient.get('/api/v1/branding/provider')
  },

  /**
   * Update service provider branding
   * PUT /api/v1/branding/provider
   */
  updateProvider: async (provider: ServiceProviderBranding): Promise<BrandingConfig> => {
    return apiClient.put('/api/v1/branding/provider', provider)
  },

  /**
   * Remove service provider branding
   * DELETE /api/v1/branding/provider
   */
  deleteProvider: async (): Promise<BrandingConfig> => {
    return apiClient.delete('/api/v1/branding/provider')
  },

  /**
   * Get client branding
   * GET /api/v1/branding/client
   */
  getClient: async (): Promise<ClientBranding | null> => {
    return apiClient.get('/api/v1/branding/client')
  },

  /**
   * Update client branding
   * PUT /api/v1/branding/client
   */
  updateClient: async (client: ClientBranding): Promise<BrandingConfig> => {
    return apiClient.put('/api/v1/branding/client', client)
  },

  /**
   * Remove client branding
   * DELETE /api/v1/branding/client
   */
  deleteClient: async (): Promise<BrandingConfig> => {
    return apiClient.delete('/api/v1/branding/client')
  },

  updateReport: async (report: ReportBranding): Promise<BrandingConfig> => {
    return apiClient.put('/api/v1/branding/report', { report })
  },
}