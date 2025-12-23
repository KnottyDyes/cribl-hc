import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { analysisApi } from '../api/analysis'
import { ResultsSummary } from '../components/results/ResultsSummary'
import { FindingCard } from '../components/results/FindingCard'
import { Button, Select } from '../components/common'
import { ArrowLeftIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline'
import type { AnalysisResultResponse } from '../api/types'

export function ResultsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')

  const { data: results, isLoading, error } = useQuery({
    queryKey: ['analysis-results', id],
    queryFn: () => analysisApi.getResults(id!),
    enabled: !!id,
  })

  // Calculate summary from findings if not provided by backend
  const enrichedResults = useMemo((): AnalysisResultResponse | undefined => {
    if (!results) return undefined

    if (results.summary) return results

    // Calculate summary from findings
    const findings = results.findings || []
    const critical_count = findings.filter((f) => f.severity === 'critical').length
    const high_count = findings.filter((f) => f.severity === 'high').length
    const medium_count = findings.filter((f) => f.severity === 'medium').length
    const low_count = findings.filter((f) => f.severity === 'low').length
    const info_count = findings.filter((f) => f.severity === 'info').length

    // Calculate categories
    const categories: Record<string, number> = {}
    findings.forEach((f) => {
      categories[f.category] = (categories[f.category] || 0) + 1
    })

    // Calculate health score if not provided
    // More balanced scoring: critical/high have big impact, medium/low have smaller impact
    const health_score = results.health_score !== null
      ? results.health_score
      : Math.max(0, 100 - (critical_count * 20 + high_count * 10 + medium_count * 3 + low_count * 0.5))

    // Determine risk level
    let risk_level = 'low'
    if (critical_count > 0 || high_count > 3) risk_level = 'critical'
    else if (high_count > 0 || medium_count > 5) risk_level = 'high'
    else if (medium_count > 0) risk_level = 'medium'

    return {
      ...results,
      summary: {
        total_findings: findings.length,
        critical_count,
        high_count,
        medium_count,
        low_count,
        info_count,
        health_score,
        risk_level,
        categories,
      },
    }
  }, [results])

  const handleExport = async (format: 'json' | 'html' | 'md') => {
    if (!id) return
    try {
      const blob = await analysisApi.export(id, format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `health-check-${id}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      alert('Failed to export results')
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error || !enrichedResults) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <p className="text-red-600 mb-4">Failed to load analysis results</p>
          <Button onClick={() => navigate('/analysis')}>
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Analyses
          </Button>
        </div>
      </div>
    )
  }

  const severityOptions = [
    { value: 'all', label: 'All Severities' },
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
    { value: 'info', label: 'Info' },
  ]

  const categories = ['all', ...Object.keys(enrichedResults.summary?.categories || {})]
  const categoryOptions = categories.map((cat) => ({
    value: cat,
    label: cat === 'all' ? 'All Categories' : cat,
  }))

  const severityOrder = { critical: 5, high: 4, medium: 3, low: 2, info: 1 }

  const filteredFindings = enrichedResults.findings
    .filter((finding) => {
      const matchesSeverity = severityFilter === 'all' || finding.severity === severityFilter
      const matchesCategory = categoryFilter === 'all' || finding.category === categoryFilter
      return matchesSeverity && matchesCategory
    })
    .sort((a, b) => {
      // Sort by severity first (descending: critical → high → medium → low → info)
      const severityDiff = severityOrder[b.severity] - severityOrder[a.severity]
      if (severityDiff !== 0) return severityDiff
      // Then by category (ascending) as secondary sort
      return a.category.localeCompare(b.category)
    })

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate('/analysis')}>
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {enrichedResults.deployment_name}
              </h1>
              <p className="text-sm text-gray-500">
                Analysis ID: {enrichedResults.analysis_id} • Completed:{' '}
                {enrichedResults.completed_at ? new Date(enrichedResults.completed_at).toLocaleString() : "N/A"}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleExport('json')}
            >
              <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
              JSON
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleExport('html')}
            >
              <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
              HTML
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleExport('md')}
            >
              <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
              Markdown
            </Button>
          </div>
        </div>

        {enrichedResults.summary && <ResultsSummary results={enrichedResults} />}

        <div className="mb-6 flex gap-4">
          <div className="flex-1">
            <Select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              options={severityOptions}
            />
          </div>
          <div className="flex-1">
            <Select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              options={categoryOptions}
            />
          </div>
        </div>

        <div className="space-y-4">
          {filteredFindings.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg">
              <p className="text-gray-500">No findings match the selected filters.</p>
            </div>
          ) : (
            filteredFindings.map((finding) => (
              <FindingCard key={finding.id} finding={finding} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}
