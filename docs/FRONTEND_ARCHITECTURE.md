# Frontend Architecture - Cribl Health Check Web GUI

**Status**: Design Phase
**Last Updated**: 2025-12-19
**Target Stack**: React 18 + Vite + TypeScript

---

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Component Architecture](#component-architecture)
5. [State Management](#state-management)
6. [Routing](#routing)
7. [API Integration](#api-integration)
8. [Styling](#styling)
9. [Testing Strategy](#testing-strategy)
10. [Development Workflow](#development-workflow)

---

## Overview

The Cribl Health Check Web GUI is a modern React-based single-page application (SPA) that provides a user-friendly interface for managing Cribl deployments, running health check analyses, and viewing results.

### Key Features

- **Credential Management**: Add, edit, test, and delete deployment credentials
- **Analysis Dashboard**: Run health checks with real-time progress updates
- **Results Viewer**: Interactive findings table with filtering and sorting
- **WebSocket Integration**: Live updates during analysis execution
- **Responsive Design**: Works on desktop and tablet devices

### Design Principles

- **Performance First**: Target < 2s initial load, < 100ms interaction response
- **Type Safety**: Full TypeScript coverage for all components and API calls
- **Accessibility**: WCAG 2.1 AA compliance
- **Progressive Enhancement**: Core functionality works without JavaScript
- **Offline Resilience**: Graceful degradation when API is unavailable

---

## Technology Stack

### Core Framework

- **React 18.3+**: UI library with concurrent features
- **Vite 5+**: Build tool and dev server
- **TypeScript 5+**: Type-safe JavaScript

### State Management

- **TanStack Query v5**: Server state management, caching, and synchronization
  - Automatic background refetching
  - Optimistic updates
  - Request deduplication
  - Cache invalidation

### Routing

- **React Router v6**: Client-side routing
  - Nested routes
  - Route loaders for data fetching
  - Protected routes for future auth

### Styling

- **Tailwind CSS 3+**: Utility-first CSS framework
- **Headless UI**: Unstyled, accessible components
- **Heroicons**: SVG icon library

### HTTP Client

- **Axios**: Promise-based HTTP client
  - Request/response interceptors
  - Automatic retries
  - Timeout handling

### WebSocket Client

- **Native WebSocket API**: For real-time analysis updates
- **Custom hook**: `useAnalysisWebSocket()` for state management

### Development Tools

- **ESLint**: Code linting
- **Prettier**: Code formatting
- **Vitest**: Unit testing
- **Playwright**: E2E testing

---

## Project Structure

```
frontend/
├── public/                  # Static assets
│   ├── favicon.ico
│   └── logo.svg
├── src/
│   ├── api/                # API client and types
│   │   ├── client.ts       # Axios instance with interceptors
│   │   ├── types.ts        # TypeScript interfaces matching API
│   │   ├── credentials.ts  # Credential endpoints
│   │   ├── analyzers.ts    # Analyzer endpoints
│   │   ├── analysis.ts     # Analysis endpoints
│   │   └── websocket.ts    # WebSocket client
│   │
│   ├── components/         # Reusable components
│   │   ├── common/         # Generic UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Toast.tsx
│   │   │   └── Spinner.tsx
│   │   │
│   │   ├── layout/         # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Footer.tsx
│   │   │
│   │   ├── credentials/    # Credential-specific
│   │   │   ├── CredentialList.tsx
│   │   │   ├── CredentialForm.tsx
│   │   │   ├── CredentialCard.tsx
│   │   │   └── ConnectionTest.tsx
│   │   │
│   │   ├── analysis/       # Analysis-specific
│   │   │   ├── AnalysisForm.tsx
│   │   │   ├── AnalysisList.tsx
│   │   │   ├── AnalysisCard.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   └── LiveUpdates.tsx
│   │   │
│   │   └── findings/       # Findings-specific
│   │       ├── FindingsTable.tsx
│   │       ├── FindingDetail.tsx
│   │       ├── SeverityBadge.tsx
│   │       └── FindingFilters.tsx
│   │
│   ├── pages/              # Route pages
│   │   ├── Dashboard.tsx   # Main landing page
│   │   ├── Credentials.tsx # Credential management
│   │   ├── Analysis.tsx    # Run analysis
│   │   ├── Results.tsx     # View results
│   │   └── NotFound.tsx    # 404 page
│   │
│   ├── hooks/              # Custom React hooks
│   │   ├── useCredentials.ts
│   │   ├── useAnalyzers.ts
│   │   ├── useAnalysis.ts
│   │   ├── useAnalysisWebSocket.ts
│   │   └── useToast.ts
│   │
│   ├── utils/              # Utility functions
│   │   ├── formatters.ts   # Date, number formatting
│   │   ├── validators.ts   # Form validation
│   │   └── constants.ts    # App constants
│   │
│   ├── types/              # Global TypeScript types
│   │   └── index.ts
│   │
│   ├── App.tsx             # Root component
│   ├── main.tsx            # Entry point
│   └── index.css           # Global styles
│
├── .env.example            # Environment variables template
├── .eslintrc.cjs           # ESLint configuration
├── .prettierrc             # Prettier configuration
├── index.html              # HTML template
├── package.json            # Dependencies
├── tsconfig.json           # TypeScript configuration
├── vite.config.ts          # Vite configuration
└── README.md               # Frontend README
```

---

## Component Architecture

### Design Patterns

1. **Container/Presenter Pattern**
   - Container components handle data fetching and state
   - Presenter components focus on rendering UI

2. **Composition Over Inheritance**
   - Small, reusable components
   - Props for customization

3. **Controlled Components**
   - Forms use controlled inputs
   - Single source of truth

### Component Hierarchy

```
App
├── Layout
│   ├── Header
│   │   └── Navigation
│   ├── Sidebar (optional)
│   └── Footer
│
└── Router
    ├── Dashboard Page
    │   ├── QuickStats
    │   ├── RecentAnalyses
    │   └── CredentialStatus
    │
    ├── Credentials Page
    │   ├── CredentialList
    │   │   └── CredentialCard[]
    │   │       ├── ConnectionTest
    │   │       └── Actions (Edit/Delete)
    │   └── CredentialForm (Modal)
    │       ├── BearerTokenFields
    │       └── OAuthFields
    │
    ├── Analysis Page
    │   ├── AnalysisForm
    │   │   ├── DeploymentSelect
    │   │   └── AnalyzerCheckboxes
    │   ├── AnalysisList
    │   │   └── AnalysisCard[]
    │   │       ├── ProgressBar
    │   │       └── LiveUpdates (WebSocket)
    │   └── ActiveAnalysis (if running)
    │       ├── ProgressBar
    │       ├── LiveFindings
    │       └── CancelButton
    │
    └── Results Page
        ├── ResultsSummary
        │   ├── HealthScore
        │   └── Statistics
        ├── FindingsTable
        │   ├── FindingFilters
        │   ├── SortControls
        │   └── FindingRow[]
        │       └── SeverityBadge
        └── FindingDetail (Modal)
            ├── Description
            ├── RemediationSteps
            └── Metadata
```

---

## State Management

### TanStack Query Strategy

```typescript
// Query keys for cache management
const queryKeys = {
  credentials: ['credentials'] as const,
  credential: (name: string) => ['credentials', name] as const,

  analyzers: ['analyzers'] as const,
  analyzer: (name: string) => ['analyzers', name] as const,

  analyses: ['analyses'] as const,
  analysis: (id: string) => ['analyses', id] as const,
  analysisResults: (id: string) => ['analyses', id, 'results'] as const,
}

// Example: Fetch credentials with auto-refetch
const { data: credentials, isLoading, error } = useQuery({
  queryKey: queryKeys.credentials,
  queryFn: fetchCredentials,
  refetchInterval: 30000, // Refetch every 30s
  staleTime: 10000,       // Consider stale after 10s
})

// Example: Create credential with optimistic update
const createCredentialMutation = useMutation({
  mutationFn: createCredential,
  onMutate: async (newCredential) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries({ queryKey: queryKeys.credentials })

    // Snapshot previous value
    const previousCredentials = queryClient.getQueryData(queryKeys.credentials)

    // Optimistically update
    queryClient.setQueryData(queryKeys.credentials, (old) => [...old, newCredential])

    return { previousCredentials }
  },
  onError: (err, newCredential, context) => {
    // Rollback on error
    queryClient.setQueryData(queryKeys.credentials, context.previousCredentials)
  },
  onSettled: () => {
    // Refetch to sync with server
    queryClient.invalidateQueries({ queryKey: queryKeys.credentials })
  },
})
```

### Local State (React useState/useReducer)

- Form inputs
- UI toggles (modals, dropdowns)
- Ephemeral state (hover, focus)

### WebSocket State

```typescript
// Custom hook for analysis WebSocket
function useAnalysisWebSocket(analysisId: string) {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')
  const [messages, setMessages] = useState<WebSocketMessage[]>([])
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8080/api/v1/analysis/ws/${analysisId}`)

    ws.onopen = () => setStatus('connected')
    ws.onclose = () => setStatus('disconnected')

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      setLastMessage(message)
      setMessages(prev => [...prev, message])

      // Invalidate queries on completion
      if (message.type === 'complete') {
        queryClient.invalidateQueries({
          queryKey: queryKeys.analysisResults(analysisId)
        })
      }
    }

    return () => ws.close()
  }, [analysisId])

  return { status, messages, lastMessage }
}
```

---

## Routing

### Route Structure

```typescript
const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: 'credentials',
        element: <Credentials />,
      },
      {
        path: 'analysis',
        children: [
          {
            index: true,
            element: <Analysis />,
          },
          {
            path: ':analysisId/results',
            element: <Results />,
            loader: async ({ params }) => {
              // Pre-fetch results
              return queryClient.ensureQueryData({
                queryKey: queryKeys.analysisResults(params.analysisId),
                queryFn: () => fetchAnalysisResults(params.analysisId),
              })
            },
          },
        ],
      },
      {
        path: '*',
        element: <NotFound />,
      },
    ],
  },
])
```

### Navigation Flow

```
Dashboard
  ├─> Credentials → Add/Edit Credential → Test Connection
  ├─> Analysis → Start Analysis → View Live Progress → Results
  └─> Recent Results → View Results → Finding Details
```

---

## API Integration

### Type Definitions

```typescript
// src/api/types.ts

// Credentials
export interface Credential {
  name: string
  url: string
  auth_type: 'bearer' | 'oauth'
  has_token: boolean
  has_oauth: boolean
  client_id?: string
}

export interface CredentialCreate {
  name: string
  url: string
  auth_type: 'bearer' | 'oauth'
  token?: string
  client_id?: string
  client_secret?: string
}

export interface ConnectionTestResult {
  success: boolean
  message: string
  cribl_version?: string
  response_time_ms?: number
  error?: string
}

// Analyzers
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

// Analysis
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
  started_at?: string
  completed_at?: string
  analyzers: string[]
  progress_percent: number
  current_step?: string
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
  health_score?: number
  findings_count: number
  findings: Finding[]
  recommendations_count: number
  completed_at?: string
  duration_seconds?: number
}

// WebSocket Messages
export type WebSocketMessageType =
  | 'status'
  | 'progress'
  | 'finding'
  | 'complete'
  | 'error'
  | 'keepalive'
  | 'pong'

export interface WebSocketMessage {
  type: WebSocketMessageType
  analysis_id?: string
  status?: AnalysisStatus
  percent?: number
  step?: string
  finding?: Finding
  health_score?: number
  error?: string
}
```

### API Client

```typescript
// src/api/client.ts
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Future: Add auth token
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // Global error handling
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)
```

### API Modules

```typescript
// src/api/credentials.ts
import { apiClient } from './client'
import type { Credential, CredentialCreate, ConnectionTestResult } from './types'

export const credentialsApi = {
  list: () =>
    apiClient.get<Credential[]>('/api/v1/credentials'),

  get: (name: string) =>
    apiClient.get<Credential>(`/api/v1/credentials/${name}`),

  create: (data: CredentialCreate) =>
    apiClient.post<Credential>('/api/v1/credentials', data),

  update: (name: string, data: Partial<CredentialCreate>) =>
    apiClient.put<Credential>(`/api/v1/credentials/${name}`, data),

  delete: (name: string) =>
    apiClient.delete(`/api/v1/credentials/${name}`),

  test: (name: string) =>
    apiClient.post<ConnectionTestResult>(`/api/v1/credentials/${name}/test`),
}

// src/api/analysis.ts
import { apiClient } from './client'
import type {
  AnalysisRequest,
  AnalysisResponse,
  AnalysisResultResponse
} from './types'

export const analysisApi = {
  list: () =>
    apiClient.get<AnalysisResponse[]>('/api/v1/analysis'),

  get: (id: string) =>
    apiClient.get<AnalysisResponse>(`/api/v1/analysis/${id}`),

  getResults: (id: string) =>
    apiClient.get<AnalysisResultResponse>(`/api/v1/analysis/${id}/results`),

  start: (data: AnalysisRequest) =>
    apiClient.post<AnalysisResponse>('/api/v1/analysis', data),

  delete: (id: string) =>
    apiClient.delete(`/api/v1/analysis/${id}`),
}
```

---

## Styling

### Tailwind CSS Configuration

```javascript
// tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Cribl brand colors
        cribl: {
          primary: '#00A3E0',
          secondary: '#0066A1',
          accent: '#FFB81C',
        },
        // Severity colors
        severity: {
          critical: '#DC2626', // red-600
          high: '#EA580C',     // orange-600
          medium: '#F59E0B',   // amber-500
          low: '#3B82F6',      // blue-500
          info: '#6B7280',     // gray-500
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
```

### Component Styling Example

```tsx
// Severity badge component
export function SeverityBadge({ severity }: { severity: Finding['severity'] }) {
  const colors = {
    critical: 'bg-severity-critical text-white',
    high: 'bg-severity-high text-white',
    medium: 'bg-severity-medium text-white',
    low: 'bg-severity-low text-white',
    info: 'bg-severity-info text-white',
  }

  return (
    <span className={`
      inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
      ${colors[severity]}
    `}>
      {severity.toUpperCase()}
    </span>
  )
}
```

---

## Testing Strategy

### Unit Tests (Vitest)

```typescript
// src/components/common/__tests__/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Button } from '../Button'

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    fireEvent.click(screen.getByText('Click me'))
    expect(handleClick).toHaveBeenCalledOnce()
  })

  it('is disabled when loading', () => {
    render(<Button loading>Click me</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })
})
```

### Integration Tests (React Testing Library)

```typescript
// src/pages/__tests__/Credentials.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Credentials } from '../Credentials'
import { credentialsApi } from '@/api/credentials'

vi.mock('@/api/credentials')

describe('Credentials Page', () => {
  it('displays credential list', async () => {
    vi.mocked(credentialsApi.list).mockResolvedValue([
      { name: 'prod', url: 'https://example.com', auth_type: 'bearer', has_token: true, has_oauth: false },
    ])

    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <Credentials />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('prod')).toBeInTheDocument()
    })
  })
})
```

### E2E Tests (Playwright)

```typescript
// tests/e2e/analysis.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Analysis Flow', () => {
  test('should run analysis and view results', async ({ page }) => {
    // Navigate to analysis page
    await page.goto('/analysis')

    // Select deployment
    await page.selectOption('[data-testid="deployment-select"]', 'prod')

    // Select analyzers
    await page.check('[data-testid="analyzer-health"]')

    // Start analysis
    await page.click('[data-testid="start-analysis-btn"]')

    // Wait for completion
    await expect(page.locator('[data-testid="analysis-status"]')).toHaveText('completed', { timeout: 60000 })

    // View results
    await page.click('[data-testid="view-results-btn"]')

    // Verify results page
    await expect(page).toHaveURL(/\/analysis\/.*\/results/)
    await expect(page.locator('[data-testid="findings-table"]')).toBeVisible()
  })
})
```

---

## Development Workflow

### Setup

```bash
# Install dependencies
cd frontend
npm install

# Start dev server
npm run dev

# Run tests
npm run test

# Run E2E tests
npm run test:e2e

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8080

# .env.production
VITE_API_BASE_URL=/
```

### Code Quality

```bash
# Lint
npm run lint

# Format
npm run format

# Type check
npm run type-check
```

---

## Performance Targets

- **Initial Load**: < 2 seconds (3G connection)
- **Time to Interactive**: < 3 seconds
- **First Contentful Paint**: < 1 second
- **Largest Contentful Paint**: < 2.5 seconds
- **Cumulative Layout Shift**: < 0.1
- **Bundle Size**: < 300 KB (gzipped)

### Optimization Strategies

1. **Code Splitting**: Route-based lazy loading
2. **Tree Shaking**: Remove unused code
3. **Image Optimization**: WebP format, lazy loading
4. **Caching**: Service worker for offline support (future)
5. **CDN**: Static asset delivery
6. **Compression**: Gzip/Brotli

---

## Accessibility

### WCAG 2.1 AA Compliance

- **Keyboard Navigation**: All interactive elements accessible via keyboard
- **Screen Reader Support**: Semantic HTML, ARIA labels
- **Color Contrast**: Minimum 4.5:1 for text
- **Focus Indicators**: Visible focus states
- **Error Messages**: Clear, actionable error messages
- **Form Labels**: Proper label associations

### Testing Tools

- **axe DevTools**: Automated accessibility testing
- **NVDA/JAWS**: Screen reader testing
- **Lighthouse**: Accessibility audits

---

## Next Steps

1. **Install Node.js** (user task)
2. **Initialize Vite project** with React + TypeScript template
3. **Install dependencies** (TanStack Query, React Router, Tailwind CSS, etc.)
4. **Implement API client layer**
5. **Build credential management UI**
6. **Build analysis dashboard**
7. **Build results viewer**
8. **Integration testing**
9. **Production deployment**

---

**Ready for implementation once Node.js is installed!**
