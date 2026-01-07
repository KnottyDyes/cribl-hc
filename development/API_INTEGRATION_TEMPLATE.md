# API Integration Layer - TypeScript Templates

**Purpose**: Ready-to-use TypeScript code for integrating with the Cribl Health Check API
**Status**: Ready for copy-paste into React frontend

---

## File Structure

```
frontend/src/api/
├── client.ts          # Axios instance
├── types.ts           # TypeScript interfaces
├── credentials.ts     # Credential endpoints
├── analyzers.ts       # Analyzer endpoints
├── analysis.ts        # Analysis endpoints
└── websocket.ts       # WebSocket client
```

---

## 1. API Types (`src/api/types.ts`)

```typescript
/**
 * API type definitions matching the FastAPI backend
 * Generated from: http://localhost:8080/api/openapi.json
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
```

---

## 2. API Client (`src/api/client.ts`)

```typescript
import axios, { AxiosInstance, AxiosError } from 'axios'

// Base URL from environment or default to localhost
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

/**
 * Axios instance configured for the Cribl Health Check API
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Request interceptor
 * Future: Add authentication token
 */
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token when implemented
    // const token = localStorage.getItem('auth_token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * Response interceptor
 * Unwrap response data and handle errors
 */
apiClient.interceptors.response.use(
  (response) => {
    // Unwrap data from response
    return response.data
  },
  (error: AxiosError) => {
    // Global error handling
    if (error.response) {
      // Server responded with error
      console.error('API Error:', error.response.status, error.response.data)
    } else if (error.request) {
      // Request made but no response
      console.error('Network Error: No response received')
    } else {
      // Error setting up request
      console.error('Request Error:', error.message)
    }
    return Promise.reject(error)
  }
)
```

---

## 3. Credentials API (`src/api/credentials.ts`)

```typescript
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
```

---

## 4. Analyzers API (`src/api/analyzers.ts`)

```typescript
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
```

---

## 5. Analysis API (`src/api/analysis.ts`)

```typescript
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
```

---

## 6. WebSocket Client (`src/api/websocket.ts`)

```typescript
import type { WebSocketMessage } from './types'

// WebSocket URL from environment or default to localhost
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8080'

export interface WebSocketOptions {
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
  onMessage?: (message: WebSocketMessage) => void
  reconnect?: boolean
  reconnectDelay?: number
  maxReconnectAttempts?: number
}

/**
 * WebSocket client for analysis live updates
 */
export class AnalysisWebSocket {
  private ws: WebSocket | null = null
  private analysisId: string
  private options: WebSocketOptions
  private reconnectAttempts = 0
  private shouldReconnect = true

  constructor(analysisId: string, options: WebSocketOptions = {}) {
    this.analysisId = analysisId
    this.options = {
      reconnect: true,
      reconnectDelay: 2000,
      maxReconnectAttempts: 5,
      ...options,
    }
  }

  /**
   * Connect to the WebSocket
   */
  connect(): void {
    const url = `${WS_BASE_URL}/api/v1/analysis/ws/${this.analysisId}`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log(`WebSocket connected: ${this.analysisId}`)
      this.reconnectAttempts = 0
      this.options.onOpen?.()
    }

    this.ws.onclose = () => {
      console.log(`WebSocket closed: ${this.analysisId}`)
      this.options.onClose?.()

      // Attempt reconnection
      if (
        this.shouldReconnect &&
        this.options.reconnect &&
        this.reconnectAttempts < (this.options.maxReconnectAttempts || 5)
      ) {
        this.reconnectAttempts++
        console.log(
          `Reconnecting (${this.reconnectAttempts}/${this.options.maxReconnectAttempts})...`
        )
        setTimeout(() => {
          this.connect()
        }, this.options.reconnectDelay)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      this.options.onError?.(error)
    }

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        this.options.onMessage?.(message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }
  }

  /**
   * Send a message (for ping/pong)
   */
  send(data: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(data)
    }
  }

  /**
   * Close the WebSocket connection
   */
  close(): void {
    this.shouldReconnect = false
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * Get the current connection state
   */
  getState(): number {
    return this.ws?.readyState || WebSocket.CLOSED
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}
```

---

## 7. System API (`src/api/system.ts`)

```typescript
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
```

---

## 8. React Hook Examples

### Custom Hook: `useCredentials`

```typescript
// src/hooks/useCredentials.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { credentialsApi } from '@/api/credentials'
import type { CredentialCreate, CredentialUpdate } from '@/api/types'

const QUERY_KEY = ['credentials']

export function useCredentials() {
  const queryClient = useQueryClient()

  // List credentials
  const { data: credentials, isLoading, error } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: credentialsApi.list,
    refetchInterval: 30000, // Refetch every 30s
  })

  // Create credential
  const createMutation = useMutation({
    mutationFn: credentialsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  // Update credential
  const updateMutation = useMutation({
    mutationFn: ({ name, data }: { name: string; data: CredentialUpdate }) =>
      credentialsApi.update(name, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  // Delete credential
  const deleteMutation = useMutation({
    mutationFn: credentialsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  // Test connection
  const testMutation = useMutation({
    mutationFn: credentialsApi.test,
  })

  return {
    credentials,
    isLoading,
    error,
    createCredential: createMutation.mutate,
    updateCredential: updateMutation.mutate,
    deleteCredential: deleteMutation.mutate,
    testConnection: testMutation.mutate,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isTesting: testMutation.isPending,
    testResult: testMutation.data,
  }
}
```

### Custom Hook: `useAnalysis`

```typescript
// src/hooks/useAnalysis.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { analysisApi } from '@/api/analysis'
import type { AnalysisRequest } from '@/api/types'

const QUERY_KEY = ['analyses']

export function useAnalysis(analysisId?: string) {
  const queryClient = useQueryClient()

  // List all analyses
  const { data: analyses, isLoading: isLoadingList } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: analysisApi.list,
    refetchInterval: 5000, // Poll every 5s for status updates
  })

  // Get specific analysis
  const { data: analysis, isLoading: isLoadingAnalysis } = useQuery({
    queryKey: [...QUERY_KEY, analysisId],
    queryFn: () => analysisApi.get(analysisId!),
    enabled: !!analysisId,
    refetchInterval: (query) => {
      // Poll every 2s if running, stop if completed/failed
      const status = query.state.data?.status
      return status === 'running' || status === 'pending' ? 2000 : false
    },
  })

  // Get analysis results
  const { data: results, isLoading: isLoadingResults } = useQuery({
    queryKey: [...QUERY_KEY, analysisId, 'results'],
    queryFn: () => analysisApi.getResults(analysisId!),
    enabled: !!analysisId && analysis?.status === 'completed',
  })

  // Start analysis
  const startMutation = useMutation({
    mutationFn: analysisApi.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  // Delete analysis
  const deleteMutation = useMutation({
    mutationFn: analysisApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  return {
    analyses,
    analysis,
    results,
    isLoading: isLoadingList || isLoadingAnalysis || isLoadingResults,
    startAnalysis: startMutation.mutate,
    deleteAnalysis: deleteMutation.mutate,
    isStarting: startMutation.isPending,
    isDeleting: deleteMutation.isPending,
  }
}
```

### Custom Hook: `useAnalysisWebSocket`

```typescript
// src/hooks/useAnalysisWebSocket.ts
import { useEffect, useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { AnalysisWebSocket } from '@/api/websocket'
import type { WebSocketMessage } from '@/api/types'

export function useAnalysisWebSocket(analysisId: string | undefined) {
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState<WebSocketMessage[]>([])
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const queryClient = useQueryClient()

  const handleMessage = useCallback((message: WebSocketMessage) => {
    setLastMessage(message)
    setMessages((prev) => [...prev, message])

    // Invalidate queries on completion
    if (message.type === 'complete') {
      queryClient.invalidateQueries({
        queryKey: ['analyses', analysisId, 'results'],
      })
      queryClient.invalidateQueries({
        queryKey: ['analyses', analysisId],
      })
    }
  }, [analysisId, queryClient])

  useEffect(() => {
    if (!analysisId) return

    const ws = new AnalysisWebSocket(analysisId, {
      onOpen: () => setIsConnected(true),
      onClose: () => setIsConnected(false),
      onMessage: handleMessage,
    })

    ws.connect()

    return () => {
      ws.close()
    }
  }, [analysisId, handleMessage])

  return {
    isConnected,
    messages,
    lastMessage,
  }
}
```

---

## Usage Examples

### Example 1: List Credentials

```tsx
import { useCredentials } from '@/hooks/useCredentials'

function CredentialsList() {
  const { credentials, isLoading, error } = useCredentials()

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error: {error.message}</div>

  return (
    <ul>
      {credentials?.map((cred) => (
        <li key={cred.name}>
          {cred.name} - {cred.url} ({cred.auth_type})
        </li>
      ))}
    </ul>
  )
}
```

### Example 2: Create Credential

```tsx
import { useState } from 'react'
import { useCredentials } from '@/hooks/useCredentials'

function CreateCredentialForm() {
  const { createCredential, isCreating } = useCredentials()
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    auth_type: 'bearer' as const,
    token: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createCredential(formData)
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Name"
        value={formData.name}
        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
      />
      <input
        type="url"
        placeholder="URL"
        value={formData.url}
        onChange={(e) => setFormData({ ...formData, url: e.target.value })}
      />
      <input
        type="password"
        placeholder="Token"
        value={formData.token}
        onChange={(e) => setFormData({ ...formData, token: e.target.value })}
      />
      <button type="submit" disabled={isCreating}>
        {isCreating ? 'Creating...' : 'Create'}
      </button>
    </form>
  )
}
```

### Example 3: Start Analysis with WebSocket

```tsx
import { useState } from 'react'
import { useAnalysis } from '@/hooks/useAnalysis'
import { useAnalysisWebSocket } from '@/hooks/useAnalysisWebSocket'

function AnalysisRunner() {
  const { startAnalysis, isStarting } = useAnalysis()
  const [currentAnalysisId, setCurrentAnalysisId] = useState<string>()
  const { isConnected, lastMessage } = useAnalysisWebSocket(currentAnalysisId)

  const handleStart = () => {
    startAnalysis(
      { deployment_name: 'prod', analyzers: ['health'] },
      {
        onSuccess: (response) => {
          setCurrentAnalysisId(response.analysis_id)
        },
      }
    )
  }

  return (
    <div>
      <button onClick={handleStart} disabled={isStarting}>
        Start Analysis
      </button>

      {currentAnalysisId && (
        <div>
          <p>Analysis ID: {currentAnalysisId}</p>
          <p>WebSocket: {isConnected ? 'Connected' : 'Disconnected'}</p>
          {lastMessage?.type === 'progress' && (
            <p>Progress: {lastMessage.percent}%</p>
          )}
          {lastMessage?.type === 'complete' && (
            <p>Complete! Health Score: {lastMessage.health_score}</p>
          )}
        </div>
      )}
    </div>
  )
}
```

---

**All TypeScript templates are ready to copy-paste into your React project!**
