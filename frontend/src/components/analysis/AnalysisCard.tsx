import type { AnalysisResponse } from '../../api/types'
import { Card, Button } from '../common'
import {
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowRightIcon
} from '@heroicons/react/24/outline'

interface AnalysisCardProps {
  analysis: AnalysisResponse
  onViewResults: (id: string) => void
}

export function AnalysisCard({ analysis, onViewResults }: AnalysisCardProps) {
  const getStatusColor = () => {
    switch (analysis.status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'running':
        return 'bg-blue-100 text-blue-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusIcon = () => {
    switch (analysis.status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5" />
      case 'running':
        return <ClockIcon className="h-5 w-5 animate-spin" />
      case 'failed':
        return <ExclamationCircleIcon className="h-5 w-5" />
      default:
        return <ClockIcon className="h-5 w-5" />
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  return (
    <Card hoverable>
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h4 className="text-lg font-semibold text-gray-900">
                {analysis.deployment_name}
              </h4>
              <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${getStatusColor()}`}>
                {getStatusIcon()}
                {analysis.status.toUpperCase()}
              </span>
            </div>
            <p className="mt-1 text-sm text-gray-500">ID: {analysis.analysis_id}</p>
          </div>
          {analysis.status === 'completed' && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => onViewResults(analysis.analysis_id)}
            >
              View Results
              <ArrowRightIcon className="ml-1 h-4 w-4" />
            </Button>
          )}
        </div>

        {analysis.status === 'running' && (
          <div>
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-gray-600">{analysis.current_step || 'Running...'}</span>
              <span className="font-medium text-gray-900">{analysis.progress_percent}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${analysis.progress_percent}%` }}
              />
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Started:</span>
            <p className="font-medium text-gray-900">{formatDate(analysis.started_at)}</p>
          </div>
          <div>
            <span className="text-gray-500">Completed:</span>
            <p className="font-medium text-gray-900">{formatDate(analysis.completed_at)}</p>
          </div>
          <div>
            <span className="text-gray-500">Analyzers:</span>
            <p className="font-medium text-gray-900">{analysis.analyzers.length}</p>
          </div>
          <div>
            <span className="text-gray-500">API Calls:</span>
            <p className="font-medium text-gray-900">{analysis.api_calls_used}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-1">
          {analysis.analyzers.map((analyzer) => (
            <span
              key={analyzer}
              className="inline-flex items-center rounded-md bg-gray-100 px-2 py-1 text-xs text-gray-700"
            >
              {analyzer}
            </span>
          ))}
        </div>
      </div>
    </Card>
  )
}
