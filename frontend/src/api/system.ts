import { apiClient } from './client'
import type { VersionResponse, HealthResponse } from './types'

/**
 * System information API endpoints
 */
export const systemApi = {
  /**
   * Get API version and features
   * GET /api/v1/version
   */
  getVersion: async (): Promise<VersionResponse> => {
    return apiClient.get('/api/v1/version')
  },

  /**
   * Get health status
   * GET /health
   */
  getHealth: async (): Promise<HealthResponse> => {
    return apiClient.get('/health')
  },
}
