import type { ExecutiveSummary, ComplianceStatus, CategorySummary } from '../../api/types'

interface ExecutiveViewProps {
  summary: ExecutiveSummary
}

export function ExecutiveView({ summary }: ExecutiveViewProps) {
  const getRiskColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 border-green-300 dark:border-green-700'
      case 'warning':
        return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 border-yellow-300 dark:border-yellow-700'
      case 'critical':
        return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 border-red-300 dark:border-red-700'
      default:
        return 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-300 border-gray-300 dark:border-gray-700'
    }
  }

  const getComplianceColor = (status: string) => {
    switch (status) {
      case 'compliant':
        return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
      case 'at_risk':
        return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300'
      case 'non_compliant':
        return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
      default:
        return 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-300'
    }
  }

  return (
    <div className="space-y-6 executive-view">
      <div className={`rounded-lg border-2 p-8 text-center executive-risk-score ${getRiskColor(summary.overall_risk.status)}`}>
        <div className="text-6xl font-bold mb-2 risk-score-value">{summary.overall_risk.score}</div>
        <div className="text-2xl font-semibold risk-score-label">{summary.overall_risk.label}</div>
        <div className="mt-4 text-sm opacity-80">Overall Risk Score (0=Healthy, 100=Critical)</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 executive-kpi-grid">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700 executive-kpi-card">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Total Issues</div>
          <div className="text-4xl font-bold text-gray-900 dark:text-gray-100 kpi-value">{summary.total_findings}</div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700 executive-kpi-card">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Critical Issues</div>
          <div className="text-4xl font-bold text-red-600 dark:text-red-400 kpi-value">{summary.critical_count}</div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700 executive-kpi-card">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Recommendations</div>
          <div className="text-4xl font-bold text-orange-600 dark:text-orange-400 kpi-value">{summary.recommendations_count}</div>
        </div>
      </div>

      {summary.compliance_status.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 executive-section">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 executive-section-header">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Compliance Status</h3>
          </div>
          <div className="p-6 executive-section-body">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {summary.compliance_status.map((comp: ComplianceStatus) => (
                <div
                  key={comp.framework}
                  className={`rounded-lg p-4 ${getComplianceColor(comp.status)}`}
                >
                  <div className="font-semibold text-lg mb-2">{comp.framework}</div>
                  <div className="text-sm capitalize mb-2">{comp.status.replace('_', ' ')}</div>
                  {comp.total_violations > 0 && (
                    <div className="text-sm">
                      {comp.critical_violations > 0 && (
                        <div>{comp.critical_violations} critical</div>
                      )}
                      <div>{comp.total_violations} total violations</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 executive-two-col">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 executive-section">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 executive-section-header">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Top Risk Areas</h3>
          </div>
          <div className="p-6 executive-section-body">
            {summary.top_risks.length > 0 ? (
              <ul className="space-y-3">
                {summary.top_risks.map((risk: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-3 risk-list-item">
                    <span className="flex-shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-full bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 text-sm font-semibold">
                      {idx + 1}
                    </span>
                    <span className="text-gray-700 dark:text-gray-300">{risk}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500 dark:text-gray-400">No critical risks identified</p>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 executive-section">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 executive-section-header">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Severity Distribution</h3>
          </div>
          <div className="p-6 space-y-3 executive-section-body">
            <div className="flex justify-between items-center severity-row">
              <span className="text-gray-700 dark:text-gray-300">Critical</span>
              <span className="font-semibold text-red-600 dark:text-red-400">{summary.critical_count}</span>
            </div>
            <div className="flex justify-between items-center severity-row">
              <span className="text-gray-700 dark:text-gray-300">High</span>
              <span className="font-semibold text-orange-600 dark:text-orange-400">{summary.high_count}</span>
            </div>
            <div className="flex justify-between items-center severity-row">
              <span className="text-gray-700 dark:text-gray-300">Medium</span>
              <span className="font-semibold text-yellow-600 dark:text-yellow-400">{summary.medium_count}</span>
            </div>
            <div className="flex justify-between items-center severity-row">
              <span className="text-gray-700 dark:text-gray-300">Low</span>
              <span className="font-semibold text-sky-600 dark:text-sky-400">{summary.low_count}</span>
            </div>
            <div className="flex justify-between items-center severity-row">
              <span className="text-gray-700 dark:text-gray-300">Info</span>
              <span className="font-semibold text-gray-600 dark:text-gray-400">{summary.info_count}</span>
            </div>
          </div>
        </div>
      </div>

      {summary.category_breakdown.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 executive-section">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 executive-section-header">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Category Breakdown</h3>
          </div>
          <div className="p-6 executive-section-body">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead>
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Category</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Critical</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">High</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Medium</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {summary.category_breakdown.map((cat: CategorySummary) => (
                    <tr key={cat.category}>
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100 capitalize">
                        {cat.category.replace(/_/g, ' ')}
                      </td>
                      <td className="px-4 py-3 text-sm text-center">
                        {cat.critical_count > 0 && (
                          <span className="font-semibold text-red-600 dark:text-red-400">{cat.critical_count}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-center">
                        {cat.high_count > 0 && (
                          <span className="font-semibold text-orange-600 dark:text-orange-400">{cat.high_count}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-center">
                        {cat.medium_count > 0 && (
                          <span className="font-semibold text-yellow-600 dark:text-yellow-400">{cat.medium_count}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-center font-semibold text-gray-900 dark:text-gray-100">
                        {cat.total_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
