import axios from 'axios'
import type { AxiosError } from 'axios'

// Base URL from environment or default to localhost
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

/**
 * Axios instance configured for the Cribl Health Check API
 */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Request interceptor
 */
apiClient.interceptors.request.use(
  (config) => {
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
      console.error('API Error:', error.response.status, error.response.data)
    } else if (error.request) {
      console.error('Network Error: No response received')
    } else {
      console.error('Request Error:', error.message)
    }
    return Promise.reject(error)
  }
)
