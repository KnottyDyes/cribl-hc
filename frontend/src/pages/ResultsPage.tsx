import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { analysisApi } from '../api/analysis'
import { ResultsSummary } from '../components/results/ResultsSummary'
import { FindingCard } from '../components/results/FindingCard'
import { GroupedFindingCard } from '../components/results/GroupedFindingCard'
import { Button, Select, SkeletonFindingCard } from '../components/common'
import { ArrowLeftIcon, ArrowDownTrayIcon, ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import type { AnalysisResultResponse, CriblProduct, Finding } from '../api/types'

const SEVERITY_ORDER = { critical: 5, high: 4, medium: 3, low: 2, info: 1 } as const

export function ResultsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [productFilter, setProductFilter] = useState<string>('all')
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set())

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

  const filteredFindings = useMemo(() => {
    if (!enrichedResults?.findings) return []
    
    return enrichedResults.findings
      .filter((finding) => {
        const matchesSeverity = severityFilter === 'all' || finding.severity === severityFilter
        const matchesCategory = categoryFilter === 'all' || finding.category === categoryFilter
        const matchesProduct = productFilter === 'all' ||
          (finding.product_tags && finding.product_tags.includes(productFilter as CriblProduct))
        return matchesSeverity && matchesCategory && matchesProduct
      })
      .sort((a, b) => {
        const severityDiff = SEVERITY_ORDER[b.severity] - SEVERITY_ORDER[a.severity]
        if (severityDiff !== 0) return severityDiff
        return a.category.localeCompare(b.category)
      })
  }, [enrichedResults, severityFilter, categoryFilter, productFilter])

  const groupedFindings = useMemo(() => {
     const workerGroupMap: { [key: string]: { [key: string]: Finding[] } } = {}
     
     filteredFindings.forEach((finding) => {
       // Global findings (no worker_group) are separate from default worker group
       const workerGroup = finding.worker_group === null || finding.worker_group === undefined ? '__global__' : finding.worker_group
       if (!workerGroupMap[workerGroup]) {
         workerGroupMap[workerGroup] = {}
       }
      
      const groupKey = finding.grouping_id || finding.id
      if (!workerGroupMap[workerGroup][groupKey]) {
        workerGroupMap[workerGroup][groupKey] = []
      }
      workerGroupMap[workerGroup][groupKey].push(finding)
    })

    const result: Array<{
      findings: Finding[]
      groupTitle: string
      workerGroup: string
      isGrouped: boolean
      severity: string
    }> = []

    Object.entries(workerGroupMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .forEach(([workerGroup, groups]) => {
        Object.entries(groups).forEach(([, findings]) => {
          const first = findings[0]
          const isGrouped = !!first.grouping_id && findings.length > 1
          const groupTitle = isGrouped ? first.title.split(':')[0] : first.title
          
          result.push({
            findings,
            groupTitle,
            workerGroup,
            isGrouped,
            severity: first.severity,
          })
        })
      })

    return result.sort((a, b) => {
      if (a.workerGroup !== b.workerGroup) {
        return a.workerGroup.localeCompare(b.workerGroup)
      }
      const severityDiff = SEVERITY_ORDER[b.severity as keyof typeof SEVERITY_ORDER] - SEVERITY_ORDER[a.severity as keyof typeof SEVERITY_ORDER]
      if (severityDiff !== 0) return severityDiff
      return a.groupTitle.localeCompare(b.groupTitle)
    })
  }, [filteredFindings])

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
    } catch {
      alert('Failed to export results')
    }
  }

  const toggleWorkerGroupCollapse = (workerGroup: string) => {
    const newCollapsed = new Set(collapsedGroups)
    if (newCollapsed.has(workerGroup)) {
      newCollapsed.delete(workerGroup)
    } else {
      newCollapsed.add(workerGroup)
    }
    setCollapsedGroups(newCollapsed)
  }

  if (isLoading) {
    return (
      <div className="bg-gray-50 dark:bg-gray-900 min-h-screen p-6">
        <div className="max-w-7xl mx-auto">
          <div className="mb-6">
            <Button
              variant="ghost"
              onClick={() => navigate('/analysis')}
              className="mb-4"
            >
              <ArrowLeftIcon className="h-5 w-5 mr-2" />
              Back to Analyses
            </Button>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Loading Analysis Results...</h1>
          </div>

          <div className="grid grid-cols-1 gap-6">
            {Array.from({ length: 5 }).map((_, i) => (
              <SkeletonFindingCard key={i} />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error || !enrichedResults) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <p className="text-red-600 dark:text-red-400 mb-4">Failed to load analysis results</p>
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

  const productOptions = [
    { value: 'all', label: 'All Products' },
    { value: 'stream', label: 'Stream' },
    { value: 'edge', label: 'Edge' },
    { value: 'lake', label: 'Lake' },
    { value: 'search', label: 'Search' },
  ]

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate('/analysis')}>
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {enrichedResults.deployment_name}
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
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
          <div className="flex-1">
            <Select
              value={productFilter}
              onChange={(e) => setProductFilter(e.target.value)}
              options={productOptions}
            />
          </div>
        </div>

        <div className="space-y-6">
          {groupedFindings.length === 0 ? (
            <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg">
              <p className="text-gray-500 dark:text-gray-400">No findings match the selected filters.</p>
            </div>
          ) : (
             Object.entries(
               groupedFindings.reduce(
                 (acc, group) => {
                   const wg = group.workerGroup
                   if (!acc[wg]) acc[wg] = []
                   acc[wg].push(group)
                   return acc
                 },
                 {} as Record<string, typeof groupedFindings>
               )
             ).map(([workerGroup, groups]) => {
               const isCollapsed = collapsedGroups.has(workerGroup)
               const displayName = 
                 workerGroup === '__global__' ? 'Global Findings' :
                 workerGroup === 'default' ? 'Default Worker Group' : 
                 `Worker Group: ${workerGroup}`
               return (
                 <div key={workerGroup} className="bg-white dark:bg-gray-800 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
                   <button
                     onClick={() => toggleWorkerGroupCollapse(workerGroup)}
                     className="w-full px-4 py-4 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                   >
                     {isCollapsed ? (
                       <ChevronRightIcon className="h-5 w-5 text-gray-400" />
                     ) : (
                       <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                     )}
                     <div className="flex-1 text-left">
                       <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                         {displayName}
                       </h2>
                     </div>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {groups.length} finding{groups.length !== 1 ? 's' : ''}
                    </span>
                  </button>

                  {!isCollapsed && (
                    <div className="px-4 pb-4 pt-0 space-y-4 border-t border-gray-200 dark:border-gray-700">
                      {groups.map((group, idx) => (
                        group.isGrouped ? (
                          <GroupedFindingCard
                            key={`${group.findings[0].grouping_id}-${group.workerGroup}-${idx}`}
                            findings={group.findings}
                            groupTitle={group.groupTitle}
                            workerGroup={group.workerGroup}
                          />
                        ) : (
                          <FindingCard key={group.findings[0].id} finding={group.findings[0]} />
                        )
                      ))}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
