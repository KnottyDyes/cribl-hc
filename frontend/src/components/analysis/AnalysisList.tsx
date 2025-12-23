import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { analysisApi } from '../../api/analysis'
import { AnalysisCard } from './AnalysisCard'
import { AnalysisForm } from './AnalysisForm'
import { Button, Modal, SkeletonAnalysisCard } from '../common'
import { PlusIcon } from '@heroicons/react/24/outline'
import type { AnalysisRequestInput, AnalysisRequest } from '../../api/types'
import { useNavigate } from 'react-router-dom'

export function AnalysisList() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [isModalOpen, setIsModalOpen] = useState(false)

  const { data: analyses, isLoading } = useQuery({
    queryKey: ['analyses'],
    queryFn: analysisApi.list,
    refetchInterval: (query) => {
      const hasRunning = query.state.data?.some((a) => a.status === 'running')
      return hasRunning ? 3000 : false
    },
  })

  const startMutation = useMutation({
    mutationFn: analysisApi.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analyses'] })
      setIsModalOpen(false)
    },
  })

  const handleStart = (data: AnalysisRequestInput) => {
    // Convert credential_name to deployment_name for API
    const apiRequest: AnalysisRequest = {
      deployment_name: data.credential_name,
      analyzers: data.analyzers,
    }
    startMutation.mutate(apiRequest)
  }

  const handleViewResults = (id: string) => {
    navigate(`/results/${id}`)
  }

  if (isLoading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Health Check Analyses</h2>
            <p className="mt-1 text-sm text-gray-500">
              Loading analyses...
            </p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonAnalysisCard key={i} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Health Check Analyses</h2>
          <p className="mt-1 text-sm text-gray-500">
            Start new analyses or view results from previous runs
          </p>
        </div>
        <Button onClick={() => setIsModalOpen(true)}>
          <PlusIcon className="h-5 w-5 mr-2" />
          New Analysis
        </Button>
      </div>

      {analyses && analyses.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No analyses run yet.</p>
          <Button className="mt-4" onClick={() => setIsModalOpen(true)}>
            Start Your First Analysis
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {analyses?.map((analysis) => (
            <AnalysisCard
              key={analysis.analysis_id}
              analysis={analysis}
              onViewResults={handleViewResults}
            />
          ))}
        </div>
      )}

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Start New Analysis"
        size="xl"
      >
        <AnalysisForm
          onSubmit={handleStart}
          isSubmitting={startMutation.isPending}
        />
      </Modal>
    </div>
  )
}
