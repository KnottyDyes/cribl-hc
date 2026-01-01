/**
 * Tauri integration utilities
 * Handles communication with the Rust backend wrapper
 */

// Check if running in Tauri
export const isTauri = () => {
  return '__TAURI__' in window;
};

/**
 * Get the backend URL from Tauri
 * In Tauri mode, the backend URL is provided by the Rust wrapper
 * In web mode, use the environment variable
 */
export const getBackendUrl = async (): Promise<string> => {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const url = await invoke<string>('get_backend_url');
      return url;
    } catch (error) {
      console.error('Failed to get backend URL from Tauri:', error);
      // Fallback to default port in dev mode
      return 'http://localhost:8080';
    }
  } else {
    // Web mode - use environment variable
    return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';
  }
};
