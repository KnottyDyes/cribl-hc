/**
 * API type definitions matching the FastAPI backend
 */

// ============================================================================
// Credentials
// ============================================================================

export type AuthType = 'bearer' | 'oauth'

export interface Credential {
  name: string
  url: string
  auth_type: AuthType
  has_token: boolean
  has_oauth: boolean
  client_id?: string | null
}

export interface CredentialCreate {
  name: string
  url: string
  auth_type: AuthType
  token?: string
  client_id?: string
  client_secret?: string
}

export interface CredentialUpdate {
  url?: string
  auth_type?: AuthType
  token?: string
  client_id?: string
  client_secret?: string
}

export interface ConnectionTestResult {
  success: boolean
  message: string
  cribl_version?: string | null
  response_time_ms?: number | null
  error?: string | null
}
