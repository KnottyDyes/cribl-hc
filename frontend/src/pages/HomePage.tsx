import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { systemApi } from '../api/system'
import { credentialsApi } from '../api/credentials'
import { analysisApi } from '../api/analysis'
import { Card, Button } from '../components/common'
import {
  KeyIcon,
  BeakerIcon,
  CheckCircleIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline'

export function HomePage() {
  const navigate = useNavigate()

  const { data: version } = useQuery({
    queryKey: ['version'],
    queryFn: systemApi.getVersion,
  })

  const { data: credentials } = useQuery({
    queryKey: ['credentials'],
    queryFn: credentialsApi.list,
  })

  const { data: analyses } = useQuery({
    queryKey: ['analyses'],
    queryFn: analysisApi.list,
  })

  const recentAnalyses = analyses?.slice(0, 3) || []

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Cribl Health Check
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Automated security and configuration analysis for your Cribl deployments
          </p>
          {version && (
            <p className="mt-2 text-sm text-gray-500">
              API Version: {version.version}
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <Card
            title="Credentials"
            subtitle={`${credentials?.length || 0} configured`}
            hoverable
            className="cursor-pointer"
            onClick={() => navigate('/credentials')}
          >
            <div className="flex items-center justify-between">
              <KeyIcon className="h-12 w-12 text-blue-600" />
              <Button variant="ghost" size="sm">
                Manage
                <ArrowRightIcon className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </Card>

          <Card
            title="Analyses"
            subtitle={`${analyses?.length || 0} total runs`}
            hoverable
            className="cursor-pointer"
            onClick={() => navigate('/analysis')}
          >
            <div className="flex items-center justify-between">
              <BeakerIcon className="h-12 w-12 text-green-600" />
              <Button variant="ghost" size="sm">
                View
                <ArrowRightIcon className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </Card>

          <Card title="Quick Start" subtitle="Get started in minutes">
            <div className="space-y-3 text-sm">
              <div className="flex items-start">
                <CheckCircleIcon className="h-5 w-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
                <span>Add your Cribl deployment credentials</span>
              </div>
              <div className="flex items-start">
                <CheckCircleIcon className="h-5 w-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
                <span>Select analyzers to run</span>
              </div>
              <div className="flex items-start">
                <CheckCircleIcon className="h-5 w-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
                <span>Review findings and recommendations</span>
              </div>
            </div>
          </Card>
        </div>

        {recentAnalyses.length > 0 && (
          <Card title="Recent Analyses">
            <div className="space-y-3">
              {recentAnalyses.map((analysis) => (
                <div
                  key={analysis.analysis_id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer"
                  onClick={() => {
                    if (analysis.status === 'completed') {
                      navigate(`/results/${analysis.analysis_id}`)
                    } else {
                      navigate('/analysis')
                    }
                  }}
                >
                  <div>
                    <p className="font-medium text-gray-900">
                      {analysis.deployment_name}
                    </p>
                    <p className="text-sm text-gray-500">
                      {new Date(analysis.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                      analysis.status === 'completed'
                        ? 'bg-green-100 text-green-800'
                        : analysis.status === 'running'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {analysis.status.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        )}

        {credentials?.length === 0 && (
          <Card className="bg-blue-50 border-blue-200">
            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Get Started
              </h3>
              <p className="text-gray-600 mb-4">
                Add your first Cribl deployment credential to begin running health checks
              </p>
              <Button onClick={() => navigate('/credentials')}>
                Add Credential
              </Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
