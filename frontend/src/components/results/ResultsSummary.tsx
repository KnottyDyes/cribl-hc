import type { AnalysisResultResponse } from '../../api/types'
import { Card } from '../common'

interface ResultsSummaryProps {
  results: AnalysisResultResponse
}

export function ResultsSummary({ results }: ResultsSummaryProps) {
  const summary = results.summary

  if (!summary) {
    return null
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <Card padding="md">
        <div className="text-center">
          <div className="text-3xl font-bold text-gray-900">{summary.total_findings}</div>
          <div className="text-sm text-gray-500 mt-1">Total Findings</div>
        </div>
      </Card>

      <Card padding="md" className="border-l-4 border-red-500">
        <div className="text-center">
          <div className="text-3xl font-bold text-red-600">
            {summary.critical_count + summary.high_count}
          </div>
          <div className="text-sm text-gray-500 mt-1">Critical & High</div>
        </div>
      </Card>

      <Card padding="md" className="border-l-4 border-yellow-500">
        <div className="text-center">
          <div className="text-3xl font-bold text-yellow-600">
            {summary.medium_count}
          </div>
          <div className="text-sm text-gray-500 mt-1">Medium</div>
        </div>
      </Card>

      <Card padding="md" className="border-l-4 border-blue-500">
        <div className="text-center">
          <div className="text-3xl font-bold text-blue-600">
            {summary.low_count + summary.info_count}
          </div>
          <div className="text-sm text-gray-500 mt-1">Low & Info</div>
        </div>
      </Card>

      <Card padding="md" className="md:col-span-2">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">
            {summary.health_score}/100
          </div>
          <div className="text-sm text-gray-500 mt-1">Health Score</div>
          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${
                summary.health_score >= 80
                  ? 'bg-green-600'
                  : summary.health_score >= 60
                  ? 'bg-yellow-600'
                  : 'bg-red-600'
              }`}
              style={{ width: `${summary.health_score}%` }}
            />
          </div>
        </div>
      </Card>

      <Card padding="md" className="md:col-span-2">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">
            {summary.risk_level.toUpperCase()}
          </div>
          <div className="text-sm text-gray-500 mt-1">Overall Risk Level</div>
          <div className="mt-2 text-xs text-gray-600">
            {Object.entries(summary.categories).map(([category, count]) => (
              <span key={category} className="mr-3">
                {category}: {count}
              </span>
            ))}
          </div>
        </div>
      </Card>
    </div>
  )
}
