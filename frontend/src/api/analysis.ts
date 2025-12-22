import { apiClient } from './client'
import type {
  AnalysisRequest,
  AnalysisResponse,
  AnalysisResultResponse,
} from './types'

/**
 * Analysis execution API endpoints
 */
export const analysisApi = {
  /**
   * List all analyses
   * GET /api/v1/analysis
   */
  list: async (): Promise<AnalysisResponse[]> => {
    return apiClient.get('/api/v1/analysis')
  },

  /**
   * Get analysis status and metadata
   * GET /api/v1/analysis/{id}
   */
  get: async (id: string): Promise<AnalysisResponse> => {
    return apiClient.get(`/api/v1/analysis/${id}`)
  },

  /**
   * Get full analysis results
   * GET /api/v1/analysis/{id}/results
   */
  getResults: async (id: string): Promise<AnalysisResultResponse> => {
    return apiClient.get(`/api/v1/analysis/${id}/results`)
  },

  /**
   * Start a new analysis
   * POST /api/v1/analysis
   */
  start: async (data: AnalysisRequest): Promise<AnalysisResponse> => {
    return apiClient.post('/api/v1/analysis', data)
  },

  /**
   * Delete an analysis
   * DELETE /api/v1/analysis/{id}
   */
  delete: async (id: string): Promise<void> => {
    return apiClient.delete(`/api/v1/analysis/${id}`)
  },
}
