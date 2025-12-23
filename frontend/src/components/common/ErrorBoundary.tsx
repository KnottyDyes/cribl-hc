import { Component, ErrorInfo, ReactNode } from 'react'
import { Button } from './Button'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

/**
 * Error Boundary component to catch and handle React errors gracefully.
 * Prevents the entire app from crashing when a component throws an error.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details for debugging
    console.error('Error Boundary caught an error:', error, errorInfo)

    this.setState({
      error,
      errorInfo,
    })

    // TODO: Send error to monitoring service (e.g., Sentry)
    // logErrorToService(error, errorInfo)
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Default error UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
            <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 rounded-full">
              <svg
                className="w-6 h-6 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>

            <h2 className="mt-6 text-center text-2xl font-bold text-gray-900">
              Something went wrong
            </h2>

            <p className="mt-2 text-center text-sm text-gray-600">
              We're sorry for the inconvenience. An unexpected error occurred.
            </p>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mt-4 p-4 bg-gray-50 rounded border border-gray-200">
                <summary className="cursor-pointer font-medium text-sm text-gray-700">
                  Error Details (Development Only)
                </summary>
                <div className="mt-2 text-xs">
                  <p className="font-mono text-red-600 break-all">
                    {this.state.error.toString()}
                  </p>
                  {this.state.errorInfo && (
                    <pre className="mt-2 overflow-auto text-gray-600">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              </details>
            )}

            <div className="mt-6 flex gap-3">
              <Button
                onClick={this.handleReset}
                className="flex-1"
                variant="primary"
              >
                Try Again
              </Button>
              <Button
                onClick={() => window.location.href = '/'}
                className="flex-1"
                variant="secondary"
              >
                Go Home
              </Button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
