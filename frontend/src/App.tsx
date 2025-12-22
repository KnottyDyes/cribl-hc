import { useQuery } from '@tanstack/react-query'
import { systemApi } from './api/system'
import { credentialsApi } from './api/credentials'
import { analyzersApi } from './api/analyzers'

function App() {
  // Fetch system version
  const { data: version, isLoading: versionLoading, error: versionError } = useQuery({
    queryKey: ['version'],
    queryFn: systemApi.getVersion,
  })

  // Fetch credentials
  const { data: credentials, isLoading: credsLoading } = useQuery({
    queryKey: ['credentials'],
    queryFn: credentialsApi.list,
  })

  // Fetch analyzers
  const { data: analyzers, isLoading: analyzersLoading } = useQuery({
    queryKey: ['analyzers'],
    queryFn: analyzersApi.list,
  })

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Cribl Health Check
          </h1>
          <p className="text-gray-600">Web GUI - Phase 2 Frontend</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* API Version Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-900">
              API Version
            </h2>
            {versionLoading && (
              <div className="text-gray-500">Loading...</div>
            )}
            {versionError && (
              <div className="text-red-600">
                Error: API not reachable. Make sure the backend is running on
                port 8080.
              </div>
            )}
            {version && (
              <div className="space-y-2">
                <div className="flex items-center">
                  <span className="w-3 h-3 bg-green-500 rounded-full mr-2"></span>
                  <span className="text-green-700 font-medium">Connected</span>
                </div>
                <div className="text-sm text-gray-600">
                  <div>
                    <strong>Version:</strong> {version.version}
                  </div>
                  <div>
                    <strong>API:</strong> {version.api_version}
                  </div>
                </div>
                <div className="mt-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">
                    Features:
                  </h3>
                  <ul className="text-xs space-y-1">
                    {Object.entries(version.features).map(([key, value]) => (
                      <li key={key} className="flex items-center">
                        <span
                          className={`w-2 h-2 rounded-full mr-2 ${
                            value ? 'bg-green-500' : 'bg-gray-300'
                          }`}
                        ></span>
                        {key}: {value ? 'Yes' : 'No'}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Credentials Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-900">
              Credentials
            </h2>
            {credsLoading && (
              <div className="text-gray-500">Loading...</div>
            )}
            {credentials && (
              <div className="space-y-2">
                <div className="text-2xl font-bold text-blue-600">
                  {credentials.length}
                </div>
                <div className="text-sm text-gray-600">
                  {credentials.length === 0
                    ? 'No credentials configured'
                    : credentials.length === 1
                    ? '1 deployment configured'
                    : `${credentials.length} deployments configured`}
                </div>
                {credentials.length > 0 && (
                  <ul className="mt-4 space-y-2">
                    {credentials.map((cred) => (
                      <li
                        key={cred.name}
                        className="text-sm border-l-2 border-blue-500 pl-2"
                      >
                        <div className="font-medium">{cred.name}</div>
                        <div className="text-xs text-gray-500">
                          {cred.auth_type}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          {/* Analyzers Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-900">
              Analyzers
            </h2>
            {analyzersLoading && (
              <div className="text-gray-500">Loading...</div>
            )}
            {analyzers && (
              <div className="space-y-2">
                <div className="text-2xl font-bold text-purple-600">
                  {analyzers.total_count}
                </div>
                <div className="text-sm text-gray-600">
                  {analyzers.total_count} analyzer
                  {analyzers.total_count !== 1 ? 's' : ''} available
                </div>
                <div className="text-xs text-gray-500 mt-2">
                  Total API calls: {analyzers.total_api_calls}
                </div>
                {analyzers.analyzers.length > 0 && (
                  <ul className="mt-4 space-y-2">
                    {analyzers.analyzers.map((analyzer) => (
                      <li
                        key={analyzer.name}
                        className="text-sm border-l-2 border-purple-500 pl-2"
                      >
                        <div className="font-medium capitalize">
                          {analyzer.name}
                        </div>
                        <div className="text-xs text-gray-500">
                          {analyzer.api_calls} API calls
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Instructions */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">
            ✅ Frontend Setup Complete!
          </h3>
          <div className="text-sm text-blue-800 space-y-2">
            <p>
              <strong>API Integration:</strong> Successfully connected to backend
            </p>
            <p>
              <strong>Next Steps:</strong> Build credential management and
              analysis UI components
            </p>
            <p className="text-xs text-blue-600 mt-4">
              This is a temporary test page. The full UI with credential
              management, analysis dashboard, and results viewer will be built
              next.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
