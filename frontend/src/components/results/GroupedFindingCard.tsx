import { useState } from 'react'
import type { Finding } from '../../api/types'
import { Card } from '../common'
import {
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
  InformationCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'

interface GroupedFindingCardProps {
  findings: Finding[]
  groupTitle: string
  workerGroup?: string | null
}

export function GroupedFindingCard({ findings, groupTitle, workerGroup }: GroupedFindingCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const firstFinding = findings[0]

  const getSeverityColor = () => {
    switch (firstFinding.severity) {
      case 'critical':
        return 'bg-red-100 dark:bg-red-900/50 text-red-800 dark:text-red-300 border-red-200 dark:border-red-800'
      case 'high':
        return 'bg-orange-100 dark:bg-orange-900/50 text-orange-800 dark:text-orange-300 border-orange-200 dark:border-orange-800'
      case 'medium':
        return 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800'
      case 'low':
        return 'bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300 border-blue-200 dark:border-blue-800'
      case 'info':
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-600'
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-600'
    }
  }

  const getSeverityIcon = () => {
    switch (firstFinding.severity) {
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
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${getSeverityColor()}`}>
                {getSeverityIcon()}
                {firstFinding.severity.toUpperCase()}
              </span>
              <span className="inline-flex items-center rounded-md bg-blue-100 dark:bg-blue-900/50 px-2 py-0.5 text-xs font-medium text-blue-800 dark:text-blue-300">
                {firstFinding.category}
              </span>
              {workerGroup && (
                <span className="inline-flex items-center rounded-md bg-cyan-100 dark:bg-cyan-900/50 px-2 py-0.5 text-xs font-medium text-cyan-800 dark:text-cyan-300">
                  {workerGroup}
                </span>
              )}
              <span className="inline-flex items-center rounded-md bg-purple-100 dark:bg-purple-900/50 px-2 py-0.5 text-xs font-medium text-purple-800 dark:text-purple-300">
                {findings.length} instance{findings.length > 1 ? 's' : ''}
              </span>
            </div>

            {(() => {
              const uniquePipelines = Array.from(new Set(findings.map(f => (f.metadata as Record<string, any>)?.pipeline).filter(Boolean)))
              const uniqueInputs = Array.from(new Set(findings.map(f => (f.metadata as Record<string, any>)?.input).filter(Boolean)))
              const uniqueWorkerGroups = Array.from(new Set(findings.map(f => (f.metadata as Record<string, any>)?.worker_group).filter(Boolean)))
              
              if (uniquePipelines.length === 0 && uniqueInputs.length === 0 && uniqueWorkerGroups.length === 0) return null

              return (
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-500 dark:text-gray-400">
                  {uniqueWorkerGroups.length > 0 && !workerGroup && (
                    <span className="inline-flex items-center gap-1">
                      <span className="font-medium">Worker Groups:</span> {uniqueWorkerGroups.slice(0, 3).join(', ')}
                      {uniqueWorkerGroups.length > 3 && ` +${uniqueWorkerGroups.length - 3} more`}
                    </span>
                  )}
                  {uniquePipelines.length > 0 && (
                    <span className="inline-flex items-center gap-1">
                      <span className="font-medium">Found in {uniquePipelines.length} pipeline{uniquePipelines.length !== 1 ? 's' : ''}:</span> 
                      {uniquePipelines.slice(0, 3).join(', ')}
                      {uniquePipelines.length > 3 && ` +${uniquePipelines.length - 3} more`}
                    </span>
                  )}
                </div>
              )
            })()}

            <h4 className="mt-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
              {groupTitle}
            </h4>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              {firstFinding.description.split('.')[0]}.
            </p>
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="ml-4 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            aria-label={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? (
              <ChevronDownIcon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            ) : (
              <ChevronRightIcon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            )}
          </button>
        </div>

        <div>
          <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Affected Components
          </h5>
          <div className="flex flex-wrap gap-2">
            {(() => {
              const allComponents = findings.flatMap(f => f.affected_components)
              const displayComponents = isExpanded ? allComponents : allComponents.slice(0, 10)
              
              return (
                <>
                  {displayComponents.map((component, idx) => (
                    <span
                      key={`${component}-${idx}`}
                      className="inline-flex items-center rounded-md bg-gray-100 dark:bg-gray-700 px-2.5 py-1 text-xs text-gray-700 dark:text-gray-300"
                    >
                      {component}
                    </span>
                  ))}
                  {!isExpanded && allComponents.length > 10 && (
                    <span className="inline-flex items-center rounded-md bg-gray-100 dark:bg-gray-700 px-2.5 py-1 text-xs text-gray-500 dark:text-gray-400">
                      +{allComponents.length - 10} more
                    </span>
                  )}
                </>
              )
            })()}
          </div>
        </div>

        {isExpanded && (
          <>
            {firstFinding.estimated_impact && (
              <div>
                <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Impact
                </h5>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {firstFinding.estimated_impact}
                </p>
              </div>
            )}

            {firstFinding.remediation_steps.length > 0 && (
              <div>
                <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Remediation Steps
                </h5>
                <ol className="list-decimal list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400">
                  {firstFinding.remediation_steps.map((step, idx) => (
                    <li key={idx}>{step}</li>
                  ))}
                </ol>
              </div>
            )}

            {firstFinding.documentation_url && (
              <div>
                <a
                  href={firstFinding.documentation_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                >
                  View Documentation →
                </a>
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  )
}
