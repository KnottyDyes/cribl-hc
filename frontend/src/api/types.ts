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

// ============================================================================
// Analyzers
// ============================================================================

export interface Analyzer {
  name: string
  description: string
  api_calls: number
  permissions: string[]
  categories: string[]
}

export interface AnalyzersListResponse {
  analyzers: Analyzer[]
  total_count: number
  total_api_calls: number
}

// ============================================================================
// Analysis
// ============================================================================

export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface AnalysisRequest {
  deployment_name: string
  analyzers?: string[]
}

export interface AnalysisResponse {
  analysis_id: string
  deployment_name: string
  status: AnalysisStatus
  created_at: string
  started_at: string | null
  completed_at: string | null
  analyzers: string[]
  progress_percent: number
  current_step: string | null
  api_calls_used: number
}

export interface Finding {
  id: string
  category: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  title: string
  description: string
  affected_components: string[]
  remediation_steps: string[]
  documentation_links: string[]
  estimated_impact: string
  confidence_level: 'high' | 'medium' | 'low'
  detected_at: string
  metadata: Record<string, any>
}

export interface AnalysisResultResponse {
  analysis_id: string
  deployment_name: string
  status: AnalysisStatus
  health_score: number | null
  findings_count: number
  findings: Finding[]
  recommendations_count: number
  completed_at: string | null
  duration_seconds: number | null
}

// ============================================================================
// System
// ============================================================================

export interface VersionResponse {
  version: string
  api_version: string
  features: {
    oauth_auth: boolean
    bearer_auth: boolean
    websocket_updates: boolean
    real_time_analysis: boolean
  }
}

export interface HealthResponse {
  status: string
  version: string
  service: string
}

// ============================================================================
// WebSocket
// ============================================================================

export type WebSocketMessageType =
  | 'status'
  | 'progress'
  | 'finding'
  | 'complete'
  | 'error'
  | 'keepalive'
  | 'pong'

export interface WebSocketStatusMessage {
  type: 'status'
  analysis_id: string
  status: AnalysisStatus
}

export interface WebSocketProgressMessage {
  type: 'progress'
  percent: number
  step: string
}

export interface WebSocketFindingMessage {
  type: 'finding'
  finding: Finding
}

export interface WebSocketCompleteMessage {
  type: 'complete'
  analysis_id: string
  health_score: number | null
}

export interface WebSocketErrorMessage {
  type: 'error'
  analysis_id: string
  error: string
}

export interface WebSocketKeepaliveMessage {
  type: 'keepalive'
}

export interface WebSocketPongMessage {
  type: 'pong'
}

export type WebSocketMessage =
  | WebSocketStatusMessage
  | WebSocketProgressMessage
  | WebSocketFindingMessage
  | WebSocketCompleteMessage
  | WebSocketErrorMessage
  | WebSocketKeepaliveMessage
  | WebSocketPongMessage

// ============================================================================
// API Error
// ============================================================================

export interface APIError {
  detail: string
}
