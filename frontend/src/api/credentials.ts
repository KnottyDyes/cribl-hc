import { apiClient } from './client'
import type {
  Credential,
  CredentialCreate,
  CredentialUpdate,
  ConnectionTestResult,
} from './types'

/**
 * Credential management API endpoints
 */
export const credentialsApi = {
  /**
   * List all credentials
   * GET /api/v1/credentials
   */
  list: async (): Promise<Credential[]> => {
    return apiClient.get('/api/v1/credentials')
  },

  /**
   * Get a specific credential
   * GET /api/v1/credentials/{name}
   */
  get: async (name: string): Promise<Credential> => {
    return apiClient.get(`/api/v1/credentials/${name}`)
  },

  /**
   * Create a new credential
   * POST /api/v1/credentials
   */
  create: async (data: CredentialCreate): Promise<Credential> => {
    return apiClient.post('/api/v1/credentials', data)
  },

  /**
   * Update an existing credential
   * PUT /api/v1/credentials/{name}
   */
  update: async (name: string, data: CredentialUpdate): Promise<Credential> => {
    return apiClient.put(`/api/v1/credentials/${name}`, data)
  },

  /**
   * Delete a credential
   * DELETE /api/v1/credentials/{name}
   */
  delete: async (name: string): Promise<void> => {
    return apiClient.delete(`/api/v1/credentials/${name}`)
  },

  /**
   * Test connection to a deployment
   * POST /api/v1/credentials/{name}/test
   */
  test: async (name: string): Promise<ConnectionTestResult> => {
    return apiClient.post(`/api/v1/credentials/${name}/test`)
  },
}
