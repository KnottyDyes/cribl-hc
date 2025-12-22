import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { credentialsApi } from '../../api/credentials'
import { analyzersApi } from '../../api/analyzers'
import { Select, Button } from '../common'
import type { AnalysisRequestInput } from '../../api/types'

interface AnalysisFormProps {
  onSubmit: (data: AnalysisRequestInput) => void
  isSubmitting?: boolean
}

export function AnalysisForm({ onSubmit, isSubmitting = false }: AnalysisFormProps) {
  const [selectedCredential, setSelectedCredential] = useState('')
  const [selectedAnalyzers, setSelectedAnalyzers] = useState<string[]>([])

  const { data: credentials, isLoading: loadingCredentials } = useQuery({
    queryKey: ['credentials'],
    queryFn: credentialsApi.list,
  })

  const { data: analyzersData, isLoading: loadingAnalyzers } = useQuery({
    queryKey: ['analyzers'],
    queryFn: analyzersApi.list,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedCredential && selectedAnalyzers.length > 0) {
      onSubmit({
        credential_name: selectedCredential,
        analyzers: selectedAnalyzers,
      })
    }
  }

  const toggleAnalyzer = (analyzerName: string) => {
    setSelectedAnalyzers((prev) =>
      prev.includes(analyzerName)
        ? prev.filter((name) => name !== analyzerName)
        : [...prev, analyzerName]
    )
  }

  const selectAll = () => {
    if (analyzersData?.analyzers) {
      setSelectedAnalyzers(analyzersData.analyzers.map((a) => a.name))
    }
  }

  const deselectAll = () => {
    setSelectedAnalyzers([])
  }

  const credentialOptions = [
    { value: '', label: 'Select a credential...' },
    ...(credentials?.map((c) => ({ value: c.name, label: `${c.name} (${c.url})` })) || []),
  ]

  if (loadingCredentials || loadingAnalyzers) {
    return <div className="text-center py-4 text-gray-500">Loading...</div>
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Select
        label="Cribl Deployment"
        value={selectedCredential}
        onChange={(e) => setSelectedCredential(e.target.value)}
        options={credentialOptions}
        required
      />

      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="block text-sm font-medium text-gray-700">
            Select Analyzers <span className="text-red-500">*</span>
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={selectAll}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              Select All
            </button>
            <span className="text-gray-400">|</span>
            <button
              type="button"
              onClick={deselectAll}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              Deselect All
            </button>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4 space-y-2 max-h-96 overflow-y-auto">
          {analyzersData?.analyzers.map((analyzer) => (
            <label
              key={analyzer.name}
              className="flex items-start p-3 bg-white rounded-md border border-gray-200 hover:bg-gray-50 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selectedAnalyzers.includes(analyzer.name)}
                onChange={() => toggleAnalyzer(analyzer.name)}
                className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <div className="ml-3 flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">
                    {analyzer.name}
                  </span>
                  <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800">
                    {analyzer.api_calls} API calls
                  </span>
                </div>
                <p className="mt-1 text-xs text-gray-500">{analyzer.description}</p>
              </div>
            </label>
          ))}
        </div>

        {selectedAnalyzers.length === 0 && (
          <p className="mt-2 text-sm text-red-600">
            Please select at least one analyzer
          </p>
        )}
      </div>

      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={!selectedCredential || selectedAnalyzers.length === 0}
          loading={isSubmitting}
        >
          Start Analysis
        </Button>
      </div>
    </form>
  )
}
