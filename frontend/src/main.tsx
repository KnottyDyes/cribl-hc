import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import './index.css'
import App from './App.tsx'
import { initializeApiClient } from './api/client'

// Create a client with optimized caching strategy
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Don't refetch on window focus by default (opt-in per query)
      refetchOnWindowFocus: false,
      // Retry failed requests once
      retry: 1,
      // Consider data stale after 30 seconds (will still show cached data but refetch in background)
      staleTime: 30 * 1000,
      // Keep unused data in cache for 5 minutes
      gcTime: 5 * 60 * 1000,
    },
    mutations: {
      // Retry mutations once on network errors
      retry: 1,
    },
  },
})

// Initialize API client with correct backend URL (from Tauri or env)
initializeApiClient().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
        {/* React Query Devtools - only included in development builds */}
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </StrictMode>,
  )
})
