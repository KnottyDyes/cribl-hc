import { apiClient } from './client'
import type { Analyzer, AnalyzersListResponse } from './types'

/**
 * Analyzer metadata API endpoints
 */
export const analyzersApi = {
  /**
   * List all available analyzers
   * GET /api/v1/analyzers
   */
  list: async (): Promise<AnalyzersListResponse> => {
    return apiClient.get('/api/v1/analyzers')
  },

  /**
   * Get details about a specific analyzer
   * GET /api/v1/analyzers/{name}
   */
  get: async (name: string): Promise<Analyzer> => {
    return apiClient.get(`/api/v1/analyzers/${name}`)
  },
}
