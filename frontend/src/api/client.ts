import axios from 'axios'
import type { AxiosError } from 'axios'
import { getBackendUrl } from '../utils/tauri'

// Base URL will be set dynamically
let API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

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
 * Initialize the API client with the correct backend URL
 * Must be called before making any API requests
 */
export const initializeApiClient = async () => {
  try {
    API_BASE_URL = await getBackendUrl()
    apiClient.defaults.baseURL = API_BASE_URL
    console.log('API client initialized with baseURL:', API_BASE_URL)
  } catch (error) {
    console.error('Failed to initialize API client:', error)
  }
}

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
