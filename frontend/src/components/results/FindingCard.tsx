import type { Finding } from '../../api/types'
import { Card } from '../common'
import {
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'

interface FindingCardProps {
  finding: Finding
}

export function FindingCard({ finding }: FindingCardProps) {
  const getSeverityColor = () => {
    switch (finding.severity) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'info':
        return 'bg-gray-100 text-gray-800 border-gray-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getSeverityIcon = () => {
    switch (finding.severity) {
      case 'critical':
      case 'high':
        return <ShieldExclamationIcon className="h-5 w-5" />
      case 'medium':
        return <ExclamationTriangleIcon className="h-5 w-5" />
      default:
        return <InformationCircleIcon className="h-5 w-5" />
    }
  }

  return (
    <Card className={`border-l-4 ${getSeverityColor()}`}>
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${getSeverityColor()}`}>
                {getSeverityIcon()}
                {finding.severity.toUpperCase()}
              </span>
              <span className="inline-flex items-center rounded-md bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                {finding.category}
              </span>
            </div>
            <h4 className="mt-2 text-lg font-semibold text-gray-900">
              {finding.title}
            </h4>
            <p className="mt-1 text-sm text-gray-600">{finding.description}</p>
          </div>
        </div>

        {finding.affected_components.length > 0 && (
          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-2">
              Affected Components
            </h5>
            <div className="flex flex-wrap gap-2">
              {finding.affected_components.map((component, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center rounded-md bg-gray-100 px-2.5 py-1 text-xs text-gray-700"
                >
                  {component}
                </span>
              ))}
            </div>
          </div>
        )}

        {finding.remediation_steps.length > 0 && (
          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-2">
              Remediation Steps
            </h5>
            <ol className="list-decimal list-inside space-y-1 text-sm text-gray-600">
              {finding.remediation_steps.map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ol>
          </div>
        )}

        {finding.documentation_url && (
          <div>
            <a
              href={finding.documentation_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              View Documentation →
            </a>
          </div>
        )}

        {finding.impact_score !== undefined && (
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span>Impact Score: {finding.impact_score}/10</span>
            {finding.false_positive_risk && (
              <span className="text-yellow-600">⚠ Potential False Positive</span>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
